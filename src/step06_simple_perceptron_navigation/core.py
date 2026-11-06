"""Pure Step-6 inference and motion-policy core.

Design constraints:
- use the final Step-5 single Dense(3, softmax) H5 artifact;
- load weights with h5py only (no TensorFlow runtime);
- reproduce Step-5 OpenCV BGR2GRAY preprocessing exactly;
- preserve the accepted Step-2/Step-4 1.00 / 0.10 / 1.00 motion profile;
- emit motor writes only when the requested velocity pair changes;
- do not access CoppeliaSim camera APIs here.

Live camera transport is deliberately kept outside this module so the validated
Step-4 scene-owned camera isolation boundary is not accidentally bypassed.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import h5py
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
MOTION_PROFILE_PATH = REPO_ROOT / "config" / "motion_profile.json"

LABELS = ("forward", "left", "right")
MODEL_IMAGE_SHAPE = (50, 50, 3)
MODEL_FEATURE_COUNT = 2500
MODEL_CLASS_COUNT = 3

LOCKED_FORWARD_SPEED = 1.0
LOCKED_TURN_OUTER_SPEED = 1.0
LOCKED_TURN_INNER_SPEED = 0.10
LOCKED_CONTROL_INTERVAL_SECONDS = 0.05

KERNEL_DATASET = "model_weights/direction/sequential/direction/kernel"
BIAS_DATASET = "model_weights/direction/sequential/direction/bias"


@dataclass(frozen=True)
class DenseSoftmaxModel:
    kernel: np.ndarray
    bias: np.ndarray

    def __post_init__(self) -> None:
        if self.kernel.shape != (MODEL_FEATURE_COUNT, MODEL_CLASS_COUNT):
            raise ValueError(
                "kernel must have shape "
                f"{(MODEL_FEATURE_COUNT, MODEL_CLASS_COUNT)}, "
                f"got {self.kernel.shape}"
            )
        if self.bias.shape != (MODEL_CLASS_COUNT,):
            raise ValueError(
                f"bias must have shape {(MODEL_CLASS_COUNT,)}, got {self.bias.shape}"
            )
        if not np.all(np.isfinite(self.kernel)):
            raise ValueError("kernel contains non-finite values")
        if not np.all(np.isfinite(self.bias)):
            raise ValueError("bias contains non-finite values")


def _decode_h5_attribute(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def load_dense_softmax_h5(path: Path) -> DenseSoftmaxModel:
    """Load and validate the exact final Step-5 Dense(3, softmax) H5 contract."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Model file not found: {path}")

    with h5py.File(path, "r") as handle:
        if KERNEL_DATASET not in handle or BIAS_DATASET not in handle:
            raise ValueError(
                "H5 does not contain the expected final Step-5 Dense-layer datasets"
            )

        model_config_raw = _decode_h5_attribute(handle.attrs.get("model_config"))
        if not model_config_raw:
            raise ValueError("H5 is missing Keras model_config metadata")

        model_config = json.loads(model_config_raw)
        layers = model_config.get("config", {}).get("layers", [])
        dense_layers = [
            layer
            for layer in layers
            if layer.get("class_name") == "Dense"
        ]
        forbidden_layers = {
            "Conv1D",
            "Conv2D",
            "Conv3D",
            "MaxPooling1D",
            "MaxPooling2D",
            "MaxPooling3D",
            "AveragePooling1D",
            "AveragePooling2D",
            "AveragePooling3D",
            "Dropout",
        }
        present_forbidden = sorted(
            {
                layer.get("class_name")
                for layer in layers
                if layer.get("class_name") in forbidden_layers
            }
        )
        if present_forbidden:
            raise ValueError(
                "CNN/complex layers are forbidden in the active Step-6 model: "
                + ", ".join(present_forbidden)
            )
        if len(dense_layers) != 1:
            raise ValueError(
                f"Expected exactly one Dense layer, found {len(dense_layers)}"
            )

        dense_config = dense_layers[0].get("config", {})
        if dense_config.get("units") != MODEL_CLASS_COUNT:
            raise ValueError("Final Dense layer must have exactly 3 units")
        if dense_config.get("activation") != "softmax":
            raise ValueError("Final Dense layer activation must be softmax")

        kernel = np.asarray(handle[KERNEL_DATASET][...], dtype=np.float32)
        bias = np.asarray(handle[BIAS_DATASET][...], dtype=np.float32)

    return DenseSoftmaxModel(kernel=kernel, bias=bias)


