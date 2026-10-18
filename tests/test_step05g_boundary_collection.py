import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
module_path = (
    ROOT
    / "src"
    / "step05g_boundary_collection"
    / "record_boundary_session.py"
)
spec = importlib.util.spec_from_file_location("record_boundary_session", module_path)
collector = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = collector
spec.loader.exec_module(collector)


class FakeKeyboard:
    def __init__(self, *pressed):
        self.pressed = set(pressed)

    def is_pressed(self, key):
        return key in self.pressed


def row(frame_index, command, elapsed=None):
    return {
        "frame_index": str(frame_index),
        "human_command": command,
        "elapsed_seconds": f"{(elapsed if elapsed is not None else frame_index/10):.3f}",
    }


class Step05GBoundaryCollectionTests(unittest.TestCase):
    def test_human_command_mapping_requires_exactly_one_key(self):
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

    def test_detects_forward_to_right_boundary_across_blank_frames(self):
        rows = [
            row(1, "forward"),
            row(2, "forward"),
            row(3, "forward"),
            row(4, "forward"),
            row(5, "forward"),
            row(6, ""),
            row(7, ""),
            row(8, "right"),
            row(9, "right"),
            row(10, "right"),
            row(11, "right"),
            row(12, "right"),
        ]
        events = collector.detect_boundary_events(rows, boundary_frames=5)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["turn_class"], "right")
        self.assertEqual(
            [int(r["frame_index"]) for r in events[0]["pre_rows"]],
            [1, 2, 3, 4, 5],
        )
        self.assertEqual(
            [int(r["frame_index"]) for r in events[0]["post_rows"]],
            [8, 9, 10, 11, 12],
        )

    def test_rejects_incomplete_boundary(self):
        rows = [
            row(1, "forward"),
            row(2, "forward"),
            row(3, "forward"),
            row(4, "forward"),
            row(5, "forward"),
            row(6, "left"),
            row(7, "left"),
        ]
        events = collector.detect_boundary_events(rows, boundary_frames=5)
        self.assertEqual(events, [])

    def test_summary_counts_left_and_right_events(self):
        rows = [
            row(1, "forward"),
            row(2, "left"),
            row(3, "right"),
            row(4, ""),
        ]
        events = [
            {"turn_class": "left"},
            {"turn_class": "right"},
            {"turn_class": "right"},
        ]
        summary = collector.build_summary("boundary_train_01", "train", rows, events)
        self.assertIn("Valid left-turn boundary events: 1", summary)
        self.assertIn("Valid right-turn boundary events: 2", summary)
        self.assertIn("CNN inference: OFF", summary)


if __name__ == "__main__":
    unittest.main()
