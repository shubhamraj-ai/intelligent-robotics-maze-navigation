import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "notebooks" / "step05c_session_aware_v4_training.ipynb"
BUILDER_PATH = ROOT / "tools" / "build_step05c_session_dataset.py"


spec = importlib.util.spec_from_file_location("step05c_builder", BUILDER_PATH)
builder = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = builder
spec.loader.exec_module(builder)


class Step05CV4NotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
        cls.code_cells = [
            "".join(cell.get("source", []))
            for cell in cls.notebook["cells"]
            if cell.get("cell_type") == "code"
        ]
        cls.all_code = "\n".join(cls.code_cells)

    def test_session_split_is_locked_and_disjoint(self):
        expected = {
            "original_01": "train",
            "original_02": "train",
            "original_03": "train",
            "recovery_01": "train",
            "recovery_02": "validation",
            "recovery_03": "train",
            "recovery_04": "test",
        }
        self.assertEqual(builder.SPLIT_BY_SESSION, expected)

    def test_notebook_uses_v4_and_fixed_alpha(self):
        self.assertIn('OUTPUT_MODEL_NAME = "maze_navigation_model_v4.h5"', self.all_code)
        self.assertIn("CLASS_WEIGHT_ALPHA = 0.75", self.all_code)
        self.assertNotIn("train_test_split", self.all_code)

    def test_notebook_has_expected_session_partitions(self):
        for session_id in builder.SPLIT_BY_SESSION:
            self.assertIn(session_id, self.all_code)
        self.assertIn('"validation": {"recovery_02"}', self.all_code)
        self.assertIn('"test": {"recovery_04"}', self.all_code)

    def test_all_code_cells_compile(self):
        for index, source in enumerate(self.code_cells):
            try:
                compile(source, f"notebook_cell_{index}", "exec")
            except SyntaxError as error:
                self.fail(f"Notebook code cell {index} does not compile: {error}")

    def test_validation_precedes_held_out_test(self):
        validation_index = self.all_code.index("val_probabilities = model.predict")
        test_index = self.all_code.index("test_loss, test_accuracy = model.evaluate")
        self.assertLess(validation_index, test_index)


if __name__ == "__main__":
    unittest.main()
