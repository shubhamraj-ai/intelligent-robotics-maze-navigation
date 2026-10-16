import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "step06_autonomous_navigation"
    / "autonomous_navigation.py"
)
spec = importlib.util.spec_from_file_location("autonomous_navigation", MODULE_PATH)
auto = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = auto
spec.loader.exec_module(auto)


class FakeModel:
    def __init__(self, input_shape=(None, 50, 50, 3), output_shape=(None, 3)):
        self.input_shape = input_shape
        self.output_shape = output_shape


class AutonomousNavigationTests(unittest.TestCase):
    def test_class_order_is_locked(self):
        self.assertEqual(auto.CLASS_NAMES, ("forward", "left", "right"))
        self.assertEqual(
            auto.CLASS_TO_INDEX,
            {"forward": 0, "left": 1, "right": 2},
        )

    def test_turn_confirmation_filter_suppresses_single_frame_flips(self):
        filt = auto.TurnConfirmationFilter(confirmation_frames=2)
        self.assertEqual(filt.apply("left"), "forward")
        self.assertEqual(filt.apply("left"), "left")
        self.assertEqual(filt.apply("right"), "forward")
        self.assertEqual(filt.apply("right"), "right")

    def test_turn_confirmation_filter_resets_on_forward(self):
        filt = auto.TurnConfirmationFilter(confirmation_frames=2)
        self.assertEqual(filt.apply("right"), "forward")
        self.assertEqual(filt.apply("forward"), "forward")
        self.assertEqual(filt.apply("right"), "forward")
        self.assertEqual(filt.apply("right"), "right")

    def test_prediction_to_motor_mapping(self):
        self.assertEqual(
            auto.motor_velocities_for_prediction("forward"),
            (2.0, 2.0),
        )
        self.assertEqual(
            auto.motor_velocities_for_prediction("left"),
            (-2.0, 2.0),
        )
        self.assertEqual(
            auto.motor_velocities_for_prediction("right"),
            (2.0, -2.0),
        )
        with self.assertRaises(ValueError):
            auto.motor_velocities_for_prediction("stop")

    def test_bottom_up_rgb_is_flipped_to_top_down(self):
        bottom_row = [10, 20, 30, 40, 50, 60]
        top_row = [70, 80, 90, 100, 110, 120]
        raw = bytes(bottom_row + top_row)
        frame = auto.convert_raw_image_rgb(raw, [2, 2], np)
        expected = np.array(
            [
                [[70, 80, 90], [100, 110, 120]],
                [[10, 20, 30], [40, 50, 60]],
            ],
            dtype=np.uint8,
        )
        np.testing.assert_array_equal(frame, expected)

    def test_image_size_and_default_v3_model_are_locked(self):
        self.assertEqual(auto.MODEL_IMAGE_SIZE, (50, 50))
        self.assertEqual(auto.DEFAULT_MODEL_PATH.name, "maze_navigation_model_v3.h5")

    def test_model_contract_accepts_step5_shapes(self):
        auto.validate_model_contract(FakeModel())

    def test_model_contract_rejects_wrong_shapes(self):
        with self.assertRaises(ValueError):
            auto.validate_model_contract(
                FakeModel(input_shape=(None, 64, 64, 3))
            )
        with self.assertRaises(ValueError):
            auto.validate_model_contract(
                FakeModel(output_shape=(None, 4))
            )


if __name__ == "__main__":
    unittest.main()
