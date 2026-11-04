import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import h5py
import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative_path):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


core = load_module(
    "step06_simple_perceptron_core",
    "src/step06_simple_perceptron_navigation/core.py",
)
step5 = load_module(
    "step05_simple_perceptron_for_step06_test",
    "src/step05_simple_perceptron/train_simple_perceptron.py",
)


class FakeSim:
    def __init__(self):
        self.calls = []

    def setJointTargetVelocity(self, motor, velocity):
        self.calls.append((motor, velocity))


class Step06SimplePerceptronTests(unittest.TestCase):
    def make_valid_h5(self, path: Path, kernel=None, bias=None):
        if kernel is None:
            kernel = np.zeros((2500, 3), dtype=np.float32)
        if bias is None:
            bias = np.zeros(3, dtype=np.float32)

        model_config = {
            "class_name": "Sequential",
            "config": {
                "layers": [
                    {
                        "class_name": "InputLayer",
                        "config": {"batch_shape": [None, 2500]},
                    },
                    {
                        "class_name": "Dense",
                        "config": {
                            "name": "direction",
                            "units": 3,
                            "activation": "softmax",
                        },
                    },
                ]
            },
        }

        with h5py.File(path, "w") as handle:
            handle.attrs["model_config"] = json.dumps(model_config)
            group = handle.create_group(
                "model_weights/direction/sequential/direction"
            )
            group.create_dataset("kernel", data=kernel)
            group.create_dataset("bias", data=bias)

    def test_locked_motion_profile_preserves_validated_step4_balance(self):
        profile = core.load_locked_motion_profile()
        self.assertEqual(profile["forward_speed"], 1.0)
        self.assertEqual(profile["turn_outer_speed"], 1.0)
        self.assertEqual(profile["turn_inner_speed"], 0.10)
        self.assertEqual(profile["control_interval_seconds"], 0.05)

        self.assertEqual(
            core.wheel_command_for_label("forward", profile),
            (1.0, 1.0),
        )
        self.assertEqual(
            core.wheel_command_for_label("left", profile),
            (0.10, 1.0),
        )
        self.assertEqual(
            core.wheel_command_for_label("right", profile),
            (1.0, 0.10),
        )

    def test_locked_motion_profile_rejects_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "motion.json"
            path.write_text(
                json.dumps(
                    {
                        "forward_speed": 1.0,
                        "turn_outer_speed": 1.0,
                        "turn_inner_speed": 0.20,
                        "control_interval_seconds": 0.05,
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "motion value drifted"):
                core.load_locked_motion_profile(path)

    def test_preprocessing_exactly_matches_step5_path(self):
        rng = np.random.default_rng(123)
        image = rng.integers(
            0,
            256,
            size=(50, 50, 3),
            dtype=np.uint8,
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frame.png"
            self.assertTrue(cv2.imwrite(str(path), image))
            from_step5 = step5.preprocess_image(path)
            loaded = cv2.imread(str(path), cv2.IMREAD_COLOR)
            from_step6 = core.preprocess_bgr_frame(loaded)

        np.testing.assert_array_equal(from_step6, from_step5)

    def test_h5_loader_accepts_only_single_dense_softmax_contract(self):
        kernel = np.arange(2500 * 3, dtype=np.float32).reshape(2500, 3) / 1000
        bias = np.asarray([0.1, -0.2, 0.3], dtype=np.float32)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "model.h5"
            self.make_valid_h5(path, kernel=kernel, bias=bias)
            model = core.load_dense_softmax_h5(path)

        np.testing.assert_array_equal(model.kernel, kernel)
        np.testing.assert_array_equal(model.bias, bias)

    def test_h5_loader_rejects_cnn_layer(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.h5"
            with h5py.File(path, "w") as handle:
                handle.attrs["model_config"] = json.dumps(
                    {
                        "class_name": "Sequential",
                        "config": {
                            "layers": [
                                {"class_name": "Conv2D", "config": {}},
                                {
                                    "class_name": "Dense",
                                    "config": {
                                        "units": 3,
                                        "activation": "softmax",
                                    },
                                },
                            ]
                        },
                    }
                )
                group = handle.create_group(
                    "model_weights/direction/sequential/direction"
                )
                group.create_dataset(
                    "kernel",
                    data=np.zeros((2500, 3), dtype=np.float32),
                )
                group.create_dataset(
                    "bias",
                    data=np.zeros(3, dtype=np.float32),
                )

            with self.assertRaisesRegex(ValueError, "CNN/complex layers"):
                core.load_dense_softmax_h5(path)

    def test_numpy_softmax_inference_and_label_order(self):
        kernel = np.zeros((2500, 3), dtype=np.float32)
        bias = np.asarray([0.0, 1.0, -1.0], dtype=np.float32)
        model = core.DenseSoftmaxModel(kernel=kernel, bias=bias)
        features = np.zeros(2500, dtype=np.float32)

        label, probabilities = core.predict_features(model, features)

        self.assertEqual(label, "left")
        self.assertEqual(probabilities.shape, (3,))
        self.assertAlmostEqual(float(probabilities.sum()), 1.0, places=6)
        self.assertEqual(int(np.argmax(probabilities)), 1)

    def test_state_change_motor_gate_preserves_step4_policy(self):
        sim = FakeSim()
        previous = None
        previous = core.apply_motor_command_if_changed(
            sim, "left", "right", 0.10, 1.0, previous
        )
        previous = core.apply_motor_command_if_changed(
            sim, "left", "right", 0.10, 1.0, previous
        )
        previous = core.apply_motor_command_if_changed(
            sim, "left", "right", 1.0, 1.0, previous
        )

        self.assertEqual(
            sim.calls,
            [
                ("left", 0.10),
                ("right", 1.0),
                ("left", 1.0),
                ("right", 1.0),
            ],
        )

    def test_active_step6_source_has_no_tensorflow_or_camera_rpc(self):
        source = (
            ROOT
            / "src"
            / "step06_simple_perceptron_navigation"
            / "core.py"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("import tensorflow", source)
        self.assertNotIn("from tensorflow", source)
        self.assertNotIn("getvisionsensorimg", source)
        self.assertNotIn("/pioneerp3dx/cam1", source)
        self.assertNotIn("simim", source)

    def test_metadata_contract_rejects_balanced_or_complex_direction(self):
        valid = {
            "model_file": "maze_navigation_simple_perceptron_final.h5",
            "architecture": "2500 -> Dense(3, softmax)",
            "labels": ["forward", "left", "right"],
            "config": {
                "epochs": 3200,
                "learning_rate": 0.01,
                "l2": 0.0001,
                "seed": 42,
                "class_weighting": "none",
            },
            "preprocessing": "OpenCV BGR2GRAY -> float32 /255 -> flatten 2500",
            "input_image_shape": [50, 50, 3],
            "training_counts": {"forward": 313, "left": 36, "right": 36},
            "training_total": 385,
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "metadata.json"
            path.write_text(json.dumps(valid), encoding="utf-8")
            loaded = core.validate_step5_metadata(path)
            self.assertEqual(loaded["config"]["class_weighting"], "none")

            invalid = json.loads(json.dumps(valid))
            invalid["config"]["class_weighting"] = "balanced"
            path.write_text(json.dumps(invalid), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unexpected final Step-5 config"):
                core.validate_step5_metadata(path)


if __name__ == "__main__":
    unittest.main()
