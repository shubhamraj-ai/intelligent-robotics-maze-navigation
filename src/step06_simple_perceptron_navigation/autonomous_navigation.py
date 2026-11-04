"""Minimal autonomous Step-6 motor adapter for the simple perceptron.

Camera capture reuses the exact stable Step-4 persistent scene-owned Lua
save-only script. Python only publishes the proven small capture-label signal,
reads completed JPEG files, and commands the two motors.

Do not run this program until the live observation-only gate has passed.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

from src.step06_simple_perceptron_navigation.capture_bridge import (
    disable_existing_step4_capture,
    enable_existing_step4_capture,
)
from src.step06_simple_perceptron_navigation.core import (
    apply_motor_command_if_changed,
    load_dense_softmax_h5,
    load_locked_motion_profile,
    predict_bgr_frame,
    stop_motors,
    validate_step5_metadata,
    wheel_command_for_label,
)
from src.step06_simple_perceptron_navigation.frame_source import (
    DEFAULT_FRAME_GLOB,
    JpegFrameWatcher,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run minimal file-handoff simple-perceptron autonomous control."
    )
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--frame-dir", required=True, type=Path)
    parser.add_argument("--frame-glob", default=DEFAULT_FRAME_GLOB)
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--log-csv", type=Path, default=None)
    return parser.parse_args()


def open_log(path: Path | None):
    if path is None:
        return None, None
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("w", newline="", encoding="utf-8")
    writer = csv.writer(handle)
    writer.writerow(
        [
            "timestamp_local",
            "frame",
            "forward_probability",
            "left_probability",
            "right_probability",
            "prediction",
            "left_velocity",
            "right_velocity",
        ]
    )
    return handle, writer


def main() -> int:
    args = parse_args()
    if args.max_frames < 0:
        raise ValueError("--max-frames must be >= 0")

    metadata = validate_step5_metadata(args.metadata)
    model = load_dense_softmax_h5(args.model)
    profile = load_locked_motion_profile()
    watcher = JpegFrameWatcher(
        args.frame_dir,
        pattern=args.frame_glob,
        poll_seconds=profile["control_interval_seconds"],
    )

    from coppeliasim_zmqremoteapi_client import RemoteAPIClient

    sim = None
    left_motor = None
    right_motor = None
    last_command = None
    processed = 0
    log_handle = None
    log_writer = None

    try:
        client = RemoteAPIClient()
        sim = client.require("sim")

        if sim.getSimulationState() == sim.simulation_stopped:
            raise RuntimeError(
                "Simulation is stopped. Start the unchanged stable scene before "
                "launching Step 6; this program does not change simulator lifecycle."
            )

        left_motor = sim.getObject("/PioneerP3DX/leftMotor")
        right_motor = sim.getObject("/PioneerP3DX/rightMotor")
        if min(left_motor, right_motor) < 0:
            raise RuntimeError("Could not resolve PioneerP3DX motor objects")

        last_command = apply_motor_command_if_changed(
            sim,
            left_motor,
            right_motor,
            0.0,
            0.0,
            last_command,
        )

        # The watcher was created before enabling the proven Step-4 capture
        # signal, so only JPEG file versions produced after this point are used.
        enable_existing_step4_capture(sim)

        log_handle, log_writer = open_log(args.log_csv)

        print("STEP6_SIMPLE_AUTONOMOUS_READY")
        print("Camera source: unchanged persistent Step-4 Lua save-only path.")
        print("No confidence threshold, smoothing, commitment timer, or route logic.")

        while args.max_frames == 0 or processed < args.max_frames:
            record = watcher.wait_for_next(timeout_seconds=args.timeout_seconds)
            label, probabilities = predict_bgr_frame(model, record.frame_bgr)
            left_velocity, right_velocity = wheel_command_for_label(
                label,
                profile,
            )
            last_command = apply_motor_command_if_changed(
                sim,
                left_motor,
                right_motor,
                left_velocity,
                right_velocity,
                last_command,
            )
            processed += 1

            if log_writer is not None:
                log_writer.writerow(
                    [
                        datetime.now().astimezone().isoformat(timespec="milliseconds"),
                        record.path.name,
                        *[f"{float(value):.9f}" for value in probabilities],
                        label,
                        f"{left_velocity:.6f}",
                        f"{right_velocity:.6f}",
                    ]
                )
                log_handle.flush()

            probability_text = ", ".join(
                f"{name}={float(value):.4f}"
                for name, value in zip(metadata["labels"], probabilities)
            )
            print(
                f"FRAME {processed}: {record.path.name} -> {label}; "
                f"{probability_text}; "
                f"command=({left_velocity:.2f},{right_velocity:.2f})"
            )

    except KeyboardInterrupt:
        print("STEP6 INTERRUPTED")
    finally:
        if log_handle is not None:
            log_handle.close()
        if sim is not None:
            disable_existing_step4_capture(sim)
            stop_motors(sim, left_motor, right_motor)

    print(f"STEP6 SIMPLE AUTONOMOUS EXIT; frames={processed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
