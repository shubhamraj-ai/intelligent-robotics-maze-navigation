"""First live AirGPU gate: reuse exact stable Step-4 capture, no motors.

This wrapper connects only to publish/clear the already-proven tiny
`step4_capture_label` string signal. The existing persistent scene-owned Lua
script continues to own camera reads and JPEG saves.

No motor object is resolved and no motor command can be sent by this program.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src.step06_simple_perceptron_navigation.capture_bridge import (
    disable_existing_step4_capture,
    enable_existing_step4_capture,
)
from src.step06_simple_perceptron_navigation.core import (
    load_dense_softmax_h5,
    load_locked_motion_profile,
    predict_bgr_frame,
    validate_step5_metadata,
    wheel_command_for_label,
)
from src.step06_simple_perceptron_navigation.frame_source import (
    DEFAULT_FRAME_GLOB,
    JpegFrameWatcher,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Observe the final simple perceptron using the proven Step-4 "
            "persistent camera-save path, without motor actuation."
        )
    )
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--frame-dir", required=True, type=Path)
    parser.add_argument("--frame-glob", default=DEFAULT_FRAME_GLOB)
    parser.add_argument("--max-frames", type=int, default=3)
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
        pattern=args.frame_glob,
        poll_seconds=profile["control_interval_seconds"],
    )

    from coppeliasim_zmqremoteapi_client import RemoteAPIClient

    sim = None
    try:
        client = RemoteAPIClient()
        sim = client.require("sim")

        if sim.getSimulationState() == sim.simulation_stopped:
            raise RuntimeError(
                "Simulation is stopped. Start the unchanged stable scene first."
            )

        enable_existing_step4_capture(sim)

        print("STEP6_LIVE_OBSERVE_ONLY_READY")
        print("Capture source: existing Step-4 persistent Lua save-only script.")
        print("Capture-enable token: step4_capture_label='forward'.")
        print("No motor handles are resolved; no motor command can be sent.")

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

    finally:
        if sim is not None:
            disable_existing_step4_capture(sim)

    print("STEP6_LIVE_OBSERVE_ONLY_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
