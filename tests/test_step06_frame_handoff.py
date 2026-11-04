import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from src.step06_simple_perceptron_navigation.frame_source import (
    JpegFrameWatcher,
)


ROOT = Path(__file__).resolve().parents[1]
STEP6_ROOT = ROOT / "src" / "step06_simple_perceptron_navigation"


class Step06FrameHandoffTests(unittest.TestCase):
    def write_jpeg(self, path: Path, value: int):
        image = np.full((50, 50, 3), value, dtype=np.uint8)
        self.assertTrue(cv2.imwrite(str(path), image))

    def test_lua_writer_preserves_step4_scene_owned_camera_boundary(self):
        source = (STEP6_ROOT / "step06_scene_frame_writer.lua").read_text(
            encoding="utf-8"
        )

        self.assertIn("local STARTUP_STABLE_SECONDS = 0.75", source)
        self.assertIn("local SAVE_INTERVAL_SECONDS = 2.00", source)
        self.assertIn("sim.getObject('/PioneerP3DX/cam1')", source)
        self.assertIn("sim.getVisionSensorImg", source)
        self.assertIn("sim.saveImage", source)
        self.assertIn("sysCall_sensing", source)

        self.assertNotIn("setJointTargetVelocity", source)
        self.assertNotIn("getStringSignal", source)
        self.assertNotIn("setStringSignal", source)
        self.assertNotIn("sim.addLog", source)

    def test_frame_watcher_ignores_preexisting_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "step6_frame_000001.jpg"
            self.write_jpeg(old, 10)

            watcher = JpegFrameWatcher(
                root,
                poll_seconds=0.001,
                read_retry_seconds=0.001,
            )

            new = root / "step6_frame_000002.jpg"
            self.write_jpeg(new, 20)

            record = watcher.wait_for_next(timeout_seconds=1.0)

            self.assertEqual(record.path.name, new.name)
            self.assertEqual(record.frame_bgr.shape, (50, 50, 3))
            self.assertEqual(record.frame_bgr.dtype, np.uint8)

    def test_frame_watcher_times_out_without_new_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            watcher = JpegFrameWatcher(
                Path(tmp),
                poll_seconds=0.001,
                read_retry_seconds=0.001,
            )
            with self.assertRaises(TimeoutError):
                watcher.wait_for_next(timeout_seconds=0.01)

    def test_observation_monitor_has_no_simulator_or_motor_path(self):
        source = (STEP6_ROOT / "frame_handoff_monitor.py").read_text(
            encoding="utf-8"
        ).lower()

        self.assertNotIn("remoteapiclient", source)
        self.assertNotIn("setjointtargetvelocity", source)
        self.assertNotIn("getvisionsensorimg", source)
        self.assertNotIn("startsimulation", source)
        self.assertNotIn("stopsimulation", source)
        self.assertNotIn("tensorflow", source)

    def test_autonomous_adapter_never_touches_camera_or_sim_lifecycle(self):
        source = (STEP6_ROOT / "autonomous_navigation.py").read_text(
            encoding="utf-8"
        ).lower()

        self.assertIn("remoteapiclient", source)
        self.assertNotIn("getvisionsensorimg", source)
        self.assertNotIn("/pioneerp3dx/cam1", source)
        self.assertNotIn("startsimulation", source)
        self.assertNotIn("stopsimulation", source)
        self.assertNotIn("setstepping", source)
        self.assertNotIn("tensorflow", source)
        self.assertNotIn("confidence", source.replace("no confidence threshold", ""))
        self.assertNotIn("commitment", source.replace("commitment timer", ""))
        self.assertNotIn("route-specific", source)

    def test_python_frame_source_has_no_coppeliasim_api(self):
        source = (STEP6_ROOT / "frame_source.py").read_text(
            encoding="utf-8"
        ).lower()

        self.assertNotIn("remoteapiclient", source)
        self.assertNotIn("getvisionsensorimg", source)
        self.assertNotIn("setjointtargetvelocity", source)


if __name__ == "__main__":
    unittest.main()
