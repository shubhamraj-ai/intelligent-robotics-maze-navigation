import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from src.step05_simple_perceptron.train_simple_perceptron import (
    DEFAULT_OUTPUT_DIR,
    parse_args,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "step05_final_simple_perceptron_colab.ipynb"


class Step05FinalSubmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
        cls.sources = [
            "".join(cell.get("source", []))
            for cell in cls.notebook["cells"]
        ]
        cls.all_source = "\n".join(cls.sources)

    def test_final_cli_defaults_are_locked(self):
        with patch.object(sys, "argv", ["train_simple_perceptron.py"]):
            args = parse_args()

        self.assertEqual(args.epochs, 3200)
        self.assertAlmostEqual(args.learning_rate, 0.01)
        self.assertAlmostEqual(args.l2, 1e-4)
        self.assertEqual(args.seed, 42)
        self.assertEqual(args.class_weighting, "none")
        self.assertEqual(DEFAULT_OUTPUT_DIR.name, "step05_simple_perceptron")

    def test_balanced_weighting_remains_available_as_override(self):
        with patch.object(
            sys,
            "argv",
            ["train_simple_perceptron.py", "--class-weighting", "balanced"],
        ):
            args = parse_args()

        self.assertEqual(args.class_weighting, "balanced")

    def test_notebook_is_nbformat4_and_code_cells_compile(self):
        self.assertEqual(self.notebook.get("nbformat"), 4)

        for index, cell in enumerate(self.notebook["cells"]):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            try:
                compile(source, f"step05_final_cell_{index}", "exec")
            except SyntaxError as error:
                self.fail(f"Code cell {index} has invalid Python syntax: {error}")

    def test_notebook_locks_final_dataset_and_training_configuration(self):
        self.assertIn(
            "CONFIG = dict(epochs=3200, learning_rate=0.01, l2=1e-4, seed=42)",
            self.all_source,
        )
        self.assertIn("CLASS_WEIGHTING = 'none'", self.all_source)
        self.assertIn(
            "EXPECTED_COUNTS = {'forward': 313, 'left': 36, 'right': 36}",
            self.all_source,
        )
        for session in (
            "session_20261103_01",
            "session_20261103_02",
            "session_20261103_03",
        ):
            self.assertIn(session, self.all_source)
        self.assertIn("EXPECTED_SHAPE = (50, 50, 3)", self.all_source)
        self.assertIn("385", self.all_source)
        self.assertIn(
            "/content/drive/MyDrive/Intelligent_Robotics_Design_Project/"
            "Step05_Final_Simple_Perceptron_2026-11-04/"
            "dataset_step05_official.zip",
            self.all_source,
        )
        self.assertIn(
            "/content/drive/MyDrive/Intelligent_Robotics_Design_Project/"
            "Step05_Final_Simple_Perceptron_2026-11-04/Colab_Output",
            self.all_source,
        )

    def test_notebook_exports_minimal_h5_model_with_numpy_parity_check(self):
        self.assertIn(
            "maze_navigation_simple_perceptron_final.h5",
            self.all_source,
        )
        self.assertIn(
            "tf.keras.layers.Dense(3, activation='softmax', name='direction')",
            self.all_source,
        )
        self.assertIn("model.get_layer('direction').set_weights([weights, bias])", self.all_source)
        self.assertIn("np.testing.assert_allclose(keras_scores, numpy_scores", self.all_source)
        self.assertIn("tf.keras.models.load_model(model_path, compile=False)", self.all_source)

    def test_notebook_does_not_reintroduce_complex_model_or_step6(self):
        for forbidden in (
            "Conv2D",
            "MaxPooling",
            "MaxPool",
            "Dropout",
        ):
            self.assertNotIn(forbidden, self.all_source)

        self.assertIn("This notebook does not implement Step 6 control.", self.all_source)
        self.assertIn("Step 6 remains separate.", self.all_source)


if __name__ == "__main__":
    unittest.main()
