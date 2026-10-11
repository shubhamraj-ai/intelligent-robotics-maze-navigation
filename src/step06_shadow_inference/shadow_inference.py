"""Compare live CNN predictions with human W/A/D driving without model actuation."""

from __future__ import annotations

import argparse
import csv
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
DEFAULT_MODEL_PATH = REPO_ROOT / "models" / "maze_navigation_model_v2.h5"
DEFAULT_LOG_ROOT = REPO_ROOT / "shadow_logs"


@dataclass
class ShadowMetrics:
    """Accumulate confusion counts and disagreement streaks for scored frames."""

    confusion: list[list[int]] = field(
        default_factory=lambda: [[0 for _ in CLASS_NAMES] for _ in CLASS_NAMES]
    )
    total_scored: int = 0
    total_agree: int = 0
    false_left_streak: int = 0
    longest_false_left_streak: int = 0
    disagreement_streak: int = 0
    longest_disagreement_streak: int = 0

    def update(self, human_label: str, predicted_label: str) -> None:
        human_index = CLASS_TO_INDEX[human_label]
        predicted_index = CLASS_TO_INDEX[predicted_label]
        self.confusion[human_index][predicted_index] += 1
        self.total_scored += 1

        if human_label == predicted_label:
            self.total_agree += 1
            self.disagreement_streak = 0
        else:
            self.disagreement_streak += 1
            self.longest_disagreement_streak = max(
                self.longest_disagreement_streak, self.disagreement_streak
            )

        if human_label == "forward" and predicted_label == "left":
            self.false_left_streak += 1
            self.longest_false_left_streak = max(
                self.longest_false_left_streak, self.false_left_streak
            )
        else:
            self.false_left_streak = 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Human drives with W/A/D while the trained CNN predicts in shadow mode. "
            "The CNN never commands the motors in this program."
        )
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL_PATH,
        help=f"Path to the trained .h5 model (default: {DEFAULT_MODEL_PATH})",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_ROOT,
        help=f"Directory for CSV/summary output (default: {DEFAULT_LOG_ROOT})",
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Disable the OpenCV preview window while keeping console/log output.",
    )
    return parser.parse_args(argv)


def get_human_command(keyboard_module):
    """Return one unambiguous W/A/D command and its manual wheel velocities."""
    held = [key for key in ("w", "a", "d") if keyboard_module.is_pressed(key)]
    if len(held) != 1:
        return None, 0.0, 0.0
    if held[0] == "w":
        return "forward", FORWARD_SPEED, FORWARD_SPEED
    if held[0] == "a":
        return "left", -TURN_SPEED, TURN_SPEED
    return "right", TURN_SPEED, -TURN_SPEED


