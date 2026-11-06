"""Build the selected 2.5x turn-weight Step-5 candidate artifact.

This does not replace the current final unweighted model. It exports a separate
candidate with explicit provenance for offline/live qualification only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import h5py
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

SESSIONS = (
    "session_20261103_01",
    "session_20261103_02",
    "session_20261103_03",
)
TURN_MULTIPLIER = 2.5
DATASET_ZIP_SHA256 = "887d4f8e56c2c4274947505984ebab4071512660acce6f28ec5d0b5524a6cb2e"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--dataset-root", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--epochs", type=int, default=3200)
    p.add_argument("--learning-rate", type=float, default=0.01)
    p.add_argument("--l2", type=float, default=1e-4)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def keras_model_config() -> dict:
    return {
        "class_name": "Sequential",
        "config": {
            "name": "sequential",
            "layers": [
                {
                    "class_name": "InputLayer",
                    "config": {
                        "batch_shape": [None, 2500],
                        "dtype": "float32",
                        "name": "input_layer",
                    },
                },
                {
                    "class_name": "Dense",
                    "config": {
                        "name": "direction",
                        "units": 3,
                        "activation": "softmax",
                        "use_bias": True,
                    },
                },
            ],
            "build_input_shape": [None, 2500],
        },
    }


def write_h5(path: Path, weights: np.ndarray, bias: np.ndarray) -> None:
    with h5py.File(path, "w") as handle:
        handle.attrs["backend"] = "numpy"
        handle.attrs["keras_version"] = "experimental_numpy_export"
        handle.attrs["model_config"] = json.dumps(keras_model_config())

        direction = handle.require_group(
            "model_weights/direction/sequential/direction"
        )
        direction.create_dataset("kernel", data=weights.astype(np.float32))
        direction.create_dataset("bias", data=bias.astype(np.float32))


def main() -> int:
    args = parse_args()
    dataset_root = args.dataset_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    sessions = tuple(load_session(dataset_root, name) for name in SESSIONS)
    class_weights = np.asarray(
        [1.0, TURN_MULTIPLIER, TURN_MULTIPLIER],
        dtype=np.float32,
    )

    fold_records = []
    pooled = np.zeros((3, 3), dtype=np.int64)
    for fold_index, held_out in enumerate(sessions, start=1):
        training = tuple(s for s in sessions if s.name != held_out.name)
        x_train, y_train = combine_sessions(training)
        weights, bias, losses = train_perceptron(
            x_train,
            y_train,
            epochs=args.epochs,
            learning_rate=args.learning_rate,
            l2=args.l2,
            seed=args.seed + fold_index,
            class_weights=class_weights,
        )
        pred = predict_labels(held_out.x, weights, bias)
        matrix = confusion_matrix(held_out.y, pred)
        pooled += matrix
        fold_records.append(
            {
                "held_out_session": held_out.name,
                "seed": args.seed + fold_index,
                "train_counts": summarize_counts(y_train),
                "evaluation_counts": summarize_counts(held_out.y),
                "class_weights": {
                    "forward": 1.0,
                    "left": TURN_MULTIPLIER,
                    "right": TURN_MULTIPLIER,
                },
                "final_training_loss": float(losses[-1]),
                "metrics": metrics_from_confusion(matrix),
            }
        )

    pooled_metrics = metrics_from_confusion(pooled)
    forward_support = int(pooled[0].sum())
    forward_to_turn = float(pooled[0, 1] + pooled[0, 2]) / forward_support

    x_all, y_all = combine_sessions(sessions)
    weights, bias, losses = train_perceptron(
        x_all,
        y_all,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        l2=args.l2,
        seed=args.seed,
        class_weights=class_weights,
    )

    npz_path = output_dir / "maze_navigation_simple_perceptron_turn2p5_candidate.npz"
    np.savez_compressed(
        npz_path,
        weights=weights,
        bias=bias,
        labels=np.asarray(LABELS),
        input_shape=np.asarray((50, 50, 3), dtype=np.int32),
    )

    h5_path = output_dir / "maze_navigation_simple_perceptron_turn2p5_candidate.h5"
    write_h5(h5_path, weights, bias)

    metadata = {
        "model_file": h5_path.name,
        "architecture": "2500 -> Dense(3, softmax)",
        "labels": list(LABELS),
        "config": {
            "epochs": int(args.epochs),
            "learning_rate": float(args.learning_rate),
            "l2": float(args.l2),
            "seed": int(args.seed),
            "class_weighting": "partial_turn_multiplier",
            "turn_multiplier": TURN_MULTIPLIER,
            "class_weights": {
                "forward": 1.0,
                "left": TURN_MULTIPLIER,
                "right": TURN_MULTIPLIER,
            },
        },
        "preprocessing": "OpenCV BGR2GRAY -> float32 /255 -> flatten 2500",
        "input_image_shape": [50, 50, 3],
        "training_counts": summarize_counts(y_all),
        "training_total": int(len(y_all)),
        "dataset_zip_sha256": DATASET_ZIP_SHA256,
        "evaluation_protocol": "leave_one_session_out",
        "folds": fold_records,
        "pooled": pooled_metrics,
        "forward_to_turn_rate": forward_to_turn,
        "final_training_loss": float(losses[-1]),
        "status": (
            "EXPERIMENTAL candidate only; current final unweighted model remains "
            "authoritative until bounded Step-6 live qualification passes"
        ),
    }

    metadata_path = output_dir / "maze_navigation_simple_perceptron_turn2p5_candidate.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "h5_sha256": sha256(h5_path),
        "json_sha256": sha256(metadata_path),
        "npz_sha256": sha256(npz_path),
        "turn_multiplier": TURN_MULTIPLIER,
        "dataset_zip_sha256": DATASET_ZIP_SHA256,
    }
    manifest_path = output_dir / "candidate_sha256_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("STEP05_PARTIAL_WEIGHT_CANDIDATE_COMPLETE")
    print(f"H5={h5_path}")
    print(f"JSON={metadata_path}")
    print(f"NPZ={npz_path}")
    print(f"MANIFEST={manifest_path}")
    print(
        "POOLED "
        f"Acc={pooled_metrics['accuracy']:.4f} "
        f"MacroF1={pooled_metrics['macro_f1']:.4f} "
        f"F={pooled_metrics['per_class']['forward']['recall']:.4f} "
        f"L={pooled_metrics['per_class']['left']['recall']:.4f} "
        f"R={pooled_metrics['per_class']['right']['recall']:.4f} "
        f"Fwd->Turn={forward_to_turn:.2%}"
    )
    print(f"H5_SHA256={manifest['h5_sha256']}")
    print(f"JSON_SHA256={manifest['json_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
