"""Run raw CNN-driven autonomous maze navigation in CoppeliaSim."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


CLASS_NAMES = ("forward", "left", "right")
CLASS_TO_INDEX = {name: index for index, name in enumerate(CLASS_NAMES)}
FORWARD_SPEED = 2.0
TURN_SPEED = 2.0
LOOP_INTERVAL_SECONDS = 0.10
PRINT_INTERVAL_SECONDS = 0.50
CAMERA_PATH = "/PioneerP3DX/cam1"
MODEL_IMAGE_SIZE = (50, 50)
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = REPO_ROOT / "models" / "maze_navigation_model_v3.h5"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Use the accepted v3 CNN to drive the PioneerP3DX autonomously "
            "from its live CoppeliaSim camera feed."
        )
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help=f"Path to the trained v3 .h5 model (default: {DEFAULT_MODEL_PATH})",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Disable the OpenCV preview window while keeping console output.",
    )
    return parser.parse_args(argv)


def motor_velocities_for_prediction(predicted_label: str) -> tuple[float, float]:
    """Translate the CNN class directly into the established Pioneer wheel command."""
    if predicted_label == "forward":
        return FORWARD_SPEED, FORWARD_SPEED
    if predicted_label == "left":
        return -TURN_SPEED, TURN_SPEED
    if predicted_label == "right":
        return TURN_SPEED, -TURN_SPEED
    raise ValueError(f"Unknown prediction label: {predicted_label!r}")


def convert_raw_image_rgb(raw_image, resolution, np_module):
    """Validate CoppeliaSim's bottom-up RGB buffer and return top-down RGB."""
    if len(resolution) != 2:
        raise ValueError(f"Expected [width, height], received {resolution}")
    width, height = resolution
    if not all(isinstance(value, int) and value > 0 for value in resolution):
        raise ValueError(f"Camera resolution must contain positive integers: {resolution}")

    expected_bytes = width * height * 3
    if len(raw_image) != expected_bytes:
        raise ValueError(
            f"Expected {expected_bytes} RGB bytes, received {len(raw_image)}"
        )

    frame_rgb = np_module.frombuffer(raw_image, dtype=np_module.uint8).reshape(
        height, width, 3
    )
    return np_module.flipud(frame_rgb).copy()


def preprocess_for_model(frame_rgb, tf_module):
    """Reproduce Step-5 preprocessing: RGB, 50x50, float32, scaled to [0, 1]."""
    image = tf_module.convert_to_tensor(frame_rgb)
    image = tf_module.image.resize(image, MODEL_IMAGE_SIZE)
    image = tf_module.cast(image, tf_module.float32) / 255.0
    return image[None, ...]


def validate_model_contract(model) -> None:
    """Fail fast if the loaded model is incompatible with the accepted Step-5 contract."""
    input_shape = tuple(model.input_shape)
    output_shape = tuple(model.output_shape)
    expected_input = (None, MODEL_IMAGE_SIZE[0], MODEL_IMAGE_SIZE[1], 3)
    expected_output = (None, len(CLASS_NAMES))

    if input_shape != expected_input:
        raise ValueError(
            f"Unexpected model input shape {input_shape}; expected {expected_input}"
        )
    if output_shape != expected_output:
        raise ValueError(
            f"Unexpected model output shape {output_shape}; expected {expected_output}"
        )


