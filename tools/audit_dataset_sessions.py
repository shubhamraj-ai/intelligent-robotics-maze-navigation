"""Audit temporal session structure in the Step-4 image dataset.

The current notebooks split individual frames randomly. This script exposes the
capture-session structure so later retraining can keep adjacent frames together.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
from pathlib import Path

CLASS_NAMES = ("forward", "left", "right")
DEFAULT_GAP_SECONDS = 10.0


def timestamp_from_path(path: Path) -> datetime:
    parts = path.stem.split("_")
    if len(parts) < 3:
        raise ValueError(f"Unexpected dataset filename: {path.name}")
    return datetime.strptime(parts[1], "%Y%m%dT%H%M%S%fZ")


def load_records(dataset_root: Path):
    records = []
    for label in CLASS_NAMES:
        class_dir = dataset_root / label
        for path in sorted(class_dir.glob("*.jpg")):
            records.append((timestamp_from_path(path), label, path))
    return sorted(records, key=lambda item: item[0])


def split_sessions(records, gap_seconds: float = DEFAULT_GAP_SECONDS):
    sessions = []
    current = []
    previous_time = None
    for record in records:
        timestamp = record[0]
        if (
            previous_time is not None
            and (timestamp - previous_time).total_seconds() > gap_seconds
        ):
            sessions.append(current)
            current = []
        current.append(record)
        previous_time = timestamp
    if current:
        sessions.append(current)
    return sessions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "dataset",
    )
    parser.add_argument("--gap-seconds", type=float, default=DEFAULT_GAP_SECONDS)
    args = parser.parse_args()

    records = load_records(args.dataset)
    sessions = split_sessions(records, args.gap_seconds)

    print(f"Dataset: {args.dataset.resolve()}")
    print(f"Total frames: {len(records)}")
    print(f"Detected sessions: {len(sessions)}")
    for index, session in enumerate(sessions, start=1):
        counts = Counter(label for _, label, _ in session)
        duration = (session[-1][0] - session[0][0]).total_seconds()
        print(
            f"session_{index:02d}: frames={len(session)}, duration={duration:.1f}s, "
            + ", ".join(f"{name}={counts[name]}" for name in CLASS_NAMES)
        )
        print(f"  start={session[0][0].isoformat()} end={session[-1][0].isoformat()}")

    if len(sessions) < 3:
        print("WARNING: fewer than three independent capture sessions detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
