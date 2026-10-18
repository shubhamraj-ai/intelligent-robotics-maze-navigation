import importlib.util
import sys
import unittest
from collections import deque
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


def sample(frame_index, command):
    return {
        "frame_index": frame_index,
        "human_command": command,
        "timestamp_utc": "2026-10-18T00:00:00+00:00",
        "elapsed_seconds": f"{frame_index/10:.3f}",
        "robot_x": "0",
        "robot_y": "0",
        "robot_yaw": "0",
        "frame_rgb": np.zeros((2, 2, 3), dtype=np.uint8),
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

    def test_recent_forward_samples_ignore_blank_frames(self):
        ring = deque(
            [
                sample(1, "left"),
                sample(2, "forward"),
                sample(3, None),
                sample(4, "forward"),
                sample(5, "forward"),
                sample(6, None),
                sample(7, "forward"),
                sample(8, "forward"),
            ],
            maxlen=40,
        )
        selected = collector.recent_forward_samples(ring, count=5)
        self.assertEqual(
            [item["frame_index"] for item in selected],
            [2, 4, 5, 7, 8],
        )

    def test_recent_forward_samples_do_not_cross_prior_turn(self):
        ring = deque(
            [
                sample(1, "forward"),
                sample(2, "forward"),
                sample(3, "right"),
                sample(4, "forward"),
                sample(5, "forward"),
                sample(6, "forward"),
            ],
            maxlen=40,
        )
        self.assertEqual(collector.recent_forward_samples(ring, count=5), [])

    def test_summary_counts_completed_events_and_saved_images(self):
        rows = [
            {"human_command": "forward"},
            {"human_command": "left"},
            {"human_command": "right"},
            {"human_command": ""},
        ]
        events = [
            {"turn": "left"},
            {"turn": "right"},
            {"turn": "right"},
        ]
        summary = collector.build_summary(
            "boundary_train_01",
            "train",
            rows,
            events,
            discarded_events=1,
        )
        self.assertIn("Completed left-boundary events: 1", summary)
        self.assertIn("Completed right-boundary events: 2", summary)
        self.assertIn("Discarded incomplete boundary events: 1", summary)
        self.assertIn("Saved images: 30", summary)
        self.assertIn("Continuous JPEG writing: OFF", summary)


if __name__ == "__main__":
    unittest.main()
