# Step 5D v5 calibration results — 2026-10-17

The Step 5D Colab calibration run completed successfully and generated all expected artifacts.

## Candidate validation results

| Alpha | Epochs | Eligible | Accuracy | Macro-F1 | Forward recall | Left recall | Right recall | Fwd->L | Fwd->R | Forward false-turn rate | Longest forward false-turn streak |
|---:|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.75 | 12 | yes | 94.94% | 0.7944 | 97.03% | 73.33% | 77.42% | 2 | 15 | 2.972% | 7 |
| 0.50 | 24 | no | 96.84% | 0.8371 | 99.65% | 73.33% | 67.74% | 1 | 1 | 0.350% | 1 |
| 0.25 | 11 | no | 95.89% | 0.8083 | 98.95% | 80.00% | 54.84% | 2 | 4 | 1.049% | 4 |
| 0.00 | 22 | no | 96.05% | 0.8085 | 99.48% | 70.00% | 58.06% | 1 | 2 | 0.524% | 2 |

The pre-fixed eligibility rule required both left and right recall >=70%. Therefore alpha 0.75 was the only eligible candidate and was selected.

## Consequence

The selected alpha 0.75 candidate reproduces the v4 configuration:

- same alpha: 0.75
- same epoch count: 12
- same validation metrics
- same recovery_04 reference metrics

Therefore the Step 5D run is a valid negative result: the pre-fixed selection rule does not identify a new model that should replace v4.

Running another full live shadow traversal of the selected v5 artifact would add little information because the selected configuration has already failed the v4 fresh live-shadow gate.

## Most informative rejected candidate

Alpha 0.50 is the strongest diagnostic alternative:

- validation accuracy: 96.84%
- macro-F1: 0.8371
- forward recall: 99.65%
- left recall: 73.33%
- right recall: 67.74%
- forward false turns: 2 / 572 = 0.35%
- longest forward false-turn streak: 1 frame

It misses the pre-fixed right-recall floor by 2.26 percentage points. On the 31-frame right-turn validation support, this is one correct right prediction short of crossing 70%.

Because this result was observed after the pre-fixed selection rule, alpha 0.50 must not be retroactively called the selected v5 model. It can, however, be evaluated transparently as a separate diagnostic shadow candidate because shadow mode remains human-controlled and non-actuating.

## Recommended next action

If the current Colab runtime is still alive, export the already-trained alpha 0.50 candidate from:

    /content/step05d_candidate_alpha_0.50.keras

to Google Drive as a clearly separate diagnostic artifact, for example:

    maze_navigation_model_alpha050_shadow.h5

Then run one fresh human-controlled live shadow traversal with that diagnostic candidate.

The purpose is narrow: test whether reducing class-weight strength materially reduces the live forward false-turn rate and longest false-turn streak without making real turns unusable.

Autonomous Step 6 remains blocked regardless of the offline alpha 0.50 result until a fresh live shadow run is reviewed.
