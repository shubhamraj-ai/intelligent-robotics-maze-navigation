import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from src.step04_data_recording.finalize_capture_session import (
    finalize_session,
)


class Step04SessionFinalizeTests(unittest.TestCase):
    def _write_image(self, path: Path, value: int = 128, shape=(50, 50, 3)):
        image = np.full(shape, value, dtype=np.uint8)
        ok = cv2.imwrite(str(path), image)
        self.assertTrue(ok)

    def test_finalize_moves_labeled_jpegs_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "probe"
            destination_root = root / "sessions"
            source.mkdir()

            self._write_image(source / "forward_000001.jpg", 100)
            self._write_image(source / "forward_000002.jpg", 110)
            self._write_image(source / "left_000001.jpg", 120)
            self._write_image(source / "right_000001.jpg", 130)

            # Audit artifacts beginning with "_" must not enter the session.
            self._write_image(source / "_contact_sheet.jpg", 140)

            destination, manifest = finalize_session(
                source=source,
                destination_root=destination_root,
                session_name="session_test",
                expected_shape=(50, 50, 3),
            )

            self.assertEqual(destination, destination_root.resolve() / "session_test")
            self.assertEqual(manifest["total_images"], 4)
            self.assertEqual(
                manifest["counts"],
                {"forward": 2, "left": 1, "right": 1},
            )

            self.assertFalse((source / "forward_000001.jpg").exists())
            self.assertTrue((source / "_contact_sheet.jpg").exists())

            self.assertTrue(
                (destination / "forward" / "forward_000001.jpg").exists()
            )
            self.assertTrue(
                (destination / "left" / "left_000001.jpg").exists()
            )
            self.assertTrue(
                (destination / "right" / "right_000001.jpg").exists()
            )

            manifest_path = destination / "manifest.json"
            self.assertTrue(manifest_path.exists())
            disk_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(disk_manifest["image_shape_hwc"], [50, 50, 3])
            self.assertTrue(
                disk_manifest["capture_architecture"]["persistent_scene_owned_lua"]
            )
            self.assertFalse(
                disk_manifest["capture_architecture"]["runtime_lua_create_remove"]
            )
            self.assertFalse(
                disk_manifest["capture_architecture"]["lua_runtime_logging"]
            )

    def test_dry_run_does_not_move_or_create_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "probe"
            destination_root = root / "sessions"
            source.mkdir()

            image_path = source / "forward_000001.jpg"
            self._write_image(image_path)

            destination, manifest = finalize_session(
                source=source,
                destination_root=destination_root,
                session_name="session_dry",
                expected_shape=(50, 50, 3),
                dry_run=True,
            )

            self.assertTrue(image_path.exists())
            self.assertFalse(destination.exists())
            self.assertEqual(manifest["total_images"], 1)

    def test_finalize_rejects_wrong_image_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "probe"
            source.mkdir()
            self._write_image(
                source / "forward_000001.jpg",
                shape=(40, 50, 3),
            )

            with self.assertRaisesRegex(RuntimeError, "Unexpected image shape"):
                finalize_session(
                    source=source,
                    destination_root=root / "sessions",
                    session_name="session_bad_shape",
                    expected_shape=(50, 50, 3),
                )

    def test_finalize_rejects_unknown_capture_jpeg_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "probe"
            source.mkdir()
            self._write_image(source / "mystery_000001.jpg")

            with self.assertRaisesRegex(RuntimeError, "Unexpected JPEG filenames"):
                finalize_session(
                    source=source,
                    destination_root=root / "sessions",
                    session_name="session_bad_name",
                    expected_shape=(50, 50, 3),
                )


if __name__ == "__main__":
    unittest.main()
