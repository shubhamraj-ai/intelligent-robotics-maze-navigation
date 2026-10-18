# Step 5F v6 Colab results — 2026-10-18

## Artifact set

Google Drive outputs confirmed:
- maze_navigation_model_v6.h5
- step05f_v6_metrics.json
- step05f_v6_reference_confusion.csv
- step05f_v6_history.csv

v6 method:
- session-aware targeted hard-negative retraining
- class-weight alpha = 0.50
- train = 3,701
- validation recovery_02 = 633
- reference recovery_04 = 665
- epochs completed = 18

## Validation comparison: v6 vs alpha-0.50 baseline

Both use recovery_02.

| Metric | alpha-0.50 baseline | v6 | delta |
|---|---:|---:|---:|
| accuracy | 96.8404% | 96.3665% | -0.4739 pp |
| macro-F1 | 0.83709 | 0.82787 | -0.00923 |
| forward recall | 99.6503% | 99.3007% | -0.3496 pp |
| left recall | 73.3333% | 73.3333% | 0 |
| right recall | 67.7419% | 64.5161% | -3.2258 pp |
| forward->left | 1 | 2 | +1 |
| forward->right | 1 | 2 | +1 |
| forward false-turn rate | 0.3497% | 0.6993% | +0.3497 pp |

v6 validation confusion:
- forward [568, 2, 2]
- left [4, 22, 4]
- right [10, 1, 20]

The prior Step 5D minimum turn-recall floor was 70% for both left and right. v6 right recall is 64.52%, so v6 does not meet that prior offline eligibility floor.

## recovery_04 repeat-reference comparison: v6 vs alpha-0.50 baseline

The alpha-0.50 model was re-evaluated locally on the same session-aware package using the same 50x50 JPEG preprocessing.

| Metric | alpha-0.50 baseline | v6 | delta |
|---|---:|---:|---:|
| accuracy | 95.3383% | 95.3383% | 0 |
| macro-F1 | 0.82661 | 0.82346 | -0.00315 |
| forward recall | 96.5058% | 97.0050% | +0.4992 pp |
| left recall | 76.6667% | 73.3333% | -3.3334 pp |
| right recall | 91.1765% | 85.2941% | -5.8824 pp |
| forward->left | 11 | 11 | 0 |
| forward->right | 10 | 7 | -3 |
| total forward false-turns | 21 | 18 | -3 |

Alpha-0.50 reference confusion:
- forward [580, 11, 10]
- left [4, 23, 3]
- right [2, 1, 31]

v6 reference confusion:
- forward [583, 11, 7]
- left [7, 22, 1]
- right [3, 2, 29]

Interpretation:
- v6 does reduce forward->right errors on recovery_04 from 10 to 7;
- however it shifts the decision boundary enough to reduce both left-turn and especially right-turn recall;
- overall accuracy is unchanged and macro-F1 is slightly worse;
- on the independent validation session, forward false turns and right recall are both worse.

## Gate decision

STEP 5F v6 OFFLINE GATE: FAIL FOR FRESH LIVE SHADOW PROMOTION.

Do not run a v6 live shadow merely because the targeted hard-negative frames reduced one repeat-reference error count. The controlled validation result does not demonstrate general improvement over alpha 0.50.

Do not run autonomous Step 6.

## Recommended next data/model experiment

The evidence indicates a boundary-timing trade-off:
- adding only forward hard negatives teaches the model to delay right-turn decisions;
- that helps some false-right states;
- but it also suppresses legitimate right-turn recognition.

The next data collection should therefore be paired and balanced rather than forward-only:
1. collect multiple clean manual passes;
2. preserve forward frames immediately before right-turn onset as hard negatives;
3. preserve true right-turn onset frames immediately after the human begins D as matched hard positives;
4. retain analogous left-turn boundary examples so left recall is not sacrificed;
5. reserve at least one fresh paired session for validation rather than training.

Keep the same CNN architecture and preprocessing unless paired boundary data still fails.
