# Step 5C v4 Colab results — 2026-10-17

The session-aware v4 training run completed successfully in Google Colab.

## Training configuration

- Method: session-aware split
- Random seed: 42
- Input: 50x50 RGB
- Classes: forward, left, right
- Fixed class-weight alpha: 0.75
- Train sessions: original_01, original_02, original_03, recovery_01, recovery_03
- Validation session: recovery_02
- Held-out test session: recovery_04
- Train images: 3,661
- Validation images: 633
- Test images: 665
- Epochs completed: 12
- Early stopping restored the best validation-loss weights.

## Validation — recovery_02

- Accuracy: 94.94%
- Macro-F1: 0.7944
- Forward recall: 97.03%
- Left recall: 73.33%
- Right recall: 77.42%
- Forward -> left: 2 / 572
- Forward -> right: 15 / 572

Confusion matrix, rows = human label and columns = model prediction:

| Human \ v4 | forward | left | right |
|---|---:|---:|---:|
| forward | 555 | 2 | 15 |
| left | 2 | 22 | 6 |
| right | 4 | 3 | 24 |

## Held-out test — recovery_04

- Accuracy: 91.43%
- Macro-F1: 0.7357
- Forward recall: 92.51%
- Left recall: 73.33%
- Right recall: 88.24%
- Forward precision: 99.29%
- Left precision: 61.11%
- Right precision: 43.48%
- Forward -> left: 12 / 601
- Forward -> right: 33 / 601

Confusion matrix:

| Human \ v4 | forward | left | right |
|---|---:|---:|---:|
| forward | 556 | 12 | 33 |
| left | 2 | 22 | 6 |
| right | 2 | 2 | 30 |

## Direct comparison with v3 on the same recovery_04 session

v3 recovery_04:
- Agreement: 84.21%
- Forward recall: 84.19%
- Left recall: 90.00%
- Right recall: 79.41%
- Forward -> left: 33
- Forward -> right: 62

v4 held-out recovery_04:
- Accuracy/agreement: 91.43%
- Forward recall: 92.51%
- Left recall: 73.33%
- Right recall: 88.24%
- Forward -> left: 12
- Forward -> right: 33

Changes:
- Overall agreement: +7.22 percentage points
- Forward recall: +8.32 percentage points
- Right recall: +8.83 percentage points
- Forward -> left errors: 33 -> 12 (63.6% reduction)
- Forward -> right errors: 62 -> 33 (46.8% reduction)
- Left recall: 90.00% -> 73.33% (regression; remains a live-shadow concern)

## Model artifact

- File: maze_navigation_model_v4.h5
- Size: 1,119,800 bytes
- SHA256: 1E47D19D18AF5C58E03DA55DAAED04B91D4DCC33A7EE13258AA57CEC91FE099D
- Local model load/warm-up: PASS
- Input shape: (None, 50, 50, 3)
- Output shape: (None, 3)
- Softmax output sum on warm-up: 1.0

## Gate decision

Offline/session-aware gate: PASS FOR LIVE SHADOW VALIDATION.

This is not an autonomous-control pass. The remaining left-recall regression and still-low turn precision require a new human-controlled live shadow run. Autonomous Step 6 remains blocked until that sequential live gate is reviewed.
