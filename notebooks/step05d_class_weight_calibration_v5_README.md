# Step 5D — Session-aware class-weight calibration for v5

This notebook is the next controlled experiment after v4 passed the session-aware offline check but failed a fresh live shadow traversal.

## Why v5 is needed

v4 live shadow:

- agreement: 84.65%
- forward recall: 83.90%
- left recall: 81.58%
- right recall: 100.00%
- forward -> left: 38 / 789 = 4.82%
- forward -> right: 89 / 789 = 11.28%
- total forward false-turn rate: 16.10%
- longest disagreement streak: 20 frames

The pattern is turn over-prediction, especially false-right predictions during true-forward travel.

## Controlled variable

Only class-weight strength changes.

Candidates:

- alpha 0.75
- alpha 0.50
- alpha 0.25
- alpha 0.00

Everything else remains fixed: session-aware dataset, split, preprocessing, architecture, optimizer, random seed, and early stopping.

## Fixed selection rule

Use recovery_02 validation only.

Eligibility:
- left recall >= 70%
- right recall >= 70%

Among eligible candidates:
1. minimize longest consecutive forward false-turn streak;
2. minimize total forward false-turn rate;
3. maximize macro-F1.

Recovery_04 is evaluated only after selection. It has already been inspected for v4, so it is a repeat reference rather than a pristine untouched test.

## Expected outputs

The Colab run saves:

- maze_navigation_model_v5.h5
- step05d_v5_metrics.json
- step05d_v5_candidate_validation_metrics.csv
- step05d_v5_reference_confusion.csv
- step05d_v5_selected_config.json

A fresh live shadow traversal remains mandatory before any autonomous Step 6 retry.
