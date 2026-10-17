# Step 5C recovery-session audit — 2026-10-17

Four independent human-controlled recovery sessions were recorded after the three failed v3 autonomous Step-6 attempts. In every recovery session the human W/A/D command controlled the motors; v3 ran in shadow mode only.

## Per-session v3 shadow results

| Session | Frames | Agreement | Forward recall | Left recall | Right recall | Human forward -> v3 left | Human forward -> v3 right |
|---|---:|---:|---:|---:|---:|---:|---:|
| recovery_01 | 631 | 87.48% | 89.03% | 78.79% | 69.70% | 14 | 48 |
| recovery_02 | 633 | 94.94% | 97.03% | 83.33% | 67.74% | 11 | 6 |
| recovery_03 | 644 | 87.42% | 87.54% | 86.67% | 85.71% | 10 | 63 |
| recovery_04 | 665 | 84.21% | 84.19% | 90.00% | 79.41% | 33 | 62 |

Aggregate recovery evidence:

- Frames: 2,573
- Agreement: 2,276 / 2,573 = 88.46%
- Forward recall: 89.37% (support 2,324)
- Left recall: 84.55% (support 123)
- Right recall: 75.40% (support 126)
- Forward precision: 98.39%
- Left precision: 56.22%
- Right precision: 34.30%

Aggregate confusion matrix, rows = human command and columns = v3 prediction:

| Human \ v3 | forward | left | right |
|---|---:|---:|---:|
| forward | 2077 | 68 | 179 |
| left | 16 | 104 | 3 |
| right | 18 | 13 | 95 |

## Main failure pattern

The strongest recurring defect is no longer merely missed right turns. Several recovery laps contain long post-turn or straight-corridor states where the human correctly commands forward but v3 continues to predict right.

Examples include:

- recovery_01 around robot position approximately (0.30, 0.13): a 5-second window with 28/28 human-forward frames predicted as right.
- recovery_03 around approximately (0.43, 0.11): 22/25 errors in a 5-second forward window, mostly predicted right.
- recovery_03 around approximately (0.88, 2.10): another sustained forward-to-right error region.
- recovery_04 around approximately (0.05, 0.17): a 5-second window with 27/27 human-forward frames predicted as right.

This evidence is consistent with the closed-loop oscillation seen in the failed autonomous runs: v3 does not reliably distinguish turn completion / post-turn forward states from continued right-turn states.

## Why the evaluation method changed

The accepted Step-4 dataset contains 2,386 frames captured across only three manual sessions. Frames were recorded at roughly 0.1-second intervals. The earlier Step-5 notebooks randomly split individual frames, so adjacent near-duplicate frames from the same lap could appear in both training and evaluation.

The Step 5C path therefore evaluates whole sessions rather than randomly mixing individual frames.

## Locked v4 split

The split was fixed before v4 training:

- Train: original_01, original_02, original_03, recovery_01, recovery_03
- Validation: recovery_02
- Test: recovery_04

Counts:

- Train: 3,661 images — forward 3,290, left 185, right 186
- Validation: 633 images — forward 572, left 30, right 31
- Test: 665 images — forward 601, left 30, right 34
- Total: 4,959 images

Dataset package:

- Filename: step05c_session_dataset_v1.zip
- SHA256: 1241b54cd3f6936c88e3fd659c729c69389df4ae67c11141cc9829757f164148

## Gate

The next model is maze_navigation_model_v4.h5. It keeps the same 50x50 three-class CNN architecture and fixes class-weight alpha at 0.75 so the primary experimental change is session-aware data/evaluation plus recovery-state coverage.

v4 must complete the session-aware Colab training/evaluation and then pass a new live human-controlled shadow validation before autonomous Step 6 is attempted again.
