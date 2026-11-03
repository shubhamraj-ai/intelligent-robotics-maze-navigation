"""Finalize one stable Step-4 capture run into a session directory.

This utility deliberately runs *after* CoppeliaSim capture has stopped.  It does
not communicate with CoppeliaSim, does not modify the persistent Lua script,
and does not change the proven runtime capture architecture.

Default source:
    dataset_simplified/_persistent_save_probe

Each source JPEG must be named:
    forward_######.jpg
    left_######.jpg
    right_######.jpg

The utility validates every JPEG, creates a timestamped/session-named
forward/left/right directory tree, moves the JPEGs into it, and writes a JSON
manifest with counts, image shape, and the accepted motion profile.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

import cv2


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = REPO_ROOT / "dataset_simplified" / "_persistent_save_probe"
DEFAULT_DESTINATION_ROOT = REPO_ROOT / "dataset_step04_fresh"
MOTION_PROFILE_PATH = REPO_ROOT / "config" / "motion_profile.json"

LABELS = ("forward", "left", "right")
FILENAME_RE = re.compile(r"^(forward|left|right)_(\d{6})\.jpg$", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and finalize one stable Step-4 capture session."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Flat probe directory containing labeled JPEGs.",
    )
    parser.add_argument(
        "--destination-root",
        type=Path,
        default=DEFAULT_DESTINATION_ROOT,
        help="Root directory under which the session directory is created.",
    )
    parser.add_argument(
        "--session-name",
        default=None,
        help=(
            "Explicit session directory name. Defaults to "
            "session_YYYYMMDD_HHMMSS."
        ),
    )
    parser.add_argument(
        "--expected-shape",
        default="50,50,3",
        help=(
            "Expected OpenCV image shape as H,W,C. Use 'auto' to accept the "
            "first readable image shape and require all others to match it."
        ),
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy JPEGs instead of moving them out of the probe directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report what would be finalized without writing files.",
    )
    return parser.parse_args()


def parse_expected_shape(value: str):
    if value.lower() == "auto":
        return None

    parts = value.split(",")
    if len(parts) != 3:
        raise ValueError("--expected-shape must be H,W,C or 'auto'")

    shape = tuple(int(part.strip()) for part in parts)
    if any(dimension <= 0 for dimension in shape):
        raise ValueError("--expected-shape dimensions must be positive")
    return shape


def collect_source_files(source: Path):
    if not source.is_dir():
        raise FileNotFoundError(f"Capture source directory does not exist: {source}")

    files = []
    unknown_jpegs = []

    for path in sorted(source.glob("*.jpg")):
        match = FILENAME_RE.fullmatch(path.name)
        if match is None:
            # Contact sheets and other audit artifacts are intentionally ignored,
            # but unknown capture-looking JPEGs should not silently enter a session.
            if path.name.startswith("_"):
                continue
            unknown_jpegs.append(path.name)
            continue
        files.append((path, match.group(1).lower()))

    if unknown_jpegs:
        raise RuntimeError(
            "Unexpected JPEG filenames in capture source: "
            + ", ".join(unknown_jpegs)
        )

    if not files:
        raise RuntimeError(f"No labeled capture JPEGs found in {source}")

    return files


def validate_images(files, expected_shape):
    counts = Counter()
    sizes = []
    discovered_shape = expected_shape

    for path, label in files:
        image = cv2.imread(str(path))
        if image is None:
            raise RuntimeError(f"Unreadable JPEG: {path}")

        if discovered_shape is None:
            discovered_shape = tuple(image.shape)

        if tuple(image.shape) != tuple(discovered_shape):
            raise RuntimeError(
                f"Unexpected image shape for {path.name}: "
                f"{tuple(image.shape)} != {tuple(discovered_shape)}"
            )

        counts[label] += 1
        sizes.append(path.stat().st_size)

    for label in LABELS:
        counts.setdefault(label, 0)

    return counts, tuple(discovered_shape), sizes


def load_motion_profile():
    if not MOTION_PROFILE_PATH.exists():
        return None
    return json.loads(MOTION_PROFILE_PATH.read_text(encoding="utf-8"))


def build_manifest(
    *,
    session_name: str,
    source: Path,
    destination: Path,
    counts,
    image_shape,
    sizes,
    operation: str,
):
    return {
        "session_name": session_name,
        "finalized_at_local": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_directory": str(source.resolve()),
        "destination_directory": str(destination.resolve()),
        "operation": operation,
        "labels": list(LABELS),
        "counts": {label: int(counts[label]) for label in LABELS},
        "total_images": int(sum(counts.values())),
        "image_shape_hwc": list(image_shape),
        "file_size_bytes": {
            "min": int(min(sizes)),
            "max": int(max(sizes)),
            "mean": round(sum(sizes) / len(sizes), 2),
        },
        "capture_architecture": {
            "persistent_scene_owned_lua": True,
            "runtime_lua_create_remove": False,
            "lua_runtime_logging": False,
            "python_writes_label_signal": True,
            "lua_reads_label_signal": True,
            "lua_reads_camera": True,
            "lua_saves_jpeg": True,
            "python_receives_camera_bytes": False,
        },
        "capture_policy": {
            "minimum_stable_command_seconds": 0.75,
            "per_label_save_interval_seconds": 2.0,
        },
        "motion_profile": load_motion_profile(),
    }


def finalize_session(
    *,
    source: Path,
    destination_root: Path,
    session_name: str,
    expected_shape,
    copy_files: bool = False,
    dry_run: bool = False,
):
    source = source.resolve()
    destination_root = destination_root.resolve()
    destination = destination_root / session_name

    files = collect_source_files(source)
    counts, image_shape, sizes = validate_images(files, expected_shape)

    if destination.exists():
        raise FileExistsError(f"Session destination already exists: {destination}")

    operation = "copy" if copy_files else "move"
    manifest = build_manifest(
        session_name=session_name,
        source=source,
        destination=destination,
        counts=counts,
        image_shape=image_shape,
        sizes=sizes,
        operation=operation,
    )

    if dry_run:
        return destination, manifest

    for label in LABELS:
        (destination / label).mkdir(parents=True, exist_ok=False)

    try:
        for source_path, label in files:
            target = destination / label / source_path.name
            if copy_files:
                shutil.copy2(source_path, target)
            else:
                shutil.move(str(source_path), str(target))

        manifest_path = destination / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception:
        # A partially-created session is intentionally left visible for forensic
        # recovery rather than silently deleting evidence after an I/O failure.
        raise

    return destination, manifest


def main() -> int:
    args = parse_args()
    expected_shape = parse_expected_shape(args.expected_shape)
    session_name = args.session_name or datetime.now().strftime(
        "session_%Y%m%d_%H%M%S"
    )

    destination, manifest = finalize_session(
        source=args.source,
        destination_root=args.destination_root,
        session_name=session_name,
        expected_shape=expected_shape,
        copy_files=args.copy,
        dry_run=args.dry_run,
    )

    print("STEP4_SESSION_FINALIZE_READY" if args.dry_run else "STEP4_SESSION_FINALIZED")
    print(f"Session       : {session_name}")
    print(f"Destination   : {destination}")
    print(f"Total images  : {manifest['total_images']}")
    print(
        "Counts        : "
        + ", ".join(
            f"{label}={manifest['counts'][label]}" for label in LABELS
        )
    )
    print(f"Image shape   : {tuple(manifest['image_shape_hwc'])}")
    print(f"Operation     : {manifest['operation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
