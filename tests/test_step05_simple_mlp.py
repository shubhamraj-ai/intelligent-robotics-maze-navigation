import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from src.step05_simple_mlp.train_simple_mlp import (
    EXPECTED_SHAPE,
    LABEL_TO_INDEX,
    confusion_matrix,
    load_session,
    metrics_from_confusion,
    preprocess_image,
)


class Step05SimpleMLPTests(unittest.TestCase):
    def _write_image(self, path: Path, value: int = 128, shape=EXPECTED_SHAPE):
        image = np.full(shape, value, dtype=np.uint8)
        ok = cv2.imwrite(str(path), image)
        self.assertTrue(ok)

    def test_preprocess_produces_2500_normalized_grayscale_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.jpg"
            self._write_image(path, value=200)

            vector = preprocess_image(path)

            self.assertEqual(vector.shape, (2500,))
            self.assertEqual(vector.dtype, np.float32)
            self.assertGreaterEqual(float(vector.min()), 0.0)
            self.assertLessEqual(float(vector.max()), 1.0)

    def test_load_session_preserves_label_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session = root / "session_x"

            for label, value in (
                ("forward", 80),
                ("left", 120),
                ("right", 160),
            ):
                folder = session / label
                folder.mkdir(parents=True, exist_ok=True)
                self._write_image(folder / f"{label}_000001.jpg", value)

            loaded = load_session(root, "session_x")

            self.assertEqual(loaded.x.shape, (3, 2500))
            self.assertEqual(loaded.y.tolist(), [
                LABEL_TO_INDEX["forward"],
                LABEL_TO_INDEX["left"],
                LABEL_TO_INDEX["right"],
            ])

    def test_confusion_and_metrics_are_class_order_locked(self):
        y_true = np.asarray([0, 0, 1, 1, 2, 2], dtype=np.int32)
        y_pred = np.asarray([0, 1, 1, 1, 2, 0], dtype=np.int32)

        matrix = confusion_matrix(y_true, y_pred)

        self.assertEqual(
            matrix.tolist(),
            [
                [1, 1, 0],
                [0, 2, 0],
                [1, 0, 1],
            ],
        )

        metrics = metrics_from_confusion(matrix)
        self.assertAlmostEqual(metrics["accuracy"], 4 / 6)
        self.assertEqual(metrics["per_class"]["left"]["support"], 2)
        self.assertAlmostEqual(metrics["per_class"]["left"]["recall"], 1.0)

    def test_wrong_shape_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.jpg"
            self._write_image(path, shape=(40, 50, 3))

            with self.assertRaisesRegex(RuntimeError, "Unexpected image shape"):
                preprocess_image(path)


if __name__ == "__main__":
    unittest.main()
