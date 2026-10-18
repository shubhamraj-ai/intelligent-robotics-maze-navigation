"""Collect fresh live states for targeted forward->right hard-negative remediation.

The human controls W/A/D. The alpha-0.50 CNN remains shadow-only. Every nonblank
camera frame is saved with human command, model probabilities, pose, and an
explicit forward->right marker so sustained false-right blocks can be reviewed
and converted into retraining data without touching the accepted datasets.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


CLASS_NAMES = ("forward", "left", "right")
FORWARD_SPEED = 2.0
TURN_SPEED = 2.0
LOOP_INTERVAL_SECONDS = 0.10
CAMERA_PATH = "/PioneerP3DX/cam1"
MODEL_IMAGE_SIZE = (50, 50)
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "hard_negative_sessions"
HIGH_CONFIDENCE_THRESHOLD = 0.90


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Human-controlled alpha-0.50 shadow collection for targeted "
            "forward->right hard-negative remediation."
        )
    )
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
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
    if not all(isinstance(value, int) and value > 0 for value in resolution):
        raise ValueError(f"Camera resolution must contain positive integers: {resolution}")
    expected = width * height * 3
    if len(raw_image) != expected:
        raise ValueError(f"Expected {expected} RGB bytes, received {len(raw_image)}")
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
            print(f"HARD-NEGATIVE CLEANUP ERROR: {error}", file=sys.stderr)
    return ok


def summarize_rows(rows):
    scored = [row for row in rows if row["human_command"] in CLASS_NAMES]
    false_right = [
        row
        for row in scored
        if row["human_command"] == "forward"
        and row["prediction"] == "right"
    ]
    high_conf_false_right = [
        row for row in false_right if float(row["confidence"]) >= HIGH_CONFIDENCE_THRESHOLD
    ]

    longest = 0
    longest_high = 0
    current = 0
    current_high = 0
    events = []
    event_start = None

    for index, row in enumerate(scored):
        is_false_right = (
            row["human_command"] == "forward" and row["prediction"] == "right"
        )
        if is_false_right:
            current += 1
            longest = max(longest, current)
            if float(row["confidence"]) >= HIGH_CONFIDENCE_THRESHOLD:
                current_high += 1
                longest_high = max(longest_high, current_high)
            else:
                current_high = 0
            if event_start is None:
                event_start = index
        else:
            current = 0
            current_high = 0
            if event_start is not None:
                events.append(scored[event_start:index])
                event_start = None

    if event_start is not None:
        events.append(scored[event_start:])

    event_summaries = []
    for event_rows in events:
        if not event_rows:
            continue
        conf = [float(row["confidence"]) for row in event_rows]
        event_summaries.append(
            {
                "frames": len(event_rows),
                "start_s": float(event_rows[0]["elapsed_seconds"]),
                "end_s": float(event_rows[-1]["elapsed_seconds"]),
                "mean_confidence": sum(conf) / len(conf),
                "max_confidence": max(conf),
                "first_frame_index": int(event_rows[0]["frame_index"]),
                "last_frame_index": int(event_rows[-1]["frame_index"]),
            }
        )
    event_summaries.sort(key=lambda item: item["frames"], reverse=True)

    return {
        "total_frames": len(rows),
        "scored_frames": len(scored),
        "false_right_frames": len(false_right),
        "high_conf_false_right_frames": len(high_conf_false_right),
        "longest_false_right_streak": longest,
        "longest_high_conf_false_right_streak": longest_high,
        "events": event_summaries,
    }


def build_summary_text(summary):
    scored = summary["scored_frames"]
    false_right = summary["false_right_frames"]
    lines = [
        "STEP 5E TARGETED HARD-NEGATIVE COLLECTION SUMMARY",
        "",
        f"Total saved frames: {summary['total_frames']}",
        f"Scored stable-command frames: {scored}",
        f"Human-forward/model-right frames: {false_right}",
        (
            "Forward->right fraction of scored frames: "
            f"{(false_right / scored if scored else 0.0):.2%}"
        ),
        (
            f"High-confidence (>= {HIGH_CONFIDENCE_THRESHOLD:.2f}) "
            f"forward->right frames: {summary['high_conf_false_right_frames']}"
        ),
        f"Longest forward->right streak: {summary['longest_false_right_streak']} frames",
        (
            "Longest high-confidence forward->right streak: "
            f"{summary['longest_high_conf_false_right_streak']} frames"
        ),
        "",
        "Top forward->right events:",
    ]
    for index, event in enumerate(summary["events"][:10], start=1):
        lines.append(
            f"{index}. frames={event['frames']}, "
            f"time={event['start_s']:.3f}-{event['end_s']:.3f}s, "
            f"mean_conf={event['mean_confidence']:.3f}, "
            f"max_conf={event['max_confidence']:.3f}, "
            f"frame_index={event['first_frame_index']}-{event['last_frame_index']}"
        )
    if not summary["events"]:
        lines.append("No forward->right events detected.")
    lines.extend(
        [
            "",
            "Every nonblank live frame was retained, so pre/post-event context is",
            "available directly from adjacent frame_index values in metadata.csv.",
            "The CNN never actuated the motors.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv=None):
    args = parse_args(argv)
    model_path = args.model.resolve()
    output_root = args.output_root.resolve()

    sim = None
    left_motor = right_motor = None
    csv_file = None
    exit_status = 0
    rows = []

    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    session_dir = output_root / f"hardneg_{run_stamp}"
    frames_dir = session_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=False)
    metadata_path = session_dir / "metadata.csv"
    summary_path = session_dir / "summary.txt"

    try:
        if not model_path.is_file():
            raise FileNotFoundError(f"Model not found: {model_path}")

        print("STEP 5E - Targeted Hard-Negative Collection")
        print("W=forward, A=left, D=right; release keys to stop.")
        print("Human controls motors. Alpha-0.50 CNN is shadow-only.")
        print("OpenCV GUI display is disabled for simulator stability.")
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
        robot = sim.getObject("/PioneerP3DX")
        left_motor = sim.getObject("/PioneerP3DX/leftMotor")
        right_motor = sim.getObject("/PioneerP3DX/rightMotor")
        camera = sim.getObject(CAMERA_PATH)
        stop_motors(sim, left_motor, right_motor)

        csv_file = metadata_path.open("w", newline="", encoding="utf-8")
        fieldnames = [
            "timestamp_utc",
            "elapsed_seconds",
            "frame_index",
            "human_command",
            "prediction",
            "forward_probability",
            "left_probability",
            "right_probability",
            "confidence",
            "agreement",
            "forward_to_right",
            "high_conf_forward_to_right",
            "image_relative_path",
            "robot_x",
            "robot_y",
            "robot_yaw",
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        csv_file.flush()

        print("READY: collector initialized. Start/resume CoppeliaSim.", flush=True)
        while sim.getSimulationState() in (
            sim.simulation_stopped,
            sim.simulation_paused,
        ):
            time.sleep(0.10)

        print(
            "SIMULATION RUNNING — W/A/D control + hard-negative capture active.",
            flush=True,
        )
        run_started = time.monotonic()
        frame_index = 0

        while True:
            loop_started = time.monotonic()
            if sim.getSimulationState() in (
                sim.simulation_stopped,
                sim.simulation_paused,
            ):
                print("Simulation stopped; ending hard-negative session.", flush=True)
                break

            before_label, left_velocity, right_velocity = get_human_command(keyboard)
            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)

            raw_image, resolution = sim.getVisionSensorImg(camera)
            frame_rgb = convert_raw_image_rgb(raw_image, resolution, np)
            if not np.any(frame_rgb):
                stop_motors(sim, left_motor, right_motor)
                time.sleep(LOOP_INTERVAL_SECONDS)
                continue

            probabilities = model(
                preprocess_for_model(frame_rgb, tf), training=False
            ).numpy()[0]
            pred_index = int(np.argmax(probabilities))
            prediction = CLASS_NAMES[pred_index]
            confidence = float(probabilities[pred_index])

            after_label, left_velocity, right_velocity = get_human_command(keyboard)
            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)
            stable_label = (
                before_label
                if before_label is not None and after_label == before_label
                else None
            )

            now = time.monotonic()
            elapsed = now - run_started
            timestamp = datetime.now(timezone.utc)
            position = sim.getObjectPosition(robot, sim.handle_world)
            yaw = sim.getObjectOrientation(robot, sim.handle_world)[2]

            frame_index += 1
            image_name = (
                f"frame_{frame_index:06d}_"
                f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.jpg"
            )
            image_path = frames_dir / image_name
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            if not cv2.imwrite(str(image_path), frame_bgr):
                raise RuntimeError(f"Could not save {image_path}")

            forward_to_right = (
                stable_label == "forward" and prediction == "right"
            )
            high_conf_forward_to_right = (
                forward_to_right and confidence >= HIGH_CONFIDENCE_THRESHOLD
            )
            agreement = (
                ""
                if stable_label is None
                else ("1" if stable_label == prediction else "0")
            )

            row = {
                "timestamp_utc": timestamp.isoformat(),
                "elapsed_seconds": f"{elapsed:.3f}",
                "frame_index": str(frame_index),
                "human_command": stable_label or "",
                "prediction": prediction,
                "forward_probability": f"{float(probabilities[0]):.6f}",
                "left_probability": f"{float(probabilities[1]):.6f}",
                "right_probability": f"{float(probabilities[2]):.6f}",
                "confidence": f"{confidence:.6f}",
                "agreement": agreement,
                "forward_to_right": "1" if forward_to_right else "0",
                "high_conf_forward_to_right": (
                    "1" if high_conf_forward_to_right else "0"
                ),
                "image_relative_path": str(image_path.relative_to(session_dir)),
                "robot_x": f"{float(position[0]):.6f}",
                "robot_y": f"{float(position[1]):.6f}",
                "robot_yaw": f"{float(yaw):.6f}",
            }
            writer.writerow(row)
            csv_file.flush()
            rows.append(row)

            if frame_index == 1 or frame_index % 50 == 0:
                print(
                    f"t={elapsed:.1f}s frames={frame_index} "
                    f"human={stable_label or 'none':<7} "
                    f"model={prediction:<7} conf={confidence:.3f} "
                    f"false_right={forward_to_right}",
                    flush=True,
                )

            remaining = LOOP_INTERVAL_SECONDS - (time.monotonic() - loop_started)
            if remaining > 0:
                time.sleep(remaining)

    except KeyboardInterrupt:
        print("Hard-negative collection stopped by user.", flush=True)
    except Exception as error:
        print(f"HARD-NEGATIVE COLLECTION ERROR: {error}", file=sys.stderr, flush=True)
        exit_status = 1
    finally:
        if sim is not None and not stop_motors(sim, left_motor, right_motor):
            exit_status = 1
        if csv_file is not None:
            csv_file.close()

        summary = summarize_rows(rows)
        summary_path.write_text(build_summary_text(summary), encoding="utf-8")
        print(build_summary_text(summary), end="", flush=True)
        print(f"Metadata: {metadata_path}", flush=True)
        print(f"Summary: {summary_path}", flush=True)

    return exit_status


if __name__ == "__main__":
    raise SystemExit(main())
