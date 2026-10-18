import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
collector_path = (
    ROOT
    / "src"
    / "step05e_hard_negative_collection"
    / "record_hard_negative_session.py"
)
spec = importlib.util.spec_from_file_location("record_hard_negative_session", collector_path)
collector = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = collector
spec.loader.exec_module(collector)


class FakeKeyboard:
    def __init__(self, *pressed):
        self.pressed = set(pressed)

    def is_pressed(self, key):
        return key in self.pressed


def row(frame_index, human, prediction, confidence, elapsed):
    return {
        "frame_index": str(frame_index),
        "human_command": human,
        "prediction": prediction,
        "confidence": f"{confidence:.6f}",
        "elapsed_seconds": f"{elapsed:.3f}",
    }


class Step05EHardNegativeTests(unittest.TestCase):
    def test_human_command_mapping_requires_one_key(self):
        self.assertEqual(
            collector.get_human_command(FakeKeyboard("w")),
            ("forward", 2.0, 2.0),
        )
        self.assertEqual(
            collector.get_human_command(FakeKeyboard("a")),
            ("left", -2.0, 2.0),
        )
        self.assertEqual(
            collector.get_human_command(FakeKeyboard("d")),
            ("right", 2.0, -2.0),
        )
        self.assertEqual(
            collector.get_human_command(FakeKeyboard("w", "d")),
            (None, 0.0, 0.0),
        )

    def test_bottom_up_rgb_is_flipped_to_top_down(self):
        raw = bytes(
            [
                10, 20, 30, 40, 50, 60,
                70, 80, 90, 100, 110, 120,
            ]
        )
        frame = collector.convert_raw_image_rgb(raw, [2, 2], np)
        expected = np.array(
            [
                [[70, 80, 90], [100, 110, 120]],
                [[10, 20, 30], [40, 50, 60]],
            ],
            dtype=np.uint8,
        )
        np.testing.assert_array_equal(frame, expected)

    def test_summary_groups_consecutive_false_right_events(self):
        rows = [
            row(1, "forward", "forward", 0.99, 0.0),
            row(2, "forward", "right", 0.91, 0.1),
            row(3, "forward", "right", 0.95, 0.2),
            row(4, "forward", "right", 0.80, 0.3),
            row(5, "left", "left", 0.99, 0.4),
            row(6, "forward", "right", 0.97, 0.5),
            row(7, "", "right", 0.99, 0.6),
            row(8, "forward", "forward", 0.99, 0.7),
        ]
        summary = collector.summarize_rows(rows)

        self.assertEqual(summary["total_frames"], 8)
        self.assertEqual(summary["scored_frames"], 7)
        self.assertEqual(summary["false_right_frames"], 4)
        self.assertEqual(summary["high_conf_false_right_frames"], 3)
        self.assertEqual(summary["longest_false_right_streak"], 3)
        self.assertEqual(summary["longest_high_conf_false_right_streak"], 2)
        self.assertEqual(len(summary["events"]), 2)
        self.assertEqual(summary["events"][0]["frames"], 3)
        self.assertEqual(summary["events"][0]["first_frame_index"], 2)
        self.assertEqual(summary["events"][0]["last_frame_index"], 4)

    def test_summary_text_states_shadow_only_context(self):
        summary = collector.summarize_rows(
            [
                row(1, "forward", "right", 0.95, 0.0),
                row(2, "forward", "forward", 0.99, 0.1),
            ]
        )
        text = collector.build_summary_text(summary)
        self.assertIn("Human-forward/model-right frames: 1", text)
        self.assertIn("The CNN never actuated the motors.", text)
        self.assertIn("pre/post-event context", text)


if __name__ == "__main__":
    unittest.main()
