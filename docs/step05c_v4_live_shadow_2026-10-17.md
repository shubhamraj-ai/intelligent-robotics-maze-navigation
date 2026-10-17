# Step 5C v4 live shadow result — 2026-10-17

The v4 CNN was validated in a fresh human-controlled live shadow traversal after the session-aware Colab run.

The human W/A/D commands controlled the PioneerP3DX. v4 predicted forward/left/right only and never actuated the motors.

## Result

- Scored frames: 873
- Agreement: 739 / 873 = 84.65%
- Longest disagreement streak: 20 frames
- Longest false-left streak while human=forward: 9 frames

Confusion matrix, rows = human command and columns = v4 prediction:

| Human \ v4 | forward | left | right |
|---|---:|---:|---:|
| forward | 662 | 38 | 89 |
| left | 1 | 31 | 6 |
| right | 0 | 0 | 46 |

Per-class live shadow metrics:

- Forward: precision 99.85%, recall 83.90%, F1 91.18%, support 789
- Left: precision 44.93%, recall 81.58%, F1 57.94%, support 38
- Right: precision 32.62%, recall 100.00%, F1 49.20%, support 46
- False-left while human=forward: 38 / 789 = 4.82%
- False-right while human=forward: 89 / 789 = 11.28%
- Total forward false-turn rate: 127 / 789 = 16.10%

## Sequential error evidence

The main operational defect is sustained over-prediction of turns during true-forward travel.

Longest scored error runs included:

- forward -> right: 20 frames, approximately 111.5–114.6 s
- forward -> right: 15 frames, approximately 60.4–62.6 s
- forward -> right: 10 frames, approximately 131.8–133.0 s
- forward -> left: 9 frames, approximately 83.2–84.3 s
- forward -> right: 9 frames, approximately 63.8–65.0 s

A 5-second hotspot around 111.5–116.5 s contained 20 errors in 23 scored frames; the segment was almost entirely human-forward while v4 continued to predict right.

## Comparison with the earlier v3 live shadow

Earlier v3 live shadow:

- agreement 95.60%
- forward -> left 20 / 889 = 2.25%
- forward -> right 16 / 889 = 1.80%
- left recall 91.30%
- right recall 93.02%

v4 live shadow:

- agreement 84.65%
- forward -> left 38 / 789 = 4.82%
- forward -> right 89 / 789 = 11.28%
- left recall 81.58%
- right recall 100.00%

Although v4 improved the independent recovery_04 offline result versus v3, it materially regressed on a fresh live shadow trajectory. In particular, right recall reached 100% but right precision fell to 32.62%, showing strong turn over-prediction.

## Gate decision

LIVE SHADOW GATE: FAIL.

Autonomous Step 6 remains blocked. No controller heuristic should be added to mask this model defect.

## Next controlled experiment

The current v4 training set contains 3,290 forward, 185 left, and 186 right training frames. With class-weight alpha 0.75, normalized sample weights are approximately:

- forward: 0.564
- left: 4.880
- right: 4.861

Given the live pattern — perfect right recall but very low right precision and a 16.10% total forward false-turn rate — the next experiment should calibrate class-weight strength downward while keeping the architecture, data split, preprocessing, and action definitions fixed.

Candidate alphas should be selected using validation data only. Recovery_04 must remain excluded from candidate selection; because it has already been inspected for v4, it should be treated as a repeat reference rather than a pristine final test for subsequent candidates. A fresh live shadow traversal remains the decisive external gate.
