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

        self.assertIn("time.sleep(pulse_seconds)", source)
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

    def test_stop_on_first_turn_guard(self):
        module = load_module()

        self.assertFalse(module.should_stop_after_label("forward", True))
        self.assertTrue(module.should_stop_after_label("left", True))
        self.assertTrue(module.should_stop_after_label("right", True))
        self.assertFalse(module.should_stop_after_label("left", False))
        self.assertFalse(module.should_stop_after_label("right", False))


if __name__ == "__main__":
    unittest.main()
