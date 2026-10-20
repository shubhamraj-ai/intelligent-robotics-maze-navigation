"""Build the Step 5H paired-boundary v7 training package.

Controlled experiment:
- start from the original Step 5C session-aware package;
- add paired boundary samples from boundary_train_01 and boundary_train_02
  to the TRAIN split only;
- keep recovery_02 as the ordinary training-time validation split;
- keep recovery_04 as the repeat reference split;
- package boundary_validation_01 separately as an untouched boundary-specific
  holdout that is never included in model.fit() or early stopping.

The Step 5F forward-only hard negatives are intentionally NOT included so the
effect of balanced pre-turn/post-turn boundary data is isolated.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import shutil
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path


CLASS_NAMES = ("forward", "left", "right")
BOUNDARY_TRAIN_SESSIONS = ("boundary_train_01", "boundary_train_02")
BOUNDARY_VALIDATION_SESSION = "boundary_validation_01"
EXPECTED_EVENT_COUNTS = {
    "boundary_train_01": 8,
    "boundary_train_02": 10,
    "boundary_validation_01": 10,
}
EXPECTED_SAMPLE_COUNTS = {
    "boundary_train_01": 80,
    "boundary_train_02": 100,
    "boundary_validation_01": 100,
}
BOUNDARY_FRAMES_PER_SIDE = 5


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


def load_boundary_session(boundary_root: Path, session_id: str):
    session_dir = boundary_root / session_id
    samples_path = session_dir / "boundary_samples.csv"
    if not samples_path.is_file():
        raise FileNotFoundError(f"Missing boundary samples: {samples_path}")

    with samples_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    expected_samples = EXPECTED_SAMPLE_COUNTS[session_id]
    if len(rows) != expected_samples:
        raise ValueError(
            f"{session_id}: expected {expected_samples} samples, got {len(rows)}"
        )

    by_event = defaultdict(list)
    for row in rows:
        by_event[int(row["event_id"])].append(row)

    expected_events = EXPECTED_EVENT_COUNTS[session_id]
    if len(by_event) != expected_events:
        raise ValueError(
            f"{session_id}: expected {expected_events} events, got {len(by_event)}"
        )

    validated = []
    for event_id in sorted(by_event):
        event_rows = by_event[event_id]
        if len(event_rows) != BOUNDARY_FRAMES_PER_SIDE * 2:
            raise ValueError(
                f"{session_id} event {event_id}: expected 10 samples, "
                f"got {len(event_rows)}"
            )

        turn_classes = {row["turn_class"] for row in event_rows}
        if len(turn_classes) != 1:
            raise ValueError(
                f"{session_id} event {event_id}: inconsistent turn classes "
                f"{sorted(turn_classes)}"
            )
        turn_class = next(iter(turn_classes))
        if turn_class not in ("left", "right"):
            raise ValueError(
                f"{session_id} event {event_id}: invalid turn class {turn_class}"
            )

        pre = sorted(
            [row for row in event_rows if row["boundary_side"] == "pre_forward"],
            key=lambda row: int(row["relative_offset"]),
        )
        post = sorted(
            [row for row in event_rows if row["boundary_side"] == "post_turn"],
            key=lambda row: int(row["relative_offset"]),
        )

        if len(pre) != BOUNDARY_FRAMES_PER_SIDE:
            raise ValueError(
                f"{session_id} event {event_id}: expected 5 pre-forward samples"
            )
        if len(post) != BOUNDARY_FRAMES_PER_SIDE:
            raise ValueError(
                f"{session_id} event {event_id}: expected 5 post-turn samples"
            )
        if any(row["human_command"] != "forward" for row in pre):
            raise ValueError(
                f"{session_id} event {event_id}: pre samples must be forward"
            )
        if any(row["human_command"] != turn_class for row in post):
            raise ValueError(
                f"{session_id} event {event_id}: post samples must match {turn_class}"
            )

        for row in pre + post:
            image_path = session_dir / row["image_relative_path"]
            if not image_path.is_file():
                raise FileNotFoundError(
                    f"{session_id}: missing boundary image {image_path}"
                )
            enriched = dict(row)
            enriched["session_id"] = session_id
            enriched["label"] = row["human_command"]
            enriched["_source_path"] = image_path
            validated.append(enriched)

    return validated


def read_base_archive(base_zip: Path):
    if not base_zip.is_file():
        raise FileNotFoundError(f"Missing base package: {base_zip}")
    with zipfile.ZipFile(base_zip, "r") as archive:
        manifest = list(
            csv.DictReader(
                io.StringIO(archive.read("manifest.csv").decode("utf-8"))
            )
        )
        split_plan = list(
            csv.DictReader(
                io.StringIO(archive.read("split_plan.csv").decode("utf-8"))
            )
        )
    return manifest, split_plan


def build_package(
    base_zip: Path,
    boundary_root: Path,
    output_dir: Path,
    package_name: str,
):
    manifest, split_plan = read_base_archive(base_zip)

    existing_sessions = {row["session_id"] for row in manifest}
    forbidden = set(BOUNDARY_TRAIN_SESSIONS) | {BOUNDARY_VALIDATION_SESSION}
    overlap = existing_sessions & forbidden
    if overlap:
        raise ValueError(f"Boundary sessions already present in base manifest: {overlap}")

    training_rows = []
    for session_id in BOUNDARY_TRAIN_SESSIONS:
        training_rows.extend(load_boundary_session(boundary_root, session_id))

    validation_rows = load_boundary_session(
        boundary_root, BOUNDARY_VALIDATION_SESSION
    )

    added_manifest_rows = []
    paired_training_manifest = []
    validation_manifest = []
    archive_entries = []

    for row in training_rows:
        source = row["_source_path"]
        relative_path = (
            Path("images")
            / row["session_id"]
            / row["label"]
            / f"event_{int(row['event_id']):02d}"
            / source.name
        ).as_posix()

        added_manifest_rows.append(
            {
                "session_id": row["session_id"],
                "split": "train",
                "label": row["label"],
                "relative_path": relative_path,
                "source_filename": source.name,
            }
        )
        paired_training_manifest.append(
            {
                "session_id": row["session_id"],
                "event_id": row["event_id"],
                "turn_class": row["turn_class"],
                "boundary_side": row["boundary_side"],
                "relative_offset": row["relative_offset"],
                "frame_index": row["frame_index"],
                "label": row["label"],
                "relative_path": relative_path,
                "robot_x": row["robot_x"],
                "robot_y": row["robot_y"],
                "robot_yaw": row["robot_yaw"],
            }
        )
        archive_entries.append((source, relative_path))

    for row in validation_rows:
        source = row["_source_path"]
        relative_path = (
            Path("boundary_validation_images")
            / row["session_id"]
            / row["label"]
            / f"event_{int(row['event_id']):02d}"
            / source.name
        ).as_posix()

        validation_manifest.append(
            {
                "session_id": row["session_id"],
                "event_id": row["event_id"],
                "turn_class": row["turn_class"],
                "boundary_side": row["boundary_side"],
                "relative_offset": row["relative_offset"],
                "frame_index": row["frame_index"],
                "label": row["label"],
                "relative_path": relative_path,
                "robot_x": row["robot_x"],
                "robot_y": row["robot_y"],
                "robot_yaw": row["robot_yaw"],
            }
        )
        archive_entries.append((source, relative_path))

    combined_manifest = manifest + added_manifest_rows
    combined_split_plan = split_plan + [
        {"session_id": session_id, "split": "train"}
        for session_id in BOUNDARY_TRAIN_SESSIONS
    ]

    # Critical leakage check: boundary validation is never part of the main
    # train/validation/test manifest used by model.fit().
    if any(
        row["session_id"] == BOUNDARY_VALIDATION_SESSION
        for row in combined_manifest
    ):
        raise ValueError("Boundary validation session leaked into main manifest")

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{package_name}.zip"
    if zip_path.exists():
        zip_path.unlink()

    manifest_fields = [
        "session_id",
        "split",
        "label",
        "relative_path",
        "source_filename",
    ]
    boundary_fields = [
        "session_id",
        "event_id",
        "turn_class",
        "boundary_side",
        "relative_offset",
        "frame_index",
        "label",
        "relative_path",
        "robot_x",
        "robot_y",
        "robot_yaw",
    ]

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_zip = Path(temp_dir) / "package.zip"
        with zipfile.ZipFile(base_zip, "r") as src, zipfile.ZipFile(
            temp_zip, "w", compression=zipfile.ZIP_DEFLATED
        ) as dst:
            for info in src.infolist():
                if info.filename in {"manifest.csv", "split_plan.csv"}:
                    continue
                dst.writestr(info, src.read(info.filename))

            dst.writestr(
                "manifest.csv",
                csv_bytes(manifest_fields, combined_manifest),
            )
            dst.writestr(
                "split_plan.csv",
                csv_bytes(["session_id", "split"], combined_split_plan),
            )
            dst.writestr(
                "paired_boundary_training_manifest.csv",
                csv_bytes(boundary_fields, paired_training_manifest),
            )
            dst.writestr(
                "boundary_validation_manifest.csv",
                csv_bytes(boundary_fields, validation_manifest),
            )

            for source, relative_path in sorted(
                archive_entries, key=lambda item: item[1]
            ):
                dst.write(source, relative_path)

        shutil.copy2(temp_zip, zip_path)

    print(f"Package: {zip_path}")
    print(f"SHA256: {sha256_file(zip_path)}")
    print(f"Added paired training images: {len(added_manifest_rows)}")
    print(
        "Paired train labels:",
        dict(Counter(row["label"] for row in paired_training_manifest)),
    )
    print(
        "Boundary validation labels:",
        dict(Counter(row["label"] for row in validation_manifest)),
    )

    for split in ("train", "validation", "test"):
        rows = [row for row in combined_manifest if row["split"] == split]
        counts = Counter(row["label"] for row in rows)
        sessions = sorted({row["session_id"] for row in rows})
        print(
            f"{split}: frames={len(rows)}, sessions={sessions}, "
            + ", ".join(f"{name}={counts[name]}" for name in CLASS_NAMES)
        )

    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-zip", type=Path, required=True)
    parser.add_argument("--boundary-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--package-name",
        default="step05h_paired_boundary_dataset_v1",
    )
    args = parser.parse_args()

    build_package(
        args.base_zip.resolve(),
        args.boundary_root.resolve(),
        args.output_dir.resolve(),
        args.package_name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
