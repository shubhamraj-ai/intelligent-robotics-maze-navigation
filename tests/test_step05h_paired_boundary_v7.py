import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

builder_path = ROOT / "tools" / "build_step05h_paired_boundary_dataset.py"
builder_spec = importlib.util.spec_from_file_location(
    "build_step05h_paired_boundary_dataset", builder_path
)
builder = importlib.util.module_from_spec(builder_spec)
sys.modules[builder_spec.name] = builder
builder_spec.loader.exec_module(builder)

NOTEBOOK_PATH = ROOT / "notebooks" / "step05h_paired_boundary_v7_training.ipynb"


class Step05HPairedBoundaryV7Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
        cls.code_cells = [
            "".join(cell.get("source", []))
            for cell in cls.notebook["cells"]
            if cell.get("cell_type") == "code"
        ]
        cls.all_code = "\n".join(cls.code_cells)

    def test_builder_roles_are_locked(self):
        self.assertEqual(
            builder.BOUNDARY_TRAIN_SESSIONS,
            ("boundary_train_01", "boundary_train_02"),
        )
        self.assertEqual(
            builder.BOUNDARY_VALIDATION_SESSION,
            "boundary_validation_01",
        )
        self.assertEqual(builder.BOUNDARY_FRAMES_PER_SIDE, 5)
        self.assertEqual(builder.EXPECTED_SAMPLE_COUNTS["boundary_train_01"], 80)
        self.assertEqual(builder.EXPECTED_SAMPLE_COUNTS["boundary_train_02"], 100)
        self.assertEqual(builder.EXPECTED_SAMPLE_COUNTS["boundary_validation_01"], 100)

    def test_notebook_code_cells_compile(self):
        for index, source in enumerate(self.code_cells):
            try:
                compile(source, f"step05h_cell_{index}", "exec")
            except SyntaxError as error:
                self.fail(f"Notebook code cell {index} does not compile: {error}")

    def test_notebook_uses_v7_and_fixed_alpha_050(self):
        self.assertIn(
            'SESSION_DATASET_ZIP_NAME = "step05h_paired_boundary_dataset_v1.zip"',
            self.all_code,
        )
        self.assertIn('OUTPUT_MODEL_NAME = "maze_navigation_model_v7.h5"', self.all_code)
        self.assertIn("CLASS_WEIGHT_ALPHA = 0.50", self.all_code)

    def test_boundary_validation_is_never_a_training_session(self):
        self.assertIn(
            'EXPECTED_BOUNDARY_VALIDATION_SESSION = "boundary_validation_01"',
            self.all_code,
        )
        self.assertIn('"boundary_train_01"', self.all_code)
        self.assertIn('"boundary_train_02"', self.all_code)
        self.assertIn(
            'if EXPECTED_BOUNDARY_VALIDATION_SESSION in set(manifest["session_id"])',
            self.all_code,
        )
        self.assertIn(
            'boundary_ds = make_dataset(boundary_df, training=False)',
            self.all_code,
        )
        self.assertNotIn("boundary_ds,\n    validation_data=", self.all_code)

    def test_main_validation_and_reference_sessions_remain_unchanged(self):
        self.assertIn('"validation": {"recovery_02"}', self.all_code)
        self.assertIn('"test": {"recovery_04"}', self.all_code)
        self.assertNotIn("train_test_split", self.all_code)

    def test_precommitted_offline_gate_is_locked(self):
        self.assertIn("RECOVERY_FORWARD_RECALL_FLOOR = 0.95", self.all_code)
        self.assertIn("RECOVERY_TURN_RECALL_FLOOR = 0.70", self.all_code)
        self.assertIn("BOUNDARY_PRE_FORWARD_FLOOR = 0.70", self.all_code)
        self.assertIn("BOUNDARY_TURN_RECALL_FLOOR = 0.70", self.all_code)
        self.assertIn("BOUNDARY_EVENT_PASS_FLOOR = 0.60", self.all_code)

    def test_boundary_event_majority_rule_is_explicit(self):
        self.assertIn("pre_correct >= 3 and post_correct >= 3", self.all_code)
        self.assertIn("event_pass_rate", self.all_code)
        self.assertIn("OFFLINE GATE", self.all_code)

    def test_step5f_forward_only_hard_negative_session_is_excluded(self):
        self.assertNotIn('"hardneg_clean_20261018"', self.all_code)


if __name__ == "__main__":
    unittest.main()
