"""Step 5 baseline: simple session-aware MLP for maze navigation.

This intentionally does not use the legacy CNN refinement path.  The model is
an OpenCV ANN_MLP with one small hidden layer and three outputs:

    50x50 RGB JPEG -> grayscale -> normalize to [0, 1] -> flatten 2500
    -> Dense(hidden_units) -> Dense(3)

Evaluation uses leave-one-session-out cross-validation so adjacent frames from
the same traversal are never randomly split across train and evaluation data.
After cross-validation, a baseline model is trained on all supplied sessions
for later shadow/autonomous testing.

No class reweighting or oversampling is applied in this first baseline.  If
turn recall is inadequate, balancing should be introduced only after measuring
this unweighted baseline.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_ROOT = REPO_ROOT / "dataset_step04_fresh"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "models" / "step05_simple_mlp"

LABELS = ("forward", "left", "right")
LABEL_TO_INDEX = {label: index for index, label in enumerate(LABELS)}
EXPECTED_SHAPE = (50, 50, 3)
DEFAULT_SESSIONS = (
    "session_20261103_01",
    "session_20261103_02",
    "session_20261103_03",
)


@dataclass(frozen=True)
class SessionData:
    name: str
    x: np.ndarray
    y: np.ndarray
    paths: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train/evaluate the professor-aligned simple Step-5 MLP using "
            "session-level cross-validation."
        )
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=DEFAULT_DATASET_ROOT,
    )
    parser.add_argument(
        "--sessions",
        nargs="+",
        default=list(DEFAULT_SESSIONS),
        help="Session directory names to include.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument(
        "--hidden-units",
        type=int,
        default=32,
    )
    parser.add_argument(
        "--max-iter",
        type=int,
        default=500,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )
    return parser.parse_args()


def preprocess_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Unreadable JPEG: {path}")

    if tuple(image.shape) != EXPECTED_SHAPE:
        raise RuntimeError(
            f"Unexpected image shape for {path}: "
            f"{tuple(image.shape)} != {EXPECTED_SHAPE}"
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    vector = gray.astype(np.float32).reshape(-1) / 255.0
    return vector


def load_session(dataset_root: Path, session_name: str) -> SessionData:
    session_root = dataset_root / session_name
    if not session_root.is_dir():
        raise FileNotFoundError(f"Session directory not found: {session_root}")

    vectors: list[np.ndarray] = []
    labels: list[int] = []
    paths: list[str] = []

    for label in LABELS:
        folder = session_root / label
        if not folder.is_dir():
            raise FileNotFoundError(f"Missing label directory: {folder}")

        files = sorted(folder.glob("*.jpg"))
        if not files:
            raise RuntimeError(f"No JPEGs found for {session_name}/{label}")

        for path in files:
            vectors.append(preprocess_image(path))
            labels.append(LABEL_TO_INDEX[label])
            paths.append(str(path))

    x = np.stack(vectors).astype(np.float32)
    y = np.asarray(labels, dtype=np.int32)

    return SessionData(
        name=session_name,
        x=x,
        y=y,
        paths=tuple(paths),
    )


def combine_sessions(sessions: Iterable[SessionData]) -> tuple[np.ndarray, np.ndarray]:
    sessions = tuple(sessions)
    if not sessions:
        raise ValueError("At least one session is required")

    x = np.concatenate([session.x for session in sessions], axis=0)
    y = np.concatenate([session.y for session in sessions], axis=0)
    return x, y


def encode_targets(y: np.ndarray) -> np.ndarray:
    targets = np.full((len(y), len(LABELS)), -1.0, dtype=np.float32)
    targets[np.arange(len(y)), y] = 1.0
    return targets


def train_mlp(
    x: np.ndarray,
    y: np.ndarray,
    *,
    hidden_units: int,
    max_iter: int,
    seed: int,
):
    if hidden_units <= 0:
        raise ValueError("hidden_units must be positive")

    cv2.setRNGSeed(int(seed))

    model = cv2.ml.ANN_MLP_create()
    model.setLayerSizes(
        np.asarray(
            [x.shape[1], int(hidden_units), len(LABELS)],
            dtype=np.int32,
        )
    )
    model.setActivationFunction(cv2.ml.ANN_MLP_SIGMOID_SYM, 1.0, 1.0)
    model.setTrainMethod(cv2.ml.ANN_MLP_RPROP)
    model.setTermCriteria(
        (
            cv2.TERM_CRITERIA_MAX_ITER | cv2.TERM_CRITERIA_EPS,
            int(max_iter),
            1e-5,
        )
    )

    train_data = cv2.ml.TrainData_create(
        x.astype(np.float32),
        cv2.ml.ROW_SAMPLE,
        encode_targets(y),
    )

    if not model.train(train_data):
        raise RuntimeError("OpenCV ANN_MLP training failed")

    return model


def predict_labels(model, x: np.ndarray) -> np.ndarray:
    _, raw = model.predict(x.astype(np.float32))
    if raw.ndim != 2 or raw.shape[1] != len(LABELS):
        raise RuntimeError(f"Unexpected prediction matrix shape: {raw.shape}")
    return np.argmax(raw, axis=1).astype(np.int32)


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    matrix = np.zeros((len(LABELS), len(LABELS)), dtype=np.int64)
    for truth, prediction in zip(y_true, y_pred):
        matrix[int(truth), int(prediction)] += 1
    return matrix


def metrics_from_confusion(matrix: np.ndarray) -> dict:
    if matrix.shape != (len(LABELS), len(LABELS)):
        raise ValueError("Unexpected confusion matrix shape")

    total = int(matrix.sum())
    correct = int(np.trace(matrix))
    accuracy = correct / total if total else 0.0

    per_class = {}
    f1_values = []

    for index, label in enumerate(LABELS):
        tp = int(matrix[index, index])
        fn = int(matrix[index, :].sum() - tp)
        fp = int(matrix[:, index].sum() - tp)
        support = int(matrix[index, :].sum())

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )

        f1_values.append(f1)
        per_class[label] = {
            "support": support,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    return {
        "accuracy": accuracy,
        "macro_f1": float(np.mean(f1_values)),
        "per_class": per_class,
        "confusion_matrix": matrix.tolist(),
    }


def summarize_counts(y: np.ndarray) -> dict[str, int]:
    counts = Counter(int(value) for value in y.tolist())
    return {
        label: int(counts.get(index, 0))
        for index, label in enumerate(LABELS)
    }


def evaluate_fold(
    *,
    train_sessions: tuple[SessionData, ...],
    held_out: SessionData,
    hidden_units: int,
    max_iter: int,
    seed: int,
) -> tuple[dict, np.ndarray, np.ndarray]:
    x_train, y_train = combine_sessions(train_sessions)

    model = train_mlp(
        x_train,
        y_train,
        hidden_units=hidden_units,
        max_iter=max_iter,
        seed=seed,
    )

    predictions = predict_labels(model, held_out.x)
    matrix = confusion_matrix(held_out.y, predictions)
    metrics = metrics_from_confusion(matrix)

    metrics.update(
        {
            "held_out_session": held_out.name,
            "train_sessions": [session.name for session in train_sessions],
            "train_counts": summarize_counts(y_train),
            "evaluation_counts": summarize_counts(held_out.y),
        }
    )

    return metrics, held_out.y, predictions


def print_metrics(title: str, metrics: dict) -> None:
    print()
    print(title)
    print(f"Accuracy : {metrics['accuracy']:.4f}")
    print(f"Macro F1 : {metrics['macro_f1']:.4f}")
    print("Confusion matrix (rows=true, cols=pred; forward,left,right):")
    for row in metrics["confusion_matrix"]:
        print(" ", row)

    print("Per-class:")
    for label in LABELS:
        item = metrics["per_class"][label]
        print(
            f"  {label:8s} "
            f"support={item['support']:3d} "
            f"precision={item['precision']:.4f} "
            f"recall={item['recall']:.4f} "
            f"f1={item['f1']:.4f}"
        )


def main() -> int:
    args = parse_args()

    if len(args.sessions) < 3:
        raise ValueError(
            "Use at least three independent traversal sessions for "
            "session-level cross-validation."
        )

    dataset_root = args.dataset_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("STEP 5 - SIMPLE MLP BASELINE")
    print("Evaluation: leave-one-session-out cross-validation")
    print("Random frame splitting: DISABLED")
    print("Class weighting/oversampling: DISABLED (baseline)")
    print("Preprocessing: BGR -> grayscale -> [0,1] -> flatten")
    print(f"Hidden units: {args.hidden_units}")
    print()

    sessions = tuple(
        load_session(dataset_root, session_name)
        for session_name in args.sessions
    )

    for session in sessions:
        print(
            f"{session.name}: "
            f"n={len(session.y)}, counts={summarize_counts(session.y)}"
        )

    fold_metrics = []
    all_true = []
    all_pred = []

    for fold_index, held_out in enumerate(sessions, start=1):
        training = tuple(
            session for session in sessions
            if session.name != held_out.name
        )

        metrics, y_true, y_pred = evaluate_fold(
            train_sessions=training,
            held_out=held_out,
            hidden_units=args.hidden_units,
            max_iter=args.max_iter,
            seed=args.seed + fold_index,
        )

        fold_metrics.append(metrics)
        all_true.append(y_true)
        all_pred.append(y_pred)

        print_metrics(
            f"=== FOLD {fold_index}: held out {held_out.name} ===",
            metrics,
        )

    pooled_true = np.concatenate(all_true)
    pooled_pred = np.concatenate(all_pred)
    pooled_matrix = confusion_matrix(pooled_true, pooled_pred)
    pooled_metrics = metrics_from_confusion(pooled_matrix)

    print_metrics("=== POOLED CROSS-VALIDATION RESULT ===", pooled_metrics)

    cv_report = {
        "model": {
            "type": "OpenCV ANN_MLP",
            "architecture": [
                2500,
                int(args.hidden_units),
                len(LABELS),
            ],
            "activation": "SIGMOID_SYM",
            "train_method": "RPROP",
            "max_iter": int(args.max_iter),
            "seed": int(args.seed),
            "class_weighting": "none",
        },
        "preprocessing": {
            "expected_input_shape_hwc": list(EXPECTED_SHAPE),
            "color_conversion": "BGR_TO_GRAYSCALE",
            "normalization": "divide_by_255",
            "flattened_features": 2500,
            "labels": list(LABELS),
        },
        "evaluation_protocol": {
            "type": "leave_one_session_out_cross_validation",
            "sessions": list(args.sessions),
            "random_frame_split": False,
        },
        "folds": fold_metrics,
        "pooled": pooled_metrics,
    }

    report_path = output_dir / "step05_simple_mlp_baseline_cv.json"
    report_path.write_text(
        json.dumps(cv_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    x_all, y_all = combine_sessions(sessions)
    final_model = train_mlp(
        x_all,
        y_all,
        hidden_units=args.hidden_units,
        max_iter=args.max_iter,
        seed=args.seed + 1000,
    )

    model_path = output_dir / "maze_navigation_simple_mlp_baseline.xml"
    final_model.save(str(model_path))

    metadata = {
        "model_file": model_path.name,
        "training_sessions": list(args.sessions),
        "training_counts": summarize_counts(y_all),
        "training_total": int(len(y_all)),
        "labels": list(LABELS),
        "input_shape_hwc": list(EXPECTED_SHAPE),
        "preprocessing": "BGR -> grayscale -> float32 / 255 -> flatten",
        "hidden_units": int(args.hidden_units),
        "class_weighting": "none",
        "status": (
            "baseline_only; review cross-validation turn recall before "
            "promoting to autonomous control"
        ),
    }

    metadata_path = output_dir / "maze_navigation_simple_mlp_baseline.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print()
    print("STEP05_SIMPLE_MLP_BASELINE_COMPLETE")
    print(f"CV report : {report_path}")
    print(f"Model     : {model_path}")
    print(f"Metadata  : {metadata_path}")
    print()
    print(
        "IMPORTANT: This is an unweighted baseline. Do not promote the model "
        "to autonomous control until pooled/fold turn recall is reviewed."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