def stop_motors(sim, left_motor, right_motor) -> bool:
    """Attempt to stop each wheel independently during shutdown."""
    succeeded = True
    for motor in (left_motor, right_motor):
        if motor is None:
            continue
        try:
            sim.setJointTargetVelocity(motor, 0.0)
        except Exception as error:
            succeeded = False
            print(
                f"STEP 6 CLEANUP ERROR: Could not stop a motor: {error}",
                file=sys.stderr,
            )
    return succeeded


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    model_path = args.model.resolve()

    print("STEP 6 - CNN Autonomous Navigation")
    print("IMPORTANT: The CNN directly controls the PioneerP3DX motors in this program.")
    print("IMPORTANT: Keep this first run inside CoppeliaSim only.")
    print(f"Model: {model_path}")

    sim = None
    cv2 = None
    left_motor = None
    right_motor = None
    exit_status = 0
    prediction_counts = {name: 0 for name in CLASS_NAMES}

    try:
        if not model_path.is_file() or model_path.stat().st_size == 0:
            raise FileNotFoundError(f"Trained v3 model not found: {model_path}")

        print(
            "Startup 1/4: importing TensorFlow and runtime libraries. "
            "Motors are not active yet.",
            flush=True,
        )
        import cv2
        import numpy as np
        import tensorflow as tf
        from coppeliasim_zmqremoteapi_client import RemoteAPIClient

        print(
            f"Startup 2/4: TensorFlow {tf.__version__} loaded. Loading v3 CNN...",
            flush=True,
        )
        model = tf.keras.models.load_model(str(model_path), compile=False)
        validate_model_contract(model)
        print(
            f"Model contract: input={model.input_shape}, output={model.output_shape}",
            flush=True,
        )
        print("Class mapping: forward=0, left=1, right=2", flush=True)

        print("Startup 3/4: warming the CNN once before actuation...", flush=True)
        model(
            tf.zeros(
                (1, MODEL_IMAGE_SIZE[0], MODEL_IMAGE_SIZE[1], 3),
                dtype=tf.float32,
            ),
            training=False,
        ).numpy()
        print("Startup 3/4: model inference warm-up complete.", flush=True)

        print("Startup 4/4: connecting to CoppeliaSim...", flush=True)
        client = RemoteAPIClient()
        sim = client.require("sim")

        handles = {}
        for path in (
            "/PioneerP3DX",
            "/PioneerP3DX/leftMotor",
            "/PioneerP3DX/rightMotor",
            CAMERA_PATH,
        ):
            handle = sim.getObject(path)
            if handle < 0:
                raise RuntimeError(f"Could not resolve scene object {path}")
            handles[path] = handle
            if path == "/PioneerP3DX/leftMotor":
                left_motor = handle
            elif path == "/PioneerP3DX/rightMotor":
                right_motor = handle

        stop_motors(sim, left_motor, right_motor)

        print(
            "READY: autonomous navigator is initialized. Start/resume the "
            "CoppeliaSim simulation when ready.",
            flush=True,
        )
        waiting_message_printed = False
        while sim.getSimulationState() in (
            sim.simulation_stopped,
            sim.simulation_paused,
        ):
            if not waiting_message_printed:
                print("Waiting for CoppeliaSim simulation to run...", flush=True)
                waiting_message_printed = True
            time.sleep(0.10)

        print(
            "SIMULATION RUNNING DETECTED — CNN MOTOR CONTROL IS ACTIVE NOW.",
            flush=True,
        )

        last_print = 0.0
        resolution_printed = False
        blank_frame_noted = False

        while True:
            loop_started = time.monotonic()

            if sim.getSimulationState() in (
                sim.simulation_stopped,
                sim.simulation_paused,
            ):
                print("Simulation stopped/paused; ending autonomous run.", flush=True)
                break

            raw_image, resolution = sim.getVisionSensorImg(handles[CAMERA_PATH])
            frame_rgb = convert_raw_image_rgb(raw_image, resolution, np)

            if not resolution_printed:
                print(f"Live camera resolution: {resolution[0]} x {resolution[1]}")
                resolution_printed = True

            # CoppeliaSim can expose an all-zero camera buffer during the first
            # sensor cycle. Keep the robot stopped until a real frame arrives.
            if not np.any(frame_rgb):
                stop_motors(sim, left_motor, right_motor)
                if not blank_frame_noted:
                    print("Waiting for the first non-blank camera frame...")
                    blank_frame_noted = True
                remaining = LOOP_INTERVAL_SECONDS - (time.monotonic() - loop_started)
                if remaining > 0:
                    time.sleep(remaining)
                continue

            model_input = preprocess_for_model(frame_rgb, tf)
            probabilities = model(model_input, training=False).numpy()[0]
            predicted_index = int(np.argmax(probabilities))
            predicted_label = CLASS_NAMES[predicted_index]
            confidence = float(probabilities[predicted_index])
            prediction_counts[predicted_label] += 1

            left_velocity, right_velocity = motor_velocities_for_prediction(
                predicted_label
            )
            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)

            if not args.no_display:
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                cv2.putText(
                    frame_bgr,
                    f"CNN: {predicted_label} {confidence:.2f}",
                    (3, 14),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.36,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    frame_bgr,
                    "AUTONOMOUS",
                    (3, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.36,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow("Step 6 - CNN Autonomous Navigation", frame_bgr)
                cv2.waitKey(1)

            now = time.monotonic()
            if now - last_print >= PRINT_INTERVAL_SECONDS:
                print(
                    f"cnn={predicted_label:<7} confidence={confidence:.3f} "
                    f"wheels=({left_velocity:.1f}, {right_velocity:.1f})"
                )
                last_print = now

            remaining = LOOP_INTERVAL_SECONDS - (time.monotonic() - loop_started)
            if remaining > 0:
                time.sleep(remaining)

    except KeyboardInterrupt:
        print("\nAutonomous navigation stopped by user.")
    except Exception as error:
        print(f"STEP 6 ERROR: {error}", file=sys.stderr)
        exit_status = 1
    finally:
        if sim is not None and not stop_motors(sim, left_motor, right_motor):
            exit_status = 1

        if cv2 is not None:
            try:
                cv2.destroyAllWindows()
            except Exception as error:
                print(
                    f"STEP 6 CLEANUP ERROR: Could not close OpenCV windows: {error}",
                    file=sys.stderr,
                )
                exit_status = 1

        total_predictions = sum(prediction_counts.values())
        if total_predictions:
            print(
                "Prediction counts: "
                + ", ".join(
                    f"{name}={prediction_counts[name]}" for name in CLASS_NAMES
                )
            )

    return exit_status


if __name__ == "__main__":
    sys.exit(main())
