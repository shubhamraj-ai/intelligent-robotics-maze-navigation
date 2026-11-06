"""Compare two simple-perceptron H5 models on the same recorded JPEG sequence.

Offline only: no CoppeliaSim connection and no motor commands.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.step06_simple_perceptron_navigation.core import (
    LABELS,
    load_dense_softmax_h5,
    predict_bgr_frame,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--baseline-model", required=True, type=Path)
    p.add_argument("--candidate-model", required=True, type=Path)
    p.add_argument("--frame-dir", required=True, type=Path)
    p.add_argument("--output-csv", required=True, type=Path)
    return p.parse_args()


def transitions(labels: list[str]) -> list[tuple[int, str, str]]:
    result = []
    for i in range(1, len(labels)):
        if labels[i] != labels[i - 1]:
            result.append((i + 1, labels[i - 1], labels[i]))
    return result


def longest_run(labels: list[str], target: str) -> int:
    best = 0
    current = 0
    for label in labels:
        if label == target:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def main() -> int:
    args = parse_args()
    baseline = load_dense_softmax_h5(args.baseline_model)
    candidate = load_dense_softmax_h5(args.candidate_model)

    frames = sorted(args.frame_dir.glob("*.jpg"))
    if not frames:
        raise RuntimeError(f"No JPEGs found in {args.frame_dir}")

    rows = []
    baseline_labels = []
    candidate_labels = []

    for index, path in enumerate(frames, start=1):
        frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if frame is None:
            raise RuntimeError(f"Unreadable JPEG: {path}")

        b_label, b_prob = predict_bgr_frame(baseline, frame)
        c_label, c_prob = predict_bgr_frame(candidate, frame)
        baseline_labels.append(b_label)
        candidate_labels.append(c_label)

        rows.append(
            {
                "index": index,
                "frame": path.name,
                "baseline_label": b_label,
                "baseline_forward": float(b_prob[0]),
                "baseline_left": float(b_prob[1]),
                "baseline_right": float(b_prob[2]),
                "candidate_label": c_label,
                "candidate_forward": float(c_prob[0]),
                "candidate_left": float(c_prob[1]),
                "candidate_right": float(c_prob[2]),
                "label_changed": b_label != c_label,
            }
        )

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with args.output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    changed = sum(int(row["label_changed"]) for row in rows)

    print("STEP05_MODEL_REPLAY_COMPARISON_COMPLETE")
    print(f"Frames: {len(frames)}")
    print(f"Changed labels candidate-vs-baseline: {changed}")
    print(
        "Baseline counts: "
        + ", ".join(
            f"{label}={baseline_labels.count(label)}" for label in LABELS
        )
    )
    print(
        "Candidate counts: "
        + ", ".join(
            f"{label}={candidate_labels.count(label)}" for label in LABELS
        )
    )
    print(f"Baseline longest-left-run: {longest_run(baseline_labels, 'left')}")
    print(f"Candidate longest-left-run: {longest_run(candidate_labels, 'left')}")

    print("Baseline transitions:")
    for index, before, after in transitions(baseline_labels):
        print(f"  pulse {index}: {before} -> {after}")

    print("Candidate transitions:")
    for index, before, after in transitions(candidate_labels):
        print(f"  pulse {index}: {before} -> {after}")

    print("Changed frames:")
    for row in rows:
        if row["label_changed"]:
            print(
                f"  {row['index']:3d} {row['frame']}: "
                f"{row['baseline_label']} -> {row['candidate_label']} | "
                f"candidate F={row['candidate_forward']:.4f} "
                f"L={row['candidate_left']:.4f} "
                f"R={row['candidate_right']:.4f}"
            )

    print(f"CSV={args.output_csv}")
    print("No simulator connection was opened.")
    print("No motor command was sent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
