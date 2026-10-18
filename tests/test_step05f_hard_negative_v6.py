import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

builder_path = ROOT / "tools" / "build_step05f_hard_negative_dataset.py"
builder_spec = importlib.util.spec_from_file_location(
    "build_step05f_hard_negative_dataset", builder_path
)
builder = importlib.util.module_from_spec(builder_spec)
sys.modules[builder_spec.name] = builder
builder_spec.loader.exec_module(builder)

NOTEBOOK_PATH = ROOT / "notebooks" / "step05f_hard_negative_v6_training.ipynb"


class Step05FHardNegativeV6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
        cls.code_cells = [
            "".join(cell.get("source", []))
            for cell in cls.notebook["cells"]
            if cell.get("cell_type") == "code"
        ]
        cls.all_code = "\n".join(cls.code_cells)

    def test_builder_selection_contract_is_locked(self):
        self.assertEqual(builder.HARDNEG_SESSION_ID, "hardneg_clean_20261018")
        self.assertEqual(builder.EXPECTED_FALSE_RIGHT, 17)
        self.assertEqual(builder.EXPECTED_SELECTED, 40)
        self.assertEqual(builder.CONTEXT_RADIUS, 3)

    def test_notebook_code_cells_compile(self):
        for index, source in enumerate(self.code_cells):
            try:
                compile(source, f"step05f_cell_{index}", "exec")
            except SyntaxError as error:
                self.fail(f"Notebook code cell {index} does not compile: {error}")

    def test_notebook_uses_v6_and_fixed_alpha_050(self):
        self.assertIn(
            'SESSION_DATASET_ZIP_NAME = "step05f_hard_negative_dataset_v1.zip"',
            self.all_code,
        )
        self.assertIn('OUTPUT_MODEL_NAME = "maze_navigation_model_v6.h5"', self.all_code)
        self.assertIn("CLASS_WEIGHT_ALPHA = 0.50", self.all_code)

    def test_notebook_keeps_validation_and_reference_sessions_unchanged(self):
        self.assertIn('"validation": {"recovery_02"}', self.all_code)
        self.assertIn('"test": {"recovery_04"}', self.all_code)
        self.assertIn('"hardneg_clean_20261018"', self.all_code)
        self.assertNotIn("train_test_split", self.all_code)

    def test_notebook_validates_targeted_selection_file(self):
        self.assertIn('hard_negative_selection.csv', self.all_code)
        self.assertIn("len(hard_negative_selection) != 40", self.all_code)


if __name__ == "__main__":
    unittest.main()
