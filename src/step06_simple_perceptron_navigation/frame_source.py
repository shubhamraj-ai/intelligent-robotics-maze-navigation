"""File-based frame handoff for the active Step-6 path.

CoppeliaSim writes JPEGs through a persistent scene-owned Lua script.
Python only reads completed files from disk. This module contains no simulator
camera API and sends no motor commands.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


FRAME_GLOB = "step6_frame_*.jpg"


@dataclass(frozen=True)
class FrameRecord:
    path: Path
    mtime_ns: int
    size_bytes: int
    frame_bgr: np.ndarray


class JpegFrameWatcher:
    """Yield only JPEG file versions that appear after watcher creation."""

    def __init__(
        self,
        frame_dir: Path,
        *,
        poll_seconds: float = 0.05,
        read_retries: int = 5,
        read_retry_seconds: float = 0.05,
    ):
        self.frame_dir = Path(frame_dir)
        self.poll_seconds = float(poll_seconds)
        self.read_retries = int(read_retries)
        self.read_retry_seconds = float(read_retry_seconds)

        if self.poll_seconds <= 0:
            raise ValueError("poll_seconds must be > 0")
        if self.read_retries <= 0:
            raise ValueError("read_retries must be > 0")
        if self.read_retry_seconds < 0:
            raise ValueError("read_retry_seconds must be >= 0")

        self.frame_dir.mkdir(parents=True, exist_ok=True)
        self._seen = {
            self._signature(path)
            for path in self.frame_dir.glob(FRAME_GLOB)
            if path.is_file()
        }

    @staticmethod
    def _signature(path: Path) -> tuple[str, int, int]:
        stat = path.stat()
        return path.name, int(stat.st_mtime_ns), int(stat.st_size)

    def _unseen_candidates(self):
        candidates = []
        for path in self.frame_dir.glob(FRAME_GLOB):
            if not path.is_file():
                continue
            signature = self._signature(path)
            if signature in self._seen:
                continue
            candidates.append((signature, path))

        candidates.sort(
            key=lambda item: (item[0][1], item[0][0], item[0][2])
        )
        return candidates

    def _read_complete_frame(self, path: Path) -> np.ndarray | None:
        for attempt in range(self.read_retries):
            frame = cv2.imread(str(path), cv2.IMREAD_COLOR)
            if frame is not None:
                return frame
            if attempt + 1 < self.read_retries:
                time.sleep(self.read_retry_seconds)
        return None

    def wait_for_next(self, *, timeout_seconds: float | None = None) -> FrameRecord:
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0 when provided")

        started = time.monotonic()

        while True:
            for signature, path in self._unseen_candidates():
                frame = self._read_complete_frame(path)
                if frame is None:
                    continue

                self._seen.add(signature)
                return FrameRecord(
                    path=path,
                    mtime_ns=signature[1],
                    size_bytes=signature[2],
                    frame_bgr=frame,
                )

            if (
                timeout_seconds is not None
                and time.monotonic() - started >= timeout_seconds
            ):
                raise TimeoutError(
                    f"No new Step-6 JPEG arrived in {self.frame_dir} "
                    f"within {timeout_seconds:.2f}s"
                )

            time.sleep(self.poll_seconds)
