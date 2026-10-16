"""Collect new human recovery demonstrations without touching the accepted dataset.

The human controls W/A/D. Every stable command frame is saved in a new session
folder together with v3 shadow predictions and robot pose. The CNN never actuates
motors in this program.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


CLASS_NAMES = ("forward", "left", "right")
CLASS_TO_INDEX = {name: index for index, name in enumerate(CLASS_NAMES)}
FORWARD_SPEED = 2.0
TURN_SPEED = 2.0
LOOP_INTERVAL_SECONDS = 0.10
SAVE_INTERVAL_SECONDS = 0.10
CAMERA_PATH = "/PioneerP3DX/cam1"
MODEL_IMAGE_SIZE = (50, 50)
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL_PATH = REPO_ROOT / "models" / "maze_navigation_model_v3.h5"
DEFAULT_SESSION_ROOT = REPO_ROOT / "recovery_sessions"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Human-driven recovery-data collection with v3 CNN in shadow mode. "
            "Saved data is isolated from the accepted Step-4 dataset."
        )
    )
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_SESSION_ROOT)
    parser.add_argument("--no-display", action="store_true")
    return parser.parse_args(argv)


def get_human_command(keyboard_module):
    held = [key for key in ("w", "a", "d") if keyboard_module.is_pressed(key)]
    if len(held) != 1:
        return None, 0.0, 0.0
    if held[0] == "w":
        return "forward", FORWARD_SPEED, FORWARD_SPEED
    if held[0] == "a":
        return "left", -TURN_SPEED, TURN_SPEED
    return "right", TURN_SPEED, -TURN_SPEED


def convert_raw_image_rgb(raw_image, resolution, np_module):
    if len(resolution) != 2:
        raise ValueError(f"Expected [width, height], received {resolution}")
    width, height = resolution
    expected = width * height * 3
    if len(raw_image) != expected:
        raise ValueError(f"Expected {expected} bytes, received {len(raw_image)}")
    frame = np_module.frombuffer(raw_image, dtype=np_module.uint8).reshape(
        height, width, 3
    )
    return np_module.flipud(frame).copy()


def preprocess_for_model(frame_rgb, tf_module):
    image = tf_module.convert_to_tensor(frame_rgb)
    image = tf_module.image.resize(image, MODEL_IMAGE_SIZE)
    image = tf_module.cast(image, tf_module.float32) / 255.0
    return image[None, ...]


def validate_model_contract(model):
    if tuple(model.input_shape) != (None, 50, 50, 3):
        raise ValueError(f"Unexpected model input shape: {model.input_shape}")
    if tuple(model.output_shape) != (None, 3):
        raise ValueError(f"Unexpected model output shape: {model.output_shape}")


def stop_motors(sim, left_motor, right_motor):
    ok = True
    for motor in (left_motor, right_motor):
        if motor is None:
            continue
        try:
            sim.setJointTargetVelocity(motor, 0.0)
        except Exception as error:
            ok = False
            print(f"RECOVERY CLEANUP ERROR: {error}", file=sys.stderr)
    return ok


def main(argv=None):
    args = parse_args(argv)
    model_path = args.model.resolve()
    output_root = args.output_root.resolve()

    sim = None
    cv2 = None
    left_motor = None
    right_motor = None
    csv_file = None
    exit_status = 0

    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    session_dir = output_root / f"recovery_{run_stamp}"
    for label in CLASS_NAMES:
        (session_dir / label).mkdir(parents=True, exist_ok=False)
    metadata_path = session_dir / "metadata.csv"

    counts = {name: 0 for name in CLASS_NAMES}
    disagreements = 0
    scored = 0
    last_save = None

    try:
        if not model_path.is_file():
            raise FileNotFoundError(f"v3 model not found: {model_path}")

        print("STEP 5C - Recovery Demonstration Collection")
        print("W=forward, A=left, D=right; release keys to stop.")
        print("The HUMAN controls the motors. v3 is shadow-only.")
        print(f"Session folder: {session_dir}")

        import cv2
        import keyboard
        import numpy as np
        import tensorflow as tf
        from coppeliasim_zmqremoteapi_client import RemoteAPIClient

        model = tf.keras.models.load_model(str(model_path), compile=False)
        validate_model_contract(model)
        model(tf.zeros((1, 50, 50, 3), dtype=tf.float32), training=False).numpy()

        client = RemoteAPIClient()
        sim = client.require("sim")
        handles = {}
        for path in (
            "/PioneerP3DX",
            "/PioneerP3DX/leftMotor",
            "/PioneerP3DX/rightMotor",
            CAMERA_PATH,
        ):
            handles[path] = sim.getObject(path)
        left_motor = handles["/PioneerP3DX/leftMotor"]
        right_motor = handles["/PioneerP3DX/rightMotor"]
        stop_motors(sim, left_motor, right_motor)

        csv_file = metadata_path.open("w", newline="", encoding="utf-8")
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "timestamp_utc",
                "elapsed_seconds",
                "human_command",
                "v3_prediction",
                "forward_probability",
                "left_probability",
                "right_probability",
                "confidence",
                "agreement",
                "image_relative_path",
                "robot_x",
                "robot_y",
                "robot_yaw",
            ]
        )

        print("READY: collector initialized. Start CoppeliaSim when ready.", flush=True)
        while sim.getSimulationState() in (
            sim.simulation_stopped,
            sim.simulation_paused,
        ):
            time.sleep(0.10)

        print(
            "SIMULATION RUNNING — W/A/D manual control and recovery recording are active.",
            flush=True,
        )
        run_started = time.monotonic()

        while True:
            loop_started = time.monotonic()
            if sim.getSimulationState() in (
                sim.simulation_stopped,
                sim.simulation_paused,
            ):
                print("Simulation stopped; ending recovery session.")
                break

            before_label, left_velocity, right_velocity = get_human_command(keyboard)
            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)

            raw_image, resolution = sim.getVisionSensorImg(handles[CAMERA_PATH])
            frame_rgb = convert_raw_image_rgb(raw_image, resolution, np)
            if not np.any(frame_rgb):
                stop_motors(sim, left_motor, right_motor)
                time.sleep(LOOP_INTERVAL_SECONDS)
                continue

            probs = model(
                preprocess_for_model(frame_rgb, tf), training=False
            ).numpy()[0]
            pred_index = int(np.argmax(probs))
            pred_label = CLASS_NAMES[pred_index]
            confidence = float(probs[pred_index])

            after_label, left_velocity, right_velocity = get_human_command(keyboard)
            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)

            stable_label = (
                before_label
                if before_label is not None and after_label == before_label
                else None
            )

            if not args.no_display:
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                cv2.putText(
                    frame_bgr,
                    f"HUMAN: {after_label or 'none'}",
                    (3, 12),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.32,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    frame_bgr,
                    f"V3: {pred_label} {confidence:.2f}",
                    (3, 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.32,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow("Step 5C - Recovery Demonstrations", frame_bgr)
                cv2.waitKey(1)

            now = time.monotonic()
            if (
                stable_label is not None
                and (last_save is None or now - last_save >= SAVE_INTERVAL_SECONDS)
            ):
                elapsed = now - run_started
                timestamp = datetime.now(timezone.utc)
                counts[stable_label] += 1
                filename = (
                    f"{stable_label}_{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}_"
                    f"{counts[stable_label]:06d}.jpg"
                )
                image_path = session_dir / stable_label / filename
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                if not cv2.imwrite(str(image_path), frame_bgr):
                    raise RuntimeError(f"Could not save {image_path}")

                position = sim.getObjectPosition(
                    handles["/PioneerP3DX"], sim.handle_world
                )
                yaw = sim.getObjectOrientation(
                    handles["/PioneerP3DX"], sim.handle_world
                )[2]
                agree = stable_label == pred_label
                scored += 1
                disagreements += int(not agree)

                writer.writerow(
                    [
                        timestamp.isoformat(),
                        f"{elapsed:.3f}",
                        stable_label,
                        pred_label,
                        f"{float(probs[0]):.6f}",
                        f"{float(probs[1]):.6f}",
                        f"{float(probs[2]):.6f}",
                        f"{confidence:.6f}",
                        "1" if agree else "0",
                        str(image_path.relative_to(session_dir)),
                        f"{float(position[0]):.6f}",
                        f"{float(position[1]):.6f}",
                        f"{float(yaw):.6f}",
                    ]
                )
                csv_file.flush()
                last_save = now

            remaining = LOOP_INTERVAL_SECONDS - (time.monotonic() - loop_started)
            if remaining > 0:
                time.sleep(remaining)

    except KeyboardInterrupt:
        print("Recovery collection stopped by user.")
    except Exception as error:
        print(f"RECOVERY COLLECTION ERROR: {error}", file=sys.stderr)
        exit_status = 1
    finally:
        if sim is not None and not stop_motors(sim, left_motor, right_motor):
            exit_status = 1
        if csv_file is not None:
            csv_file.close()
        if cv2 is not None:
            cv2.destroyAllWindows()

        print(
            "Saved frames: "
            + ", ".join(f"{name}={counts[name]}" for name in CLASS_NAMES)
        )
        if scored:
            print(
                f"v3 shadow disagreement on saved frames: "
                f"{disagreements}/{scored} ({disagreements / scored:.2%})"
            )
        print(f"Metadata: {metadata_path}")

    return exit_status


if __name__ == "__main__":
    raise SystemExit(main())