def validate_step5_metadata(path: Path) -> dict:
    """Validate the JSON evidence contract for the selected final Step-5 model."""
    path = Path(path)
    metadata = json.loads(path.read_text(encoding="utf-8"))

    if metadata.get("architecture") != "2500 -> Dense(3, softmax)":
        raise ValueError("Unexpected model architecture in Step-5 metadata")
    if tuple(metadata.get("labels", [])) != LABELS:
        raise ValueError("Unexpected label ordering in Step-5 metadata")
    if tuple(metadata.get("input_image_shape", [])) != MODEL_IMAGE_SHAPE:
        raise ValueError("Unexpected input image shape in Step-5 metadata")
    if metadata.get("preprocessing") != (
        "OpenCV BGR2GRAY -> float32 /255 -> flatten 2500"
    ):
        raise ValueError("Unexpected preprocessing contract in Step-5 metadata")

    config = metadata.get("config", {})
    expected_config = {
        "epochs": 3200,
        "learning_rate": 0.01,
        "l2": 0.0001,
        "seed": 42,
        "class_weighting": "none",
    }
    if config != expected_config:
        raise ValueError(
            f"Unexpected final Step-5 config: {config} != {expected_config}"
        )

    counts = metadata.get("training_counts", {})
    if counts != {"forward": 313, "left": 36, "right": 36}:
        raise ValueError(f"Unexpected training counts: {counts}")
    if metadata.get("training_total") != 385:
        raise ValueError("Unexpected training total; expected 385")

    return metadata


