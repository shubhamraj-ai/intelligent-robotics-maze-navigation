"""Offline Step-5 partial class-weight sweep for the simple perceptron.

This experiment keeps the professor-aligned 2500->3 softmax perceptron,
session-level cross-validation, preprocessing, optimizer schedule, and dataset
fixed. Only the relative turn-class weight changes.

It is intentionally isolated from the selected Step-6 runtime/model.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.step05_simple_perceptron.train_simple_perceptron import (
    LABELS,
    combine_sessions,
    confusion_matrix,
    load_session,
    metrics_from_confusion,
    predict_labels,
    summarize_counts,
    train_perceptron,
)

DEFAULT_SESSIONS = (
    "session_20261103_01",
    "session_20261103_02",
    "session_20261103_03",
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-root", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--turn-multipliers", nargs="+", type=float, required=True)
    p.add_argument("--seeds", nargs="+", type=int, default=[42])
    p.add_argument("--epochs", type=int, default=3200)
    p.add_argument("--learning-rate", type=float, default=0.01)
    p.add_argument("--l2", type=float, default=1e-4)
    return p.parse_args()


def pooled_row(matrix: np.ndarray, *, multiplier: float, seed: int) -> dict:
    metrics = metrics_from_confusion(matrix)
    forward_support = int(matrix[0, :].sum())
    forward_to_turn = (
        float(matrix[0, 1] + matrix[0, 2]) / forward_support
        if forward_support
        else 0.0
    )
    recalls = {
        label: float(metrics["per_class"][label]["recall"])
        for label in LABELS
    }
    return {
        "turn_multiplier": float(multiplier),
        "seed": int(seed),
        "accuracy": float(metrics["accuracy"]),
        "macro_f1": float(metrics["macro_f1"]),
        "forward_recall": recalls["forward"],
        "left_recall": recalls["left"],
        "right_recall": recalls["right"],
        "mean_turn_recall": (recalls["left"] + recalls["right"]) / 2.0,
        "min_turn_recall": min(recalls["left"], recalls["right"]),
        "forward_to_turn_rate": forward_to_turn,
        "confusion_matrix": matrix.tolist(),
    }


def main() -> int:
    args = parse_args()
    if any(m <= 0 for m in args.turn_multipliers):
        raise ValueError("Turn multipliers must be > 0")

    dataset_root = args.dataset_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    sessions = tuple(load_session(dataset_root, name) for name in DEFAULT_SESSIONS)

    print("STEP-5 PARTIAL CLASS-WEIGHT SWEEP")
    print("Architecture: grayscale 50x50 -> flatten 2500 -> linear softmax 3")
    print("Evaluation: leave-one-session-out CV")
    print("Forward weight: 1.0")
    print("Left/right weights: turn_multiplier")
    print(f"Epochs={args.epochs} lr={args.learning_rate} l2={args.l2}")
    print(f"Multipliers={args.turn_multipliers}")
    print(f"Seeds={args.seeds}")
    for session in sessions:
        print(f"{session.name}: {summarize_counts(session.y)}")

    rows: list[dict] = []
    raw: list[dict] = []

    for multiplier in args.turn_multipliers:
        class_weights = np.asarray([1.0, multiplier, multiplier], dtype=np.float32)
        for seed in args.seeds:
            pooled = np.zeros((3, 3), dtype=np.int64)
            fold_results = []

            for held_out in sessions:
                training = tuple(s for s in sessions if s.name != held_out.name)
                x_train, y_train = combine_sessions(training)
                weights, bias, losses = train_perceptron(
                    x_train,
                    y_train,
                    epochs=args.epochs,
                    learning_rate=args.learning_rate,
                    l2=args.l2,
                    seed=seed,
                    class_weights=class_weights,
                )
                pred = predict_labels(held_out.x, weights, bias)
                matrix = confusion_matrix(held_out.y, pred)
                pooled += matrix
                fold_metrics = metrics_from_confusion(matrix)
                fold_results.append(
                    {
                        "held_out_session": held_out.name,
                        "final_loss": float(losses[-1]),
                        "metrics": fold_metrics,
                    }
                )

            row = pooled_row(pooled, multiplier=multiplier, seed=seed)
            rows.append(row)
            raw.append(
                {
                    "turn_multiplier": multiplier,
                    "seed": seed,
                    "class_weights": {
                        "forward": 1.0,
                        "left": multiplier,
                        "right": multiplier,
                    },
                    "folds": fold_results,
                    "pooled": row,
                }
            )

            print(
                "M={:.3f} seed={} | Acc={:.4f} MacroF1={:.4f} "
                "F={:.4f} L={:.4f} R={:.4f} MeanTurn={:.4f} "
                "Fwd->Turn={:.2%}".format(
                    multiplier,
                    seed,
                    row["accuracy"],
                    row["macro_f1"],
                    row["forward_recall"],
                    row["left_recall"],
                    row["right_recall"],
                    row["mean_turn_recall"],
                    row["forward_to_turn_rate"],
                )
            )

    csv_path = output_dir / "partial_weight_sweep_summary.csv"
    fields = [
        "turn_multiplier",
        "seed",
        "accuracy",
        "macro_f1",
        "forward_recall",
        "left_recall",
        "right_recall",
        "mean_turn_recall",
        "min_turn_recall",
        "forward_to_turn_rate",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in fields})

    json_path = output_dir / "partial_weight_sweep_raw.json"
    json_path.write_text(
        json.dumps(
            {
                "dataset_root": str(dataset_root),
                "sessions": list(DEFAULT_SESSIONS),
                "epochs": args.epochs,
                "learning_rate": args.learning_rate,
                "l2": args.l2,
                "results": raw,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"CSV={csv_path}")
    print(f"JSON={json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
