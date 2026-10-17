"""Build the fixed session-aware Step-5C training package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

CLASS_NAMES = ("forward", "left", "right")
SESSION_GAP_SECONDS = 10.0

# Locked before v4 training. Whole sessions never cross partitions.
SPLIT_BY_SESSION = {
    "original_01": "train",
    "original_02": "train",
    "original_03": "train",
    "recovery_01": "train",
    "recovery_02": "validation",
    "recovery_03": "train",
    "recovery_04": "test",
}


def timestamp_from_original_path(path: Path) -> datetime:
    parts = path.stem.split("_")
    if len(parts) < 3:
        raise ValueError(f"Unexpected original filename: {path.name}")
    return datetime.strptime(parts[1], "%Y%m%dT%H%M%S%fZ")


def load_original_records(dataset_root: Path):
    records = []
    for label in CLASS_NAMES:
        class_dir = dataset_root / label
        if not class_dir.is_dir():
            raise FileNotFoundError(f"Missing class directory: {class_dir}")
        for path in sorted(class_dir.glob("*.jpg")):
            records.append(
                {"timestamp": timestamp_from_original_path(path), "label": label, "path": path}
            )
    return sorted(records, key=lambda row: row["timestamp"])


def split_original_sessions(records):
    sessions = []
    current = []
    previous = None
    for row in records:
        timestamp = row["timestamp"]
        if (
            previous is not None
            and (timestamp - previous).total_seconds() > SESSION_GAP_SECONDS
        ):
            sessions.append(current)
            current = []
        current.append(row)
        previous = timestamp
    if current:
        sessions.append(current)
    if len(sessions) != 3:
        raise ValueError(f"Expected 3 original sessions, detected {len(sessions)}")
    return sessions


def load_recovery_session(session_dir: Path):
    metadata_path = session_dir / "metadata.csv"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Missing recovery metadata: {metadata_path}")
    rows = []
    with metadata_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            label = row["human_command"]
            if label not in CLASS_NAMES:
                raise ValueError(f"Unexpected label {label!r} in {metadata_path}")
            image_path = session_dir / row["image_relative_path"]
            if not image_path.is_file():
                raise FileNotFoundError(f"Missing recovery image: {image_path}")
            rows.append(
                {
                    "timestamp": datetime.fromisoformat(row["timestamp_utc"]),
                    "label": label,
                    "path": image_path,
                }
            )
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_bytes(fieldnames, rows):
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def build_package(original_dataset: Path, recovery_root: Path, output_dir: Path, package_name: str):
    original_sessions = split_original_sessions(load_original_records(original_dataset))
    recovery_dirs = sorted(path for path in recovery_root.glob("recovery_*") if path.is_dir())
    if len(recovery_dirs) != 4:
        raise ValueError(f"Expected 4 recovery sessions, found {len(recovery_dirs)}")

    session_records = {
        f"original_{index:02d}": rows
        for index, rows in enumerate(original_sessions, start=1)
    }
    session_records.update(
        {
            f"recovery_{index:02d}": load_recovery_session(session_dir)
            for index, session_dir in enumerate(recovery_dirs, start=1)
        }
    )
    if set(session_records) != set(SPLIT_BY_SESSION):
        raise ValueError("Detected sessions do not match the locked split plan")

    manifest_rows = []
    archive_entries = []
    for session_id in sorted(session_records):
        split = SPLIT_BY_SESSION[session_id]
        for sequence, row in enumerate(session_records[session_id], start=1):
            source = row["path"]
            relative_path = (
                Path("images") / session_id / row["label"] / f"{sequence:06d}_{source.name}"
            ).as_posix()
            manifest_rows.append(
                {
                    "session_id": session_id,
                    "split": split,
                    "label": row["label"],
                    "relative_path": relative_path,
                    "source_filename": source.name,
                }
            )
            archive_entries.append((source, relative_path))

    split_rows = [
        {"session_id": session_id, "split": SPLIT_BY_SESSION[session_id]}
        for session_id in sorted(SPLIT_BY_SESSION)
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{package_name}.zip"
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.csv",
            csv_bytes(
                ["session_id", "split", "label", "relative_path", "source_filename"],
                manifest_rows,
            ),
        )
        archive.writestr(
            "split_plan.csv",
            csv_bytes(["session_id", "split"], split_rows),
        )
        for source, relative_path in archive_entries:
            archive.write(source, relative_path)

    print(f"Package: {zip_path}")
    print(f"SHA256: {sha256_file(zip_path)}")
    print(f"Total frames: {len(manifest_rows)}")
    for split in ("train", "validation", "test"):
        rows = [row for row in manifest_rows if row["split"] == split]
        counts = Counter(row["label"] for row in rows)
        sessions = sorted({row["session_id"] for row in rows})
        print(
            f"{split}: frames={len(rows)}, sessions={sessions}, "
            + ", ".join(f"{name}={counts[name]}" for name in CLASS_NAMES)
        )
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-dataset", type=Path, required=True)
    parser.add_argument("--recovery-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--package-name", default="step05c_session_dataset_v1")
    args = parser.parse_args()
    build_package(
        args.original_dataset.resolve(),
        args.recovery_root.resolve(),
        args.output_dir.resolve(),
        args.package_name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
