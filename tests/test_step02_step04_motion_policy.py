import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative_path):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


step2 = load_module("step02_manual_control", "src/step02_manual_control/manual_control.py")
step4 = load_module("step04_data_recording", "src/step04_data_recording/record_training_data.py")


class FakeKeyboard:
    def __init__(self, *pressed):
        self.pressed = set(pressed)

    def is_pressed(self, key):
        return key in self.pressed


class ProfessorAlignedMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profile = json.loads(
            (ROOT / "config" / "motion_profile.json").read_text(encoding="utf-8")
        )

    def test_profile_uses_forward_only_curved_turns(self):
        self.assertGreater(self.profile["forward_speed"], 0)
        self.assertGreater(self.profile["turn_outer_speed"], 0)
        self.assertGreaterEqual(self.profile["turn_inner_speed"], 0)
        self.assertLess(
            self.profile["turn_inner_speed"], self.profile["turn_outer_speed"]
        )

    def test_step2_and_step4_use_same_motion_mapping(self):
        for key, expected_label in [("w", "forward"), ("a", "left"), ("d", "right")]:
            command2 = step2.get_command(FakeKeyboard(key), self.profile)
            command4 = step4.get_command(FakeKeyboard(key), self.profile)
            self.assertEqual(command2, command4)
            self.assertEqual(command2[0], expected_label)

    def test_left_and_right_are_curves_not_reverse_wheel_pivots(self):
        _, left_l, left_r = step2.get_command(FakeKeyboard("a"), self.profile)
        _, right_l, right_r = step2.get_command(FakeKeyboard("d"), self.profile)
        self.assertGreaterEqual(left_l, 0)
        self.assertGreater(left_r, left_l)
        self.assertGreaterEqual(right_r, 0)
        self.assertGreater(right_l, right_r)

    def test_ambiguous_input_stops_robot(self):
        self.assertEqual(
            step2.get_command(FakeKeyboard("w", "a"), self.profile),
            (None, 0.0, 0.0),
        )

    def test_step4_subsamples_forward_more_than_turns(self):
        self.assertGreater(
            step4.save_interval_for("forward"),
            step4.save_interval_for("left"),
        )
        self.assertEqual(
            step4.save_interval_for("left"),
            step4.save_interval_for("right"),
        )

    def test_step4_has_nonzero_command_stability_delay(self):
        self.assertGreater(step4.MIN_STABLE_COMMAND_SECONDS, 0)


if __name__ == "__main__":
    unittest.main()
