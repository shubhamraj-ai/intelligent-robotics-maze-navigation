import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from src.step06_simple_perceptron_navigation.frame_source import (
    DEFAULT_FRAME_GLOB,
    JpegFrameWatcher,
)


ROOT = Path(__file__).resolve().parents[1]
STEP6_ROOT = ROOT / "src" / "step06_simple_perceptron_navigation"
STEP4_PERSISTENT_LUA = (
    ROOT
    / "src"
    / "step04_data_recording"
    / "persistent_camera_save_only.lua"
)


class Step06FrameHandoffTests(unittest.TestCase):
    def write_jpeg(self, path: Path, value: int):
        image = np.full((50, 50, 3), value, dtype=np.uint8)
        self.assertTrue(cv2.imwrite(str(path), image))

    def test_live_path_reuses_exact_stable_step4_persistent_lua(self):
        source = STEP4_PERSISTENT_LUA.read_text(encoding="utf-8")

        self.assertIn("local MIN_STABLE_SECONDS = 0.75", source)
        self.assertIn("local SAVE_INTERVAL_SECONDS = 2.00", source)
        self.assertIn("local LABEL_SIGNAL = 'step4_capture_label'", source)
        self.assertIn("sim.getObject('/PioneerP3DX/cam1')", source)
        self.assertIn("sim.getVisionSensorImg", source)
        self.assertIn("sim.saveImage", source)
        self.assertIn("sysCall_sensing", source)

        self.assertNotIn("setJointTargetVelocity", source)
        self.assertNotIn("simIM", source)

    def test_capture_bridge_only_writes_proven_small_string_signal(self):
        source = (STEP6_ROOT / "capture_bridge.py").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("step4_capture_label", source)
        self.assertIn('capture_enable_token = "forward"', source)
        self.assertIn("setstringsignal", source)

        self.assertNotIn("getvisionsensorimg", source)
        self.assertNotIn("setjointtargetvelocity", source)
        self.assertNotIn("/pioneerp3dx/cam1", source)
        self.assertNotIn("startsimulation", source)
        self.assertNotIn("stopsimulation", source)

    def test_default_live_glob_matches_existing_step4_capture_names(self):
        self.assertEqual(DEFAULT_FRAME_GLOB, "forward_*.jpg")

    def test_frame_watcher_ignores_preexisting_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "forward_000001.jpg"
            self.write_jpeg(old, 10)

            watcher = JpegFrameWatcher(
                root,
                pattern="forward_*.jpg",
                poll_seconds=0.001,
                read_retry_seconds=0.001,
            )

            new = root / "forward_000002.jpg"
            self.write_jpeg(new, 20)

            record = watcher.wait_for_next(timeout_seconds=1.0)

            self.assertEqual(record.path.name, new.name)
            self.assertEqual(record.frame_bgr.shape, (50, 50, 3))
            self.assertEqual(record.frame_bgr.dtype, np.uint8)

    def test_frame_watcher_never_counts_same_filename_twice(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            watcher = JpegFrameWatcher(
                root,
                pattern="forward_*.jpg",
                poll_seconds=0.001,
                read_retry_seconds=0.001,
            )

            repeated = root / "forward_000001.jpg"
            self.write_jpeg(repeated, 20)
            first = watcher.wait_for_next(timeout_seconds=1.0)
            self.assertEqual(first.path.name, repeated.name)

            # Even if the same file is overwritten with new bytes/mtime, one
            # filename must count as only one live observation in a run.
            self.write_jpeg(repeated, 40)
            with self.assertRaises(TimeoutError):
                watcher.wait_for_next(timeout_seconds=0.01)

            unique = root / "forward_000002.jpg"
            self.write_jpeg(unique, 60)
            second = watcher.wait_for_next(timeout_seconds=1.0)
            self.assertEqual(second.path.name, unique.name)

    def test_frame_watcher_times_out_without_new_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            watcher = JpegFrameWatcher(
                Path(tmp),
                poll_seconds=0.001,
                read_retry_seconds=0.001,
            )
            with self.assertRaises(TimeoutError):
                watcher.wait_for_next(timeout_seconds=0.01)

    def test_decoupled_monitor_has_no_simulator_or_motor_path(self):
        source = (STEP6_ROOT / "frame_handoff_monitor.py").read_text(
            encoding="utf-8"
        ).lower()

        self.assertNotIn("remoteapiclient", source)
        self.assertNotIn("setjointtargetvelocity", source)
        self.assertNotIn("getvisionsensorimg", source)
        self.assertNotIn("startsimulation", source)
        self.assertNotIn("stopsimulation", source)
        self.assertNotIn("tensorflow", source)

    def test_live_observe_wrapper_has_signal_access_but_no_motor_or_camera_api(self):
        source = (
            STEP6_ROOT / "observe_existing_step4_capture.py"
        ).read_text(encoding="utf-8").lower()

        self.assertIn("remoteapiclient", source)
        self.assertIn("enable_existing_step4_capture", source)
        self.assertNotIn("leftmotor", source)
        self.assertNotIn("rightmotor", source)
        self.assertNotIn("setjointtargetvelocity", source)
        self.assertNotIn("getvisionsensorimg", source)
        self.assertNotIn("/pioneerp3dx/cam1", source)
        self.assertNotIn("startsimulation", source)
        self.assertNotIn("stopsimulation", source)
        self.assertNotIn("setstepping", source)
        self.assertNotIn("tensorflow", source)

    def test_autonomous_adapter_never_touches_camera_or_sim_lifecycle(self):
        source = (STEP6_ROOT / "autonomous_navigation.py").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("remoteapiclient", source)
        self.assertIn("enable_existing_step4_capture", source)
        self.assertIn("/pioneerp3dx/leftmotor", source)
        self.assertIn("/pioneerp3dx/rightmotor", source)

        self.assertNotIn("getvisionsensorimg", source)
        self.assertNotIn("/pioneerp3dx/cam1", source)
        self.assertNotIn("startsimulation", source)
        self.assertNotIn("stopsimulation", source)
        self.assertNotIn("setstepping", source)
        self.assertNotIn("tensorflow", source)
        self.assertNotIn("route-specific", source)

    def test_python_frame_source_has_no_coppeliasim_or_motor_api(self):
        source = (STEP6_ROOT / "frame_source.py").read_text(
            encoding="utf-8"
        ).lower()

        self.assertNotIn("remoteapiclient", source)
        self.assertNotIn("getvisionsensorimg", source)
        self.assertNotIn("setjointtargetvelocity", source)


if __name__ == "__main__":
    unittest.main()
