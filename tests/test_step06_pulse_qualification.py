import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT
    / "src"
    / "step06_simple_perceptron_navigation"
    / "pulse_actuation_qualification.py"
)


def load_module():
    name = "step06_pulse_qualification_test_module"
    spec = importlib.util.spec_from_file_location(name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Step06PulseQualificationTests(unittest.TestCase):
    def test_pulse_duration_guard(self):
        module = load_module()

        self.assertEqual(module.DEFAULT_PULSE_SECONDS, 0.25)
        self.assertEqual(module.MAX_QUALIFICATION_PULSE_SECONDS, 0.50)
        self.assertEqual(module.validate_pulse_seconds(0.25), 0.25)

        with self.assertRaises(ValueError):
            module.validate_pulse_seconds(0.0)

        with self.assertRaises(ValueError):
            module.validate_pulse_seconds(0.51)

    def test_pulse_qualification_preserves_camera_isolation(self):
        source = MODULE_PATH.read_text(encoding="utf-8").lower()

        self.assertIn("time.sleep(active_pulse_seconds)", source)
        self.assertIn("stop_motors", source)
        self.assertIn("enable_existing_step4_capture", source)
        self.assertIn("/pioneerp3dx/leftmotor", source)
        self.assertIn("/pioneerp3dx/rightmotor", source)

        self.assertNotIn("getvisionsensorimg", source)
        self.assertNotIn("/pioneerp3dx/cam1", source)
        self.assertNotIn("startsimulation", source)
        self.assertNotIn("stopsimulation", source)
        self.assertNotIn("setstepping", source)
        self.assertNotIn("tensorflow", source)

    def test_forward_only_acceleration_preserves_turn_duration(self):
        module = load_module()

        self.assertEqual(
            module.pulse_seconds_for_label("forward", 0.25, 0.50),
            0.50,
        )
        self.assertEqual(
            module.pulse_seconds_for_label("left", 0.25, 0.50),
            0.25,
        )
        self.assertEqual(
            module.pulse_seconds_for_label("right", 0.25, 0.50),
            0.25,
        )

    def test_stop_on_first_turn_guard(self):
        module = load_module()

        self.assertFalse(module.should_stop_after_label("forward", True))
        self.assertTrue(module.should_stop_after_label("left", True))
        self.assertTrue(module.should_stop_after_label("right", True))
        self.assertFalse(module.should_stop_after_label("left", False))
        self.assertFalse(module.should_stop_after_label("right", False))

    def test_bounded_post_turn_stop_guard(self):
        module = load_module()

        self.assertFalse(module.should_stop_after_post_turn(72, None, 6))
        self.assertFalse(module.should_stop_after_post_turn(72, 72, 6))
        self.assertFalse(module.should_stop_after_post_turn(77, 72, 6))
        self.assertTrue(module.should_stop_after_post_turn(78, 72, 6))
        self.assertFalse(module.should_stop_after_post_turn(90, 72, 0))

    def test_experimental_candidate_requires_explicit_opt_in(self):
        source = MODULE_PATH.read_text(encoding="utf-8")

        self.assertIn("--experimental-turn-multiplier", source)
        self.assertIn(
            "validate_step5_experimental_candidate_metadata",
            source,
        )
        self.assertIn(
            "MODEL_STATUS: selected final unweighted model.",
            source,
        )
        self.assertIn("EXPERIMENTAL_MODEL:", source)

    def test_pose_is_diagnostics_only(self):
        source = MODULE_PATH.read_text(encoding="utf-8").lower()

        self.assertIn("getobjectposition", source)
        self.assertIn("getobjectorientation", source)
        self.assertIn("pose is logged for diagnostics only", source)
        self.assertIn("wheel_command_for_label", source)

        # Pose values are logged/printed, not used to choose a label or wheel command.
        self.assertNotIn("wheel_command_for_pose", source)
        self.assertNotIn("label_from_pose", source)
        self.assertNotIn("position[0] >", source)
        self.assertNotIn("position[1] >", source)
        self.assertNotIn("orientation[2] >", source)


if __name__ == "__main__":
    unittest.main()
