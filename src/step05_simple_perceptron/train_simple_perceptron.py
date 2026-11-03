"""Step 5 baseline: simple session-aware softmax perceptron.

This intentionally avoids the legacy CNN refinement path. The model is a
single linear multiclass layer (softmax regression / multiclass perceptron)
trained with NumPy only:

    50x50 RGB JPEG -> grayscale -> normalize to [0,1] -> flatten 2500
    -> affine layer (2500 x 3) -> softmax

Evaluation uses leave-one-session-out cross-validation, so neighboring frames
from the same traversal are never randomly split across train and evaluation
sets.

This controlled follow-up keeps the same single-layer model and preprocessing
while applying balanced class weights computed from each training fold only.
No oversampling is used, and held-out-session labels never influence weights.
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
DEFAULT_OUTPUT_DIR = REPO_ROOT / "models" / "step05_balanced_perceptron"

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
            "Train/evaluate a professor-aligned simple Step-5 softmax "
            "perceptron using session-level cross-validation."
        )
    )
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument(
        "--sessions",
        nargs="+",
        default=list(DEFAULT_SESSIONS),
        help="Session directory names to include.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--epochs", type=int, default=400)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument("--l2", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--class-weighting",
        choices=("balanced", "none"),
        default="balanced",
        help=(
            "Class-weight strategy. 'balanced' uses N/(K*n_c) from each "
            "training fold only; 'none' reproduces the unweighted objective."
        ),
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
    return gray.astype(np.float32).reshape(-1) / 255.0


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

    return SessionData(
        name=session_name,
        x=np.stack(vectors).astype(np.float32),
        y=np.asarray(labels, dtype=np.int32),
        paths=tuple(paths),
    )


def combine_sessions(sessions: Iterable[SessionData]) -> tuple[np.ndarray, np.ndarray]:
    sessions = tuple(sessions)
    if not sessions:
        raise ValueError("At least one session is required")
    return (
        np.concatenate([session.x for session in sessions], axis=0),
        np.concatenate([session.y for session in sessions], axis=0),
    )


def summarize_counts(y: np.ndarray) -> dict[str, int]:
    counts = Counter(int(value) for value in y.tolist())
    return {
        label: int(counts.get(index, 0))
        for index, label in enumerate(LABELS)
    }


def balanced_class_weights(y: np.ndarray) -> np.ndarray:
    """Return sklearn-style balanced weights N/(K*n_c) for LABELS."""
    if y.ndim != 1 or len(y) == 0:
        raise ValueError("y must be a non-empty 1D array")

    class_count = len(LABELS)
    counts = np.bincount(y.astype(np.int64), minlength=class_count)
    if np.any(counts <= 0):
        raise ValueError("Every class must be present to compute balanced weights")

    weights = len(y) / (class_count * counts.astype(np.float64))
    return weights.astype(np.float32)


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def train_perceptron(
    x: np.ndarray,
    y: np.ndarray,
    *,
    epochs: int,
    learning_rate: float,
    l2: float,
    seed: int,
    class_weights: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, list[float]]:
    if epochs <= 0:
        raise ValueError("epochs must be positive")
    if learning_rate <= 0:
        raise ValueError("learning_rate must be positive")
    if l2 < 0:
        raise ValueError("l2 must be non-negative")

    rng = np.random.default_rng(seed)
    feature_count = x.shape[1]
    class_count = len(LABELS)

    if class_weights is None:
        effective_class_weights = np.ones(class_count, dtype=np.float32)
    else:
        effective_class_weights = np.asarray(class_weights, dtype=np.float32)
        if effective_class_weights.shape != (class_count,):
            raise ValueError(
                f"class_weights must have shape {(class_count,)}, "
                f"got {effective_class_weights.shape}"
            )
        if not np.all(np.isfinite(effective_class_weights)):
            raise ValueError("class_weights must be finite")
        if np.any(effective_class_weights <= 0):
            raise ValueError("class_weights must be strictly positive")

    sample_weights = effective_class_weights[y]
    total_sample_weight = float(sample_weights.sum())
    if total_sample_weight <= 0:
        raise ValueError("Total sample weight must be positive")

    weights = rng.normal(
        loc=0.0,
        scale=0.01,
        size=(feature_count, class_count),
    ).astype(np.float32)
    bias = np.zeros(class_count, dtype=np.float32)

    targets = np.eye(class_count, dtype=np.float32)[y]
    losses: list[float] = []

    for _ in range(int(epochs)):
        logits = x @ weights + bias
        probabilities = _softmax(logits)

        clipped = np.clip(
            probabilities[np.arange(len(y)), y],
            1e-8,
            1.0,
        )
        data_loss = -float(
            np.sum(sample_weights * np.log(clipped)) / total_sample_weight
        )
        reg_loss = 0.5 * float(l2) * float(np.sum(weights * weights))
        losses.append(data_loss + reg_loss)

        gradient_logits = (
            (probabilities - targets)
            * sample_weights[:, None]
            / total_sample_weight
        )
        gradient_weights = x.T @ gradient_logits + float(l2) * weights
        gradient_bias = gradient_logits.sum(axis=0)

        weights -= float(learning_rate) * gradient_weights.astype(np.float32)
        bias -= float(learning_rate) * gradient_bias.astype(np.float32)

    return weights, bias, losses


def predict_scores(
    x: np.ndarray,
    weights: np.ndarray,
    bias: np.ndarray,
) -> np.ndarray:
    return _softmax(x @ weights + bias)


def predict_labels(
    x: np.ndarray,
    weights: np.ndarray,
    bias: np.ndarray,
) -> np.ndarray:
    return np.argmax(predict_scores(x, weights, bias), axis=1).astype(np.int32)


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


def evaluate_fold(
    *,
    train_sessions: tuple[SessionData, ...],
    held_out: SessionData,
    epochs: int,
    learning_rate: float,
    l2: float,
    seed: int,
    class_weighting: str,
) -> tuple[dict, np.ndarray, np.ndarray]:
    x_train, y_train = combine_sessions(train_sessions)

    if class_weighting == "balanced":
        fold_class_weights = balanced_class_weights(y_train)
    elif class_weighting == "none":
        fold_class_weights = None
    else:
        raise ValueError(f"Unsupported class_weighting: {class_weighting}")

    weights, bias, losses = train_perceptron(
        x_train,
        y_train,
        epochs=epochs,
        learning_rate=learning_rate,
        l2=l2,
        seed=seed,
        class_weights=fold_class_weights,
    )

    predictions = predict_labels(held_out.x, weights, bias)
    matrix = confusion_matrix(held_out.y, predictions)
    metrics = metrics_from_confusion(matrix)

    metrics.update(
        {
            "held_out_session": held_out.name,
            "train_sessions": [session.name for session in train_sessions],
            "train_counts": summarize_counts(y_train),
            "evaluation_counts": summarize_counts(held_out.y),
            "class_weighting": class_weighting,
            "class_weights": (
                {
                    label: float(fold_class_weights[index])
                    for index, label in enumerate(LABELS)
                }
                if fold_class_weights is not None
                else {label: 1.0 for label in LABELS}
            ),
            "final_training_loss": float(losses[-1]),
        }
    )
    return metrics, held_out.y, predictions


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

    print("STEP 5 - BALANCED SIMPLE SOFTMAX PERCEPTRON")
    print("Evaluation: leave-one-session-out cross-validation")
    print("Random frame splitting: DISABLED")
    print(f"Class weighting: {args.class_weighting}")
    print("Oversampling: DISABLED")
    print("Preprocessing: BGR -> grayscale -> [0,1] -> flatten")
    print(f"Epochs: {args.epochs}")
    print(f"Learning rate: {args.learning_rate}")
    print(f"L2: {args.l2}")
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
            epochs=args.epochs,
            learning_rate=args.learning_rate,
            l2=args.l2,
            seed=args.seed + fold_index,
            class_weighting=args.class_weighting,
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
    pooled_metrics = metrics_from_confusion(
        confusion_matrix(pooled_true, pooled_pred)
    )
    print_metrics("=== POOLED CROSS-VALIDATION RESULT ===", pooled_metrics)

    report = {
        "model": {
            "type": "single_layer_softmax_perceptron",
            "input_features": 2500,
            "outputs": len(LABELS),
            "epochs": int(args.epochs),
            "learning_rate": float(args.learning_rate),
            "l2": float(args.l2),
            "seed": int(args.seed),
            "class_weighting": args.class_weighting,
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

    report_path = output_dir / "step05_balanced_perceptron_cv.json"
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    x_all, y_all = combine_sessions(sessions)
    full_class_weights = (
        balanced_class_weights(y_all)
        if args.class_weighting == "balanced"
        else None
    )
    weights, bias, losses = train_perceptron(
        x_all,
        y_all,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        l2=args.l2,
        seed=args.seed + 1000,
        class_weights=full_class_weights,
    )

    model_path = output_dir / "maze_navigation_simple_perceptron_balanced.npz"
    np.savez_compressed(
        model_path,
        weights=weights,
        bias=bias,
        labels=np.asarray(LABELS),
        input_shape=np.asarray(EXPECTED_SHAPE, dtype=np.int32),
    )

    metadata = {
        "model_file": model_path.name,
        "training_sessions": list(args.sessions),
        "training_counts": summarize_counts(y_all),
        "training_total": int(len(y_all)),
        "labels": list(LABELS),
        "input_shape_hwc": list(EXPECTED_SHAPE),
        "preprocessing": "BGR -> grayscale -> float32 / 255 -> flatten",
        "class_weighting": args.class_weighting,
        "class_weights": (
            {
                label: float(full_class_weights[index])
                for index, label in enumerate(LABELS)
            }
            if full_class_weights is not None
            else {label: 1.0 for label in LABELS}
        ),
        "final_training_loss": float(losses[-1]),
        "status": (
            "baseline_only; review cross-validation turn recall before "
            "promoting to shadow or autonomous control"
        ),
    }

    metadata_path = output_dir / "maze_navigation_simple_perceptron_balanced.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print()
    print("STEP05_BALANCED_PERCEPTRON_COMPLETE")
    print(f"CV report : {report_path}")
    print(f"Model     : {model_path}")
    print(f"Metadata  : {metadata_path}")
    print()
    print(
        "IMPORTANT: Compare this balanced result against the frozen unweighted "
        "baseline before any shadow or robot-control promotion."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