def convert_raw_image_rgb(raw_image, resolution, np_module):
    """Validate CoppeliaSim's bottom-up RGB buffer and return top-down RGB."""
    if len(resolution) != 2:
        raise ValueError(f"Expected [width, height], received {resolution}")
    width, height = resolution
    if not all(isinstance(value, int) and value > 0 for value in resolution):
        raise ValueError(f"Camera resolution must contain positive integers: {resolution}")
    expected_bytes = width * height * 3
    if len(raw_image) != expected_bytes:
        raise ValueError(f"Expected {expected_bytes} RGB bytes, received {len(raw_image)}")
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
    """Fail fast if the loaded model is incompatible with the Step-5 contract."""
    input_shape = tuple(model.input_shape)
    output_shape = tuple(model.output_shape)
    expected_input = (None, MODEL_IMAGE_SIZE[0], MODEL_IMAGE_SIZE[1], 3)
    expected_output = (None, len(CLASS_NAMES))
    if input_shape != expected_input:
        raise ValueError(f"Unexpected model input shape {input_shape}; expected {expected_input}")
    if output_shape != expected_output:
        raise ValueError(f"Unexpected model output shape {output_shape}; expected {expected_output}")


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
            print(f"STEP 6A CLEANUP ERROR: Could not stop a motor: {error}", file=sys.stderr)
    return succeeded


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def build_summary(metrics: ShadowMetrics) -> str:
    """Build a human-readable shadow-validation summary from confusion counts."""
    lines = [
        "STEP 6A SHADOW VALIDATION SUMMARY",
        "",
        f"Scored frames: {metrics.total_scored}",
        f"Agreement: {metrics.total_agree}",
        f"Agreement rate: {_safe_ratio(metrics.total_agree, metrics.total_scored):.2%}",
        f"Longest disagreement streak: {metrics.longest_disagreement_streak}",
        f"Longest false-left streak while human=forward: {metrics.longest_false_left_streak}",
        "",
        "Confusion matrix (rows=human command, columns=model prediction):",
        "               forward    left   right",
    ]
    for row_name, row in zip(CLASS_NAMES, metrics.confusion):
        lines.append(f"{row_name:>8} {row[0]:10d} {row[1]:7d} {row[2]:7d}")

    lines.extend(["", "Per-class shadow metrics:"])
    for index, name in enumerate(CLASS_NAMES):
        true_positive = metrics.confusion[index][index]
        actual_total = sum(metrics.confusion[index])
        predicted_total = sum(row[index] for row in metrics.confusion)
        recall = _safe_ratio(true_positive, actual_total)
        precision = _safe_ratio(true_positive, predicted_total)
        f1 = _safe_ratio(2 * precision * recall, precision + recall)
        lines.append(
            f"{name}: precision={precision:.2%}, recall={recall:.2%}, f1={f1:.2%}, "
            f"support={actual_total}"
        )

    forward_total = sum(metrics.confusion[CLASS_TO_INDEX["forward"]])
    false_left = metrics.confusion[CLASS_TO_INDEX["forward"]][CLASS_TO_INDEX["left"]]
    lines.extend(
        [
            "",
            f"False-left frames while human=forward: {false_left}/{forward_total} "
            f"({_safe_ratio(false_left, forward_total):.2%})",
            "",
            "Interpretation note: only frames with one stable human W/A/D command are scored.",
            "Frames with no key or ambiguous simultaneous keys are logged but excluded from metrics.",
            "The CNN never actuates the motors in this shadow-mode program.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    model_path = args.model.resolve()
    log_dir = args.log_dir.resolve()

    print("STEP 6A - CNN Shadow Validation")
    print("W - Forward; A - Left; D - Right; release keys to stop.")
    print("IMPORTANT: The HUMAN keyboard command controls the motors.")
    print("IMPORTANT: The CNN predicts only; it NEVER controls the motors in this program.")
    print(f"Model: {model_path}")

    sim = None
    cv2 = None
    left_motor = None
    right_motor = None
    csv_file = None
    exit_status = 0
    metrics = ShadowMetrics()

    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir.mkdir(parents=True, exist_ok=True)
    csv_path = log_dir / f"shadow_{run_stamp}.csv"
    summary_path = log_dir / f"shadow_{run_stamp}_summary.txt"

    try:
        if not model_path.is_file() or model_path.stat().st_size == 0:
            raise FileNotFoundError(f"Trained model not found: {model_path}")

        print(
            "Startup 1/4: importing TensorFlow and runtime libraries. "
            "This can take 15-30 seconds on this laptop; W/A/D is NOT active yet.",
            flush=True,
        )
        import cv2
        import keyboard
        import numpy as np
        import tensorflow as tf
        from coppeliasim_zmqremoteapi_client import RemoteAPIClient

        print(f"Startup 2/4: TensorFlow {tf.__version__} loaded. Loading CNN model...", flush=True)
        model = tf.keras.models.load_model(str(model_path), compile=False)
        validate_model_contract(model)
        print(f"Model contract: input={model.input_shape}, output={model.output_shape}", flush=True)
        print("Class mapping: forward=0, left=1, right=2", flush=True)
        # Warm the tiny CNN before human driving so first-use graph setup cannot delay motor updates.
        print("Startup 3/4: warming the CNN once before driving...", flush=True)
        model(
            tf.zeros((1, MODEL_IMAGE_SIZE[0], MODEL_IMAGE_SIZE[1], 3), dtype=tf.float32),
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

        csv_file = csv_path.open("w", newline="", encoding="utf-8")
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "timestamp_utc",
                "elapsed_seconds",
                "human_command",
                "predicted_command",
                "forward_probability",
                "left_probability",
                "right_probability",
                "confidence",
                "scored",
                "agreement",
            ]
        )

        print(
            "READY: shadow validator is initialized. Start/resume the CoppeliaSim simulation now. "
            "W/A/D becomes active only after the program detects SIMULATION RUNNING.",
            flush=True,
        )
        waiting_message_printed = False
        while sim.getSimulationState() in (sim.simulation_stopped, sim.simulation_paused):
            if not waiting_message_printed:
                print("Waiting for CoppeliaSim simulation to run...", flush=True)
                waiting_message_printed = True
            time.sleep(0.10)

        print(
            "SIMULATION RUNNING DETECTED — W/A/D MANUAL CONTROL IS ACTIVE NOW. "
            "CNN remains shadow-only.",
            flush=True,
        )

        run_started = time.monotonic()
        last_print = 0.0
        resolution_printed = False
        blank_frame_noted = False

        while True:
            loop_started = time.monotonic()
            if sim.getSimulationState() in (sim.simulation_stopped, sim.simulation_paused):
                print(
                    "Simulation stopped/paused; ending this shadow run and writing the summary.",
                    flush=True,
                )
                break

            before_label, left_velocity, right_velocity = get_human_command(keyboard)
            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)

            raw_image, resolution = sim.getVisionSensorImg(handles[CAMERA_PATH])
            frame_rgb = convert_raw_image_rgb(raw_image, resolution, np)
            if not resolution_printed:
                print(f"Live camera resolution: {resolution[0]} x {resolution[1]}")
                resolution_printed = True

            # CoppeliaSim can expose an all-zero camera buffer during the first sensor cycle.
            # Do not score that transient frame as a model decision.
            if not np.any(frame_rgb):
                if not blank_frame_noted:
                    print("Waiting for the first non-blank camera frame...")
                    blank_frame_noted = True
                _, left_velocity, right_velocity = get_human_command(keyboard)
                sim.setJointTargetVelocity(left_motor, left_velocity)
                sim.setJointTargetVelocity(right_motor, right_velocity)
                remaining = LOOP_INTERVAL_SECONDS - (time.monotonic() - loop_started)
                if remaining > 0:
                    time.sleep(remaining)
                continue

            model_input = preprocess_for_model(frame_rgb, tf)
            probabilities = model(model_input, training=False).numpy()[0]
            predicted_index = int(np.argmax(probabilities))
            predicted_label = CLASS_NAMES[predicted_index]
            confidence = float(probabilities[predicted_index])

            after_label, left_velocity, right_velocity = get_human_command(keyboard)
            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)

            scored_label = (
                before_label
                if before_label is not None and after_label == before_label
                else None
            )
            agreement = None
            if scored_label is not None:
                metrics.update(scored_label, predicted_label)
                agreement = scored_label == predicted_label

            elapsed = time.monotonic() - run_started
            writer.writerow(
                [
                    datetime.now(timezone.utc).isoformat(),
                    f"{elapsed:.3f}",
                    scored_label or "",
                    predicted_label,
                    f"{float(probabilities[0]):.6f}",
                    f"{float(probabilities[1]):.6f}",
                    f"{float(probabilities[2]):.6f}",
                    f"{confidence:.6f}",
                    "1" if scored_label is not None else "0",
                    "" if agreement is None else ("1" if agreement else "0"),
                ]
            )
            csv_file.flush()

            if not args.no_display:
                frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                human_text = after_label or "none/ambiguous"
                cv2.putText(
                    frame_bgr,
                    f"HUMAN: {human_text}",
                    (3, 12),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.32,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    frame_bgr,
                    f"MODEL: {predicted_label} {confidence:.2f}",
                    (3, 24),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.32,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    frame_bgr,
                    "SHADOW ONLY",
                    (3, 36),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.32,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow("Step 6A - Human vs CNN Shadow Validation", frame_bgr)
                cv2.waitKey(1)

            now = time.monotonic()
            if scored_label is not None and now - last_print >= PRINT_INTERVAL_SECONDS:
                print(
                    f"human={scored_label:<7} model={predicted_label:<7} "
                    f"confidence={confidence:.3f} agree={agreement}"
                )
                last_print = now

            remaining = LOOP_INTERVAL_SECONDS - (time.monotonic() - loop_started)
            if remaining > 0:
                time.sleep(remaining)

    except KeyboardInterrupt:
        print("\nShadow validation stopped by user.")
    except Exception as error:
        print(f"STEP 6A ERROR: {error}", file=sys.stderr)
        exit_status = 1
    finally:
        if sim is not None and not stop_motors(sim, left_motor, right_motor):
            exit_status = 1
        if csv_file is not None:
            csv_file.close()
        if cv2 is not None:
            try:
                cv2.destroyAllWindows()
            except Exception as error:
                print(
                    f"STEP 6A CLEANUP ERROR: Could not close OpenCV windows: {error}",
                    file=sys.stderr,
                )
                exit_status = 1

        summary = build_summary(metrics)
        try:
            summary_path.write_text(summary, encoding="utf-8")
            print(summary, end="")
            print(f"CSV log: {csv_path}")
            print(f"Summary: {summary_path}")
        except Exception as error:
            print(
                f"STEP 6A CLEANUP ERROR: Could not save summary: {error}",
                file=sys.stderr,
            )
            exit_status = 1

    return exit_status


if __name__ == "__main__":
    sys.exit(main())
