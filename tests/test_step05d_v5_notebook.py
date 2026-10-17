import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "notebooks" / "step05d_class_weight_calibration_v5.ipynb"


class Step05DV5NotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
        cls.code_cells = [
            "".join(cell.get("source", []))
            for cell in cls.notebook["cells"]
            if cell.get("cell_type") == "code"
        ]
        cls.all_code = "\n".join(cls.code_cells)

    def test_all_code_cells_compile(self):
        for index, source in enumerate(self.code_cells):
            try:
                compile(source, f"notebook_cell_{index}", "exec")
            except SyntaxError as error:
                self.fail(f"Notebook code cell {index} does not compile: {error}")

    def test_candidate_schedule_is_locked(self):
        self.assertIn("CANDIDATE_WEIGHT_ALPHAS = [0.75, 0.50, 0.25, 0.00]", self.all_code)
        self.assertIn("MIN_LEFT_RECALL = 0.70", self.all_code)
        self.assertIn("MIN_RIGHT_RECALL = 0.70", self.all_code)

    def test_session_split_remains_unchanged(self):
        expected_fragments = [
            '"train": {"original_01", "original_02", "original_03", "recovery_01", "recovery_03"}',
            '"validation": {"recovery_02"}',
            '"test": {"recovery_04"}',
        ]
        for fragment in expected_fragments:
            self.assertIn(fragment, self.all_code)
        self.assertNotIn("train_test_split", self.all_code)

    def test_selection_precedes_reference_test(self):
        select_index = self.all_code.index("SELECTED_ALPHA = float(selected_row")
        test_index = self.all_code.index("reference_probabilities = selected_model.predict")
        self.assertLess(select_index, test_index)

    def test_selection_targets_false_turn_streak_and_rate(self):
        self.assertIn('"longest_forward_false_turn_streak"', self.all_code)
        self.assertIn('"forward_false_turn_rate"', self.all_code)
        self.assertIn('ascending=[True, True, False]', self.all_code)

    def test_v5_artifact_name_is_separate(self):
        self.assertIn('OUTPUT_MODEL_NAME = "maze_navigation_model_v5.h5"', self.all_code)
        self.assertNotIn('OUTPUT_MODEL_NAME = "maze_navigation_model_v4.h5"', self.all_code)


if __name__ == "__main__":
    unittest.main()