def validate_step5_experimental_candidate_metadata(
    path: Path,
    *,
    expected_turn_multiplier: float,
) -> dict:
    """Validate an explicitly opt-in partial-turn-weight Step-5 candidate."""
    path = Path(path)
    metadata = json.loads(path.read_text(encoding="utf-8"))

    if metadata.get("architecture") != "2500 -> Dense(3, softmax)":
        raise ValueError("Unexpected candidate model architecture")
    if tuple(metadata.get("labels", [])) != LABELS:
        raise ValueError("Unexpected candidate label ordering")
    if tuple(metadata.get("input_image_shape", [])) != MODEL_IMAGE_SHAPE:
        raise ValueError("Unexpected candidate input image shape")
    if metadata.get("preprocessing") != (
        "OpenCV BGR2GRAY -> float32 /255 -> flatten 2500"
    ):
        raise ValueError("Unexpected candidate preprocessing contract")

    config = metadata.get("config", {})
    fixed_expected = {
        "epochs": 3200,
        "learning_rate": 0.01,
        "l2": 0.0001,
        "seed": 42,
        "class_weighting": "partial_turn_multiplier",
    }
    for key, expected_value in fixed_expected.items():
        if config.get(key) != expected_value:
            raise ValueError(
                f"Unexpected candidate config {key}: "
                f"{config.get(key)!r} != {expected_value!r}"
            )

    multiplier = float(config.get("turn_multiplier", float("nan")))
    if not math.isclose(
        multiplier,
        float(expected_turn_multiplier),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise ValueError(
            "Unexpected candidate turn multiplier: "
            f"{multiplier} != {expected_turn_multiplier}"
        )

    expected_weights = {
        "forward": 1.0,
        "left": float(expected_turn_multiplier),
        "right": float(expected_turn_multiplier),
    }
    actual_weights = config.get("class_weights", {})
    if actual_weights != expected_weights:
        raise ValueError(
            f"Unexpected candidate class weights: "
            f"{actual_weights} != {expected_weights}"
        )

    counts = metadata.get("training_counts", {})
    if counts != {"forward": 313, "left": 36, "right": 36}:
        raise ValueError(f"Unexpected candidate training counts: {counts}")
    if metadata.get("training_total") != 385:
        raise ValueError("Unexpected candidate training total; expected 385")

    return metadata


def preprocess_bgr_frame(frame: np.ndarray) -> np.ndarray:
    """Reproduce Step-5 preprocessing for one OpenCV BGR frame."""
    frame = np.asarray(frame)
    if tuple(frame.shape) != MODEL_IMAGE_SHAPE:
        raise ValueError(
            f"Expected BGR frame shape {MODEL_IMAGE_SHAPE}, got {frame.shape}"
        )
    if frame.dtype != np.uint8:
        raise ValueError(f"Expected uint8 BGR frame, got {frame.dtype}")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    features = gray.astype(np.float32).reshape(-1) / 255.0
    if features.shape != (MODEL_FEATURE_COUNT,):
        raise AssertionError("Preprocessing produced an unexpected feature shape")
    return features


def stable_softmax(logits: np.ndarray) -> np.ndarray:
    logits = np.asarray(logits, dtype=np.float32)
    if logits.shape != (MODEL_CLASS_COUNT,):
        raise ValueError(
            f"Expected logits shape {(MODEL_CLASS_COUNT,)}, got {logits.shape}"
        )
    shifted = logits - float(np.max(logits))
    exp = np.exp(shifted, dtype=np.float32)
    denominator = float(np.sum(exp))
    if not math.isfinite(denominator) or denominator <= 0.0:
        raise ValueError("Softmax denominator is invalid")
    return (exp / denominator).astype(np.float32)


def predict_features(
    model: DenseSoftmaxModel,
    features: np.ndarray,
) -> tuple[str, np.ndarray]:
    features = np.asarray(features, dtype=np.float32)
    if features.shape != (MODEL_FEATURE_COUNT,):
        raise ValueError(
            f"Expected feature vector shape {(MODEL_FEATURE_COUNT,)}, "
            f"got {features.shape}"
        )
    if not np.all(np.isfinite(features)):
        raise ValueError("Feature vector contains non-finite values")

    logits = features @ model.kernel + model.bias
    probabilities = stable_softmax(logits)
    label = LABELS[int(np.argmax(probabilities))]
    return label, probabilities


def predict_bgr_frame(
    model: DenseSoftmaxModel,
    frame: np.ndarray,
) -> tuple[str, np.ndarray]:
    return predict_features(model, preprocess_bgr_frame(frame))


def load_locked_motion_profile(path: Path = MOTION_PROFILE_PATH) -> dict[str, float]:
    """Load the accepted Step-2/Step-4 profile and reject any silent drift."""
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {
        "forward_speed",
        "turn_outer_speed",
        "turn_inner_speed",
        "control_interval_seconds",
    }
    missing = required - set(profile)
    if missing:
        raise ValueError(f"Motion profile is missing: {sorted(missing)}")

    values = {name: float(profile[name]) for name in required}
    expected = {
        "forward_speed": LOCKED_FORWARD_SPEED,
        "turn_outer_speed": LOCKED_TURN_OUTER_SPEED,
        "turn_inner_speed": LOCKED_TURN_INNER_SPEED,
        "control_interval_seconds": LOCKED_CONTROL_INTERVAL_SECONDS,
    }
    for name, expected_value in expected.items():
        if not math.isclose(values[name], expected_value, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(
                f"Locked Step-4 motion value drifted: {name}="
                f"{values[name]} expected {expected_value}"
            )
    return values


def wheel_command_for_label(
    label: str,
    profile: dict[str, float],
) -> tuple[float, float]:
    """Map one model label to the exact accepted curved-turn wheel profile."""
    if label == "forward":
        speed = float(profile["forward_speed"])
        return speed, speed
    if label == "left":
        return (
            float(profile["turn_inner_speed"]),
            float(profile["turn_outer_speed"]),
        )
    if label == "right":
        return (
            float(profile["turn_outer_speed"]),
            float(profile["turn_inner_speed"]),
        )
    raise ValueError(f"Unknown navigation label: {label!r}")


def apply_motor_command_if_changed(
    sim,
    left_motor,
    right_motor,
    left_velocity: float,
    right_velocity: float,
    previous_command,
):
    """Preserve the validated state-change-only motor-write policy."""
    command = (float(left_velocity), float(right_velocity))
    if command == previous_command:
        return previous_command

    sim.setJointTargetVelocity(left_motor, command[0])
    sim.setJointTargetVelocity(right_motor, command[1])
    return command


def stop_motors(sim, left_motor, right_motor) -> bool:
    """Best-effort independent stop of both motors."""
    succeeded = True
    for motor in (left_motor, right_motor):
        if motor is None:
            continue
        try:
            sim.setJointTargetVelocity(motor, 0.0)
        except Exception:
            succeeded = False
    return succeeded
