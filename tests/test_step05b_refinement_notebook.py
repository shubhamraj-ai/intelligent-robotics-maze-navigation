import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = REPO_ROOT / "notebooks" / "step05b_cnn_refinement.ipynb"


class Step05BNotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
        cls.sources = ["".join(cell.get("source", [])) for cell in cls.notebook["cells"]]
        cls.all_source = "\n".join(cls.sources)

    def test_all_code_cells_compile(self):
        for index, cell in enumerate(self.notebook["cells"]):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            try:
                compile(source, f"step05b_cell_{index}", "exec")
            except SyntaxError as error:
                self.fail(f"Code cell {index} has invalid Python syntax: {error}")

    def test_audited_dataset_and_v3_names_are_locked(self):
        self.assertIn('DATASET_ZIP_NAME = "dataset_v2_clean_2383.zip"', self.all_source)
        self.assertIn('MODEL_FILENAME = "maze_navigation_model_v3.h5"', self.all_source)
        self.assertIn(
            'EXPECTED_CLASS_COUNTS = {"forward": 2137, "left": 121, "right": 125}',
            self.all_source,
        )
        self.assertIn('if len(images_df) != 2383:', self.all_source)

    def test_candidate_weight_schedule_and_normalization_are_present(self):
        self.assertIn(
            "CANDIDATE_WEIGHT_ALPHAS = [1.00, 0.75, 0.50, 0.25, 0.00]",
            self.all_source,
        )
        self.assertIn("np.power(balanced_weights_array, float(alpha))", self.all_source)
        self.assertIn("mean_sample_weight", self.all_source)
        self.assertIn("WEIGHT NORMALIZATION CHECK: PASS", self.all_source)

    def test_validation_selection_precedes_test_evaluation(self):
        select_position = self.all_source.index("SELECTED CANDIDATE:")
        test_position = self.all_source.index("test_loss, test_accuracy = selected_model.evaluate")
        self.assertLess(select_position, test_position)
        self.assertIn(
            "No moderated candidate reduced validation forward->left errors",
            self.all_source,
        )
        self.assertIn("MAX_ADDITIONAL_TURN_MISSES = 2", self.all_source)
        self.assertIn("MACRO_F1_TOLERANCE = 0.05", self.all_source)
        self.assertIn("left_correct_floor", self.all_source)
        self.assertIn("right_correct_floor", self.all_source)

    def test_v2_is_preserved_and_v3_evidence_is_saved(self):
        self.assertIn("maze_navigation_model_v2.h5", self.all_source)
        self.assertIn("step05b_candidate_validation_metrics.csv", self.all_source)
        self.assertIn("step05b_selected_config.json", self.all_source)
        self.assertIn("step05b_v3_test_metrics.json", self.all_source)


if __name__ == "__main__":
    unittest.main()
