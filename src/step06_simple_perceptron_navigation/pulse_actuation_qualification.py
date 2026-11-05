"""Bounded Step-6 pulse-actuation qualification.

This is a safety qualification gate, not the final continuous autonomous runtime.

For each new scene-owned JPEG:
1. run the final simple-perceptron prediction;
2. map the label to the locked 1.00 / 0.10 / 1.00 wheel speeds;
3. apply that command for a short bounded wall-clock pulse;
4. stop both motors immediately;
5. wait stationary for the next fresh JPEG.

Camera acquisition remains owned by the existing stable Step-4 Lua save-only
script. Python never reads camera bytes from CoppeliaSim.
"""

from __future__ import annotations

import argparse
import csv
import time
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


DEFAULT_PULSE_SECONDS = 0.25
MAX_QUALIFICATION_PULSE_SECONDS = 0.50


def validate_pulse_seconds(value: float) -> float:
    value = float(value)
    if value <= 0.0:
        raise ValueError("pulse_seconds must be > 0")
    if value > MAX_QUALIFICATION_PULSE_SECONDS:
        raise ValueError(
            "pulse_seconds exceeds the bounded qualification limit "
            f"({MAX_QUALIFICATION_PULSE_SECONDS:.2f}s)"
        )
    return value


def should_stop_after_label(label: str, stop_on_turn: bool) -> bool:
    return bool(stop_on_turn and label in {"left", "right"})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run bounded simple-perceptron motor pulses from fresh JPEGs."
    )
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--frame-dir", required=True, type=Path)
    parser.add_argument("--frame-glob", default=DEFAULT_FRAME_GLOB)
    parser.add_argument("--max-pulses", type=int, default=3)
    parser.add_argument(
        "--pulse-seconds",
        type=float,
        default=DEFAULT_PULSE_SECONDS,
    )
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument(
        "--stop-on-turn",
        action="store_true",
        help="Exit cleanly immediately after the first bounded left/right pulse.",
    )
    parser.add_argument("--log-csv", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_pulses <= 0:
        raise ValueError("--max-pulses must be > 0")
    pulse_seconds = validate_pulse_seconds(args.pulse_seconds)

    metadata = validate_step5_metadata(args.metadata)
    model = load_dense_softmax_h5(args.model)
    profile = load_locked_motion_profile()

    watcher = JpegFrameWatcher(
        args.frame_dir,
        pattern=args.frame_glob,
        poll_seconds=profile["control_interval_seconds"],
    )

    from coppeliasim_zmqremoteapi_client import RemoteAPIClient

    args.log_csv.parent.mkdir(parents=True, exist_ok=True)
    log_handle = args.log_csv.open("w", newline="", encoding="utf-8")
    log_writer = csv.writer(log_handle)
    log_writer.writerow(
        [
            "timestamp_local",
            "frame",
            "forward_probability",
            "left_probability",
            "right_probability",
            "prediction",
            "left_velocity",
            "right_velocity",
            "pulse_seconds",
            "motors_stopped_after_pulse",
            "robot_x",
            "robot_y",
            "robot_z",
            "robot_yaw",
        ]
    )

    sim = None
    left_motor = None
    right_motor = None
    last_command = None
    completed = 0

    try:
        client = RemoteAPIClient()
        sim = client.require("sim")

        if sim.getSimulationState() == sim.simulation_stopped:
            raise RuntimeError(
                "Simulation is stopped. Start the unchanged stable scene first."
            )

        robot = sim.getObject("/PioneerP3DX")
        left_motor = sim.getObject("/PioneerP3DX/leftMotor")
        right_motor = sim.getObject("/PioneerP3DX/rightMotor")
        if min(robot, left_motor, right_motor) < 0:
            raise RuntimeError("Could not resolve PioneerP3DX robot/motor objects")

        last_command = apply_motor_command_if_changed(
            sim,
            left_motor,
            right_motor,
            0.0,
            0.0,
            last_command,
        )

        enable_existing_step4_capture(sim)

        print("STEP6_PULSE_ACTUATION_READY")
        print("Camera source: unchanged persistent Step-4 Lua save-only path.")
        print(
            "Qualification pulse: "
            f"{pulse_seconds:.2f}s; maximum permitted="
            f"{MAX_QUALIFICATION_PULSE_SECONDS:.2f}s."
        )
        print("Robot is stopped between every fresh-frame decision.")
        print("Pose is logged for diagnostics only and never used for control.")
        print("No confidence threshold, smoothing, commitment timer, or route logic.")

        start_position = sim.getObjectPosition(robot, sim.handle_world)
        start_orientation = sim.getObjectOrientation(robot, sim.handle_world)
        print(
            "START_POSE "
            f"x={float(start_position[0]):.6f} "
            f"y={float(start_position[1]):.6f} "
            f"z={float(start_position[2]):.6f} "
            f"yaw={float(start_orientation[2]):.6f}"
        )

        for index in range(1, args.max_pulses + 1):
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

            time.sleep(pulse_seconds)

            last_command = apply_motor_command_if_changed(
                sim,
                left_motor,
                right_motor,
                0.0,
                0.0,
                last_command,
            )
            completed += 1

            position = sim.getObjectPosition(robot, sim.handle_world)
            orientation = sim.getObjectOrientation(robot, sim.handle_world)

            probability_text = ", ".join(
                f"{name}={float(value):.6f}"
                for name, value in zip(metadata["labels"], probabilities)
            )
            print(
                f"PULSE {index}: {record.path.name} -> {label}; "
                f"{probability_text}; "
                f"command=({left_velocity:.2f},{right_velocity:.2f}); "
                f"duration={pulse_seconds:.2f}s; STOPPED; "
                f"pose=({float(position[0]):.4f},{float(position[1]):.4f},"
                f"{float(position[2]):.4f}); yaw={float(orientation[2]):.4f}"
            )

            log_writer.writerow(
                [
                    datetime.now().astimezone().isoformat(timespec="milliseconds"),
                    record.path.name,
                    *[f"{float(value):.9f}" for value in probabilities],
                    label,
                    f"{left_velocity:.6f}",
                    f"{right_velocity:.6f}",
                    f"{pulse_seconds:.6f}",
                    "true",
                    f"{float(position[0]):.9f}",
                    f"{float(position[1]):.9f}",
                    f"{float(position[2]):.9f}",
                    f"{float(orientation[2]):.9f}",
                ]
            )
            log_handle.flush()

            if should_stop_after_label(label, args.stop_on_turn):
                print(
                    "STEP6_FIRST_TURN_DETECTED "
                    f"pulse={index} label={label} frame={record.path.name}"
                )
                break

    except KeyboardInterrupt:
        print("STEP6_PULSE_ACTUATION_INTERRUPTED")
    finally:
        try:
            log_handle.close()
        finally:
            if sim is not None:
                disable_existing_step4_capture(sim)
                stop_motors(sim, left_motor, right_motor)

    print(f"STEP6_PULSE_ACTUATION_COMPLETE pulses={completed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
