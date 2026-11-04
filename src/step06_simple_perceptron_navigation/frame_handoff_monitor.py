"""Observation-only Step-6 frame-handoff monitor.

This is the first live qualification mode. It reads scene-owned JPEGs, runs the
final simple perceptron, and prints predictions. It never connects to
CoppeliaSim and therefore cannot actuate the robot.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.step06_simple_perceptron_navigation.core import (
    load_dense_softmax_h5,
    load_locked_motion_profile,
    predict_bgr_frame,
    validate_step5_metadata,
    wheel_command_for_label,
)
from src.step06_simple_perceptron_navigation.frame_source import JpegFrameWatcher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Observe scene-owned Step-6 JPEGs without motor actuation."
    )
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--frame-dir", required=True, type=Path)
    parser.add_argument("--max-frames", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_frames <= 0:
        raise ValueError("--max-frames must be > 0")

    metadata = validate_step5_metadata(args.metadata)
    model = load_dense_softmax_h5(args.model)
    profile = load_locked_motion_profile()
    watcher = JpegFrameWatcher(
        args.frame_dir,
        poll_seconds=profile["control_interval_seconds"],
    )

    print("STEP6_OBSERVE_ONLY_READY")
    print("No CoppeliaSim connection will be opened.")
    print("No motor command can be sent by this program.")

    for index in range(1, args.max_frames + 1):
        record = watcher.wait_for_next(timeout_seconds=args.timeout_seconds)
        label, probabilities = predict_bgr_frame(model, record.frame_bgr)
        left, right = wheel_command_for_label(label, profile)
        probability_text = ", ".join(
            f"{name}={float(value):.6f}"
            for name, value in zip(metadata["labels"], probabilities)
        )
        print(
            f"FRAME {index}: {record.path.name} -> {label}; "
            f"{probability_text}; "
            f"would_command=({left:.2f},{right:.2f})"
        )

    print("STEP6_OBSERVE_ONLY_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
