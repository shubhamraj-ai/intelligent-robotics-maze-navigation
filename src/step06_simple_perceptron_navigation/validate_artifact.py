"""Offline acceptance harness for the final Step-6 simple-perceptron core.

This tool does not connect to CoppeliaSim and does not command motors.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import cv2

from src.step06_simple_perceptron_navigation.core import (
    load_dense_softmax_h5,
    load_locked_motion_profile,
    predict_bgr_frame,
    validate_step5_metadata,
    wheel_command_for_label,
)


EXPECTED_H5_SHA256 = (
    "a2ffb9258ef3527b7deadf6d4c5d137b356d573ecfec621c207f84997d976751"
)
EXPECTED_JSON_SHA256 = (
    "7a3d0fb11edcd63bba5f9301524016a9a0e79bf1fdf846a64d1fe139ab4f47e1"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the final Step-5 artifacts for Step-6 NumPy inference."
    )
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument(
        "--image",
        type=Path,
        help="Optional 50x50 JPEG for one offline prediction.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    model_hash = sha256(args.model)
    metadata_hash = sha256(args.metadata)
    if model_hash != EXPECTED_H5_SHA256:
        raise RuntimeError(
            f"Unexpected H5 SHA256: {model_hash} != {EXPECTED_H5_SHA256}"
        )
    if metadata_hash != EXPECTED_JSON_SHA256:
        raise RuntimeError(
            f"Unexpected JSON SHA256: {metadata_hash} != {EXPECTED_JSON_SHA256}"
        )

    metadata = validate_step5_metadata(args.metadata)
    model = load_dense_softmax_h5(args.model)
    profile = load_locked_motion_profile()

    print("STEP6_SIMPLE_PERCEPTRON_ARTIFACT_GATE_PASS")
    print(f"Architecture : {metadata['architecture']}")
    print(f"Labels       : {metadata['labels']}")
    print(
        "Motion       : "
        f"forward={profile['forward_speed']:.2f}, "
        f"inner={profile['turn_inner_speed']:.2f}, "
        f"outer={profile['turn_outer_speed']:.2f}"
    )
    print(f"H5 SHA256    : {model_hash}")
    print(f"JSON SHA256  : {metadata_hash}")

    if args.image is not None:
        frame = cv2.imread(str(args.image), cv2.IMREAD_COLOR)
        if frame is None:
            raise RuntimeError(f"Could not read image: {args.image}")
        label, probabilities = predict_bgr_frame(model, frame)
        left, right = wheel_command_for_label(label, profile)
        probability_text = ", ".join(
            f"{name}={float(value):.6f}"
            for name, value in zip(metadata["labels"], probabilities)
        )
        print(f"Prediction   : {label}")
        print(f"Probabilities: {probability_text}")
        print(f"Wheel target : left={left:.2f}, right={right:.2f}")

    print("No CoppeliaSim connection was opened.")
    print("No motor command was sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
