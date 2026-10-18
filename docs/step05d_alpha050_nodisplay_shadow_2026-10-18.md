# Step 5D alpha-0.50 no-display live shadow — 2026-10-18

A fresh full human-controlled live-shadow traversal was completed with the diagnostic alpha-0.50 model while the OpenCV preview path was disabled.

## Runtime / crash-isolation result

The run completed without a CoppeliaSim crash.

Active stack:
- CoppeliaSim 4.7.0 rev4
- ZMQ remote API
- manual W/A/D motor control
- raw 50x50 camera acquisition
- NumPy frame conversion
- TensorFlow 2.21 preprocessing and inference
- alpha-0.50 CNN model
- CSV scoring/logging

Disabled:
- OpenCV preview / imshow GUI

No new CoppeliaSim Application Error / Windows Error Reporting crash event was recorded during the run.

This means the full TensorFlow/CNN inference path can complete a traversal without the OpenCV preview path. Because the historical crash is intermittent, this does not prove that OpenCV is the root cause, but it makes the display path a remaining suspect rather than TensorFlow/CNN inference alone.

## Live shadow result

Scored frames: 1,163
Agreement: 1,063 / 1,163 = 91.40%

Confusion matrix, rows = human command and columns = model prediction:

| Human \ model | forward | left | right |
|---|---:|---:|---:|
| forward | 962 | 17 | 62 |
| left | 13 | 49 | 3 |
| right | 5 | 0 | 52 |

Per-class metrics:
- forward precision 98.16%, recall 92.41%, F1 95.20%, support 1,041
- left precision 74.24%, recall 75.38%, F1 74.81%, support 65
- right precision 44.44%, recall 91.23%, F1 59.77%, support 57

Forward false-turns:
- forward -> left: 17 / 1,041 = 1.63%
- forward -> right: 62 / 1,041 = 5.96%
- total forward false-turn rate: 79 / 1,041 = 7.59%

Sequential behavior:
- longest disagreement streak: 26 scored frames
- longest forward false-left streak: 7 frames
- longest forward false-right streak: 24 frames, approximately 137.015-139.781 s
- the 24-frame false-right streak had mean confidence 0.949, median 0.953, max 0.983; 23/24 frames were >=0.90 confidence

The dominant remaining failure is therefore still a sustained, confidently wrong forward -> right block.

## Comparison with v4 fresh live shadow

| Metric | v4 | alpha-0.50 no-display |
|---|---:|---:|
| agreement | 84.65% | 91.40% |
| forward recall | 83.90% | 92.41% |
| left recall | 81.58% | 75.38% |
| right recall | 100.00% | 91.23% |
| forward -> left | 4.82% | 1.63% |
| forward -> right | 11.28% | 5.96% |
| total forward false-turn rate | 16.10% | 7.59% |
| left precision | 44.93% | 74.24% |
| right precision | 32.62% | 44.44% |
| longest disagreement streak | 20 | 26 |

Alpha 0.50 materially improves overall false-turn behavior and turn precision, but does not eliminate the sequential failure mode. The 24-frame high-confidence false-right block is worse than the v4 longest disagreement streak and is unsafe for direct autonomous actuation.

## Gate decision

ALPHA-0.50 LIVE SHADOW GATE: FAIL FOR AUTONOMOUS STEP 6.

This is a materially better diagnostic model than v4, but not yet a safe autonomous candidate.

Do not add controller heuristics to conceal the model-level false-right block.

## Next model decision

The calibration sweep showed that reducing class-weight strength helped false-turn precision but alpha 0.50 still exhibits a sustained high-confidence false-right block in fresh live data.

The next model/data remediation should target the state represented by the 137-140 s hotspot rather than merely lowering class-weight alpha again. A targeted review of the corresponding logged camera frames / route state should precede any further retraining.
