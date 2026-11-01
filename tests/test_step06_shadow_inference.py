import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "step06_shadow_inference"
    / "shadow_inference.py"
)
spec = importlib.util.spec_from_file_location("shadow_inference", MODULE_PATH)
shadow = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = shadow
spec.loader.exec_module(shadow)


class FakeKeyboard:
    def __init__(self, pressed=()):
        self.pressed = set(pressed)

    def is_pressed(self, key):
        return key in self.pressed


class FakeSim:
    def __init__(self):
        self.calls = []

    def setJointTargetVelocity(self, motor, velocity):
        self.calls.append((motor, velocity))


class ShadowInferenceTests(unittest.TestCase):
    def test_single_instance_guard_rejects_second_process(self):
        first = shadow.acquire_single_instance_guard(0)
        port = first.getsockname()[1]
        try:
            with self.assertRaises(RuntimeError):
                shadow.acquire_single_instance_guard(port)
        finally:
            first.close()

        replacement = shadow.acquire_single_instance_guard(port)
        replacement.close()

    def test_human_command_mapping(self):
        self.assertEqual(
            shadow.get_human_command(FakeKeyboard({"w"})),
            ("forward", 2.0, 2.0),
        )
        self.assertEqual(
            shadow.get_human_command(FakeKeyboard({"a"})),
            ("left", -2.0, 2.0),
        )
        self.assertEqual(
            shadow.get_human_command(FakeKeyboard({"d"})),
            ("right", 2.0, -2.0),
        )
        self.assertEqual(
            shadow.get_human_command(FakeKeyboard()),
            (None, 0.0, 0.0),
        )
        self.assertEqual(
            shadow.get_human_command(FakeKeyboard({"w", "a"})),
            (None, 0.0, 0.0),
        )

    def test_motor_gate_suppresses_duplicate_writes(self):
        sim = FakeSim()
        previous = None
        previous = shadow.apply_motor_command_if_changed(
            sim, "left", "right", 2.0, 2.0, previous
        )
        previous = shadow.apply_motor_command_if_changed(
            sim, "left", "right", 2.0, 2.0, previous
        )
        previous = shadow.apply_motor_command_if_changed(
            sim, "left", "right", 0.0, 0.0, previous
        )
        self.assertEqual(sim.calls, [
            ("left", 2.0), ("right", 2.0),
            ("left", 0.0), ("right", 0.0),
        ])

    def test_bottom_up_rgb_is_flipped_to_top_down(self):
        bottom_row = [10, 20, 30, 40, 50, 60]
        top_row = [70, 80, 90, 100, 110, 120]
        raw = bytes(bottom_row + top_row)
        frame = shadow.convert_raw_image_rgb(raw, [2, 2], np)
        expected = np.array(
            [
                [[70, 80, 90], [100, 110, 120]],
                [[10, 20, 30], [40, 50, 60]],
            ],
            dtype=np.uint8,
        )
        np.testing.assert_array_equal(frame, expected)

    def test_metrics_track_false_left_and_summary(self):
        metrics = shadow.ShadowMetrics()
        for human, predicted in [
            ("forward", "forward"),
            ("forward", "left"),
            ("forward", "left"),
            ("left", "left"),
            ("right", "right"),
        ]:
            metrics.update(human, predicted)

        self.assertEqual(metrics.total_scored, 5)
        self.assertEqual(metrics.total_agree, 3)
        self.assertEqual(metrics.longest_false_left_streak, 2)
        self.assertEqual(metrics.longest_disagreement_streak, 2)

        summary = shadow.build_summary(metrics)
        self.assertIn("Agreement rate: 60.00%", summary)
        self.assertIn(
            "False-left frames while human=forward: 2/3 (66.67%)",
            summary,
        )


if __name__ == "__main__":
    unittest.main()
