"""Build Step 5F training package with clean targeted hard negatives.

Base session-aware split is preserved. Only selected human-forward frames from
clean Step 5E session hardneg_20261018T114532Z are added, and only to train.

Selection rule fixed before v6 training:
- every stable human=forward, model=right frame;
- plus +/-3 chronological frame indices when those context frames are also
  stable human=forward.

The interrupted/hung Step 5E session is intentionally excluded.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import shutil
import tempfile
import zipfile
from collections import Counter
from pathlib import Path


CLASS_NAMES = ("forward", "left", "right")
HARDNEG_SESSION_ID = "hardneg_clean_20261018"
EXPECTED_FALSE_RIGHT = 17
EXPECTED_SELECTED = 40
CONTEXT_RADIUS = 3


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


def load_hard_negative_rows(session_dir: Path):
    metadata_path = session_dir / "metadata.csv"
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Missing hard-negative metadata: {metadata_path}")

    with metadata_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    by_index = {int(row["frame_index"]): row for row in rows}
    bad_indices = sorted(
        int(row["frame_index"])
        for row in rows
        if row["human_command"] == "forward" and row["prediction"] == "right"
    )
    if len(bad_indices) != EXPECTED_FALSE_RIGHT:
        raise ValueError(
            f"Expected {EXPECTED_FALSE_RIGHT} clean false-right frames, "
            f"found {len(bad_indices)}"
        )

    selected = set(bad_indices)
    for index in bad_indices:
        for candidate in range(index - CONTEXT_RADIUS, index + CONTEXT_RADIUS + 1):
            row = by_index.get(candidate)
            if row is not None and row["human_command"] == "forward":
                selected.add(candidate)

    selected_indices = sorted(selected)
    if len(selected_indices) != EXPECTED_SELECTED:
        raise ValueError(
            f"Expected {EXPECTED_SELECTED} selected frames, found {len(selected_indices)}"
        )

    records = []
    for index in selected_indices:
        row = by_index[index]
        image_path = session_dir / row["image_relative_path"]
        if not image_path.is_file():
            raise FileNotFoundError(f"Missing selected image: {image_path}")
        reason = "false_right" if index in bad_indices else "forward_context"
        records.append(
            {
                "frame_index": index,
                "path": image_path,
                "reason": reason,
                "prediction": row["prediction"],
                "confidence": row["confidence"],
                "robot_x": row["robot_x"],
                "robot_y": row["robot_y"],
                "robot_yaw": row["robot_yaw"],
            }
        )
    return records


def read_base_archive(base_zip: Path):
    if not base_zip.is_file():
        raise FileNotFoundError(f"Missing base package: {base_zip}")
    with zipfile.ZipFile(base_zip, "r") as archive:
        manifest_text = archive.read("manifest.csv").decode("utf-8")
        split_plan_text = archive.read("split_plan.csv").decode("utf-8")
        manifest = list(csv.DictReader(io.StringIO(manifest_text)))
        split_plan = list(csv.DictReader(io.StringIO(split_plan_text)))
    return manifest, split_plan


def build_package(
    base_zip: Path,
    hard_negative_session: Path,
    output_dir: Path,
    package_name: str,
):
    manifest, split_plan = read_base_archive(base_zip)

    existing_sessions = {row["session_id"] for row in manifest}
    if HARDNEG_SESSION_ID in existing_sessions:
        raise ValueError(f"{HARDNEG_SESSION_ID} already exists in base manifest")

    selected = load_hard_negative_rows(hard_negative_session)

    new_manifest_rows = []
    selection_rows = []
    archive_entries = []

    for sequence, item in enumerate(selected, start=1):
        source = item["path"]
        relative_path = (
            Path("images")
            / HARDNEG_SESSION_ID
            / "forward"
            / f"{sequence:06d}_{source.name}"
        ).as_posix()

        new_manifest_rows.append(
            {
                "session_id": HARDNEG_SESSION_ID,
                "split": "train",
                "label": "forward",
                "relative_path": relative_path,
                "source_filename": source.name,
            }
        )
        selection_rows.append(
            {
                "session_id": HARDNEG_SESSION_ID,
                "frame_index": item["frame_index"],
                "reason": item["reason"],
                "source_prediction": item["prediction"],
                "source_confidence": item["confidence"],
                "robot_x": item["robot_x"],
                "robot_y": item["robot_y"],
                "robot_yaw": item["robot_yaw"],
                "relative_path": relative_path,
            }
        )
        archive_entries.append((source, relative_path))

    combined_manifest = manifest + new_manifest_rows
    combined_split_plan = split_plan + [
        {"session_id": HARDNEG_SESSION_ID, "split": "train"}
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{package_name}.zip"
    if zip_path.exists():
        zip_path.unlink()

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
                csv_bytes(
                    [
                        "session_id",
                        "split",
                        "label",
                        "relative_path",
                        "source_filename",
                    ],
                    combined_manifest,
                ),
            )
            dst.writestr(
                "split_plan.csv",
                csv_bytes(["session_id", "split"], combined_split_plan),
            )
            dst.writestr(
                "hard_negative_selection.csv",
                csv_bytes(
                    [
                        "session_id",
                        "frame_index",
                        "reason",
                        "source_prediction",
                        "source_confidence",
                        "robot_x",
                        "robot_y",
                        "robot_yaw",
                        "relative_path",
                    ],
                    selection_rows,
                ),
            )
            for source, relative_path in archive_entries:
                dst.write(source, relative_path)
        shutil.copy2(temp_zip, zip_path)

    print(f"Package: {zip_path}")
    print(f"SHA256: {sha256_file(zip_path)}")
    print(f"Added hard-negative frames: {len(new_manifest_rows)}")
    print(
        "Selection reasons:",
        dict(Counter(row["reason"] for row in selection_rows)),
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
    parser.add_argument("--hard-negative-session", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--package-name",
        default="step05f_hard_negative_dataset_v1",
    )
    args = parser.parse_args()

    build_package(
        args.base_zip.resolve(),
        args.hard_negative_session.resolve(),
        args.output_dir.resolve(),
        args.package_name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
