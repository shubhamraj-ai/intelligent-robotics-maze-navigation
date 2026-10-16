import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]

collector_path = (
    ROOT / "src" / "step05c_recovery_collection" / "record_recovery_session.py"
)
collector_spec = importlib.util.spec_from_file_location(
    "record_recovery_session", collector_path
)
collector = importlib.util.module_from_spec(collector_spec)
sys.modules[collector_spec.name] = collector
collector_spec.loader.exec_module(collector)

audit_path = ROOT / "tools" / "audit_dataset_sessions.py"
audit_spec = importlib.util.spec_from_file_location("audit_dataset_sessions", audit_path)
audit = importlib.util.module_from_spec(audit_spec)
sys.modules[audit_spec.name] = audit
audit_spec.loader.exec_module(audit)


class FakeKeyboard:
    def __init__(self, *pressed):
        self.pressed = set(pressed)

    def is_pressed(self, key):
        return key in self.pressed


class Step05CRecoveryTests(unittest.TestCase):
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
            collector.get_human_command(FakeKeyboard("a", "d")),
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

    def test_session_split_detects_large_timestamp_gap(self):
        from datetime import datetime, timedelta

        t0 = datetime(2026, 10, 10, 10, 0, 0)
        records = [
            (t0, "forward", Path("a.jpg")),
            (t0 + timedelta(seconds=1), "left", Path("b.jpg")),
            (t0 + timedelta(seconds=20), "right", Path("c.jpg")),
        ]
        sessions = audit.split_sessions(records, gap_seconds=10)
        self.assertEqual([len(s) for s in sessions], [2, 1])


if __name__ == "__main__":
    unittest.main()
