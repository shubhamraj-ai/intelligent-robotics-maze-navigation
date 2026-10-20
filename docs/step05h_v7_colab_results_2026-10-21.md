# Step 5H v7 Colab results — 2026-10-21

## Artifact set

Google Drive produced:
- maze_navigation_model_v7.h5 — 1,119,800 bytes
- step05h_v7_metrics.json
- step05h_v7_reference_confusion.csv
- step05h_v7_boundary_validation_confusion.csv
- step05h_v7_boundary_event_metrics.csv
- step05h_v7_history.csv

Training method:
- session-aware paired turn-boundary retraining
- seed 42
- image size 50x50 RGB
- class-weight alpha 0.50
- train images 3,841
- recovery_02 validation images 633
- recovery_04 repeat-reference images 665
- boundary_validation_01 images 100
- epochs completed 24

## recovery_02 training-time validation

- accuracy: 96.3665%
- macro-F1: 0.8424
- forward recall: 98.4266%
- left recall: 83.3333%
- right recall: 70.9677%
- forward->left: 2 / 572
- forward->right: 7 / 572

All three recovery_02 recall floors pass:
- forward >=95%: PASS
- left >=70%: PASS
- right >=70%: PASS

## recovery_04 repeat reference

- accuracy: 93.8346%
- macro-F1: 0.7992
- forward recall: 94.5092%
- left recall: 86.6667%
- right recall: 88.2353%
- forward->left: 22 / 601
- forward->right: 11 / 601

Confusion:
- forward [568, 22, 11]
- left [2, 26, 2]
- right [2, 2, 30]

## boundary_validation_01 independent boundary evaluation

Overall:
- accuracy: 53%
- macro-F1: 0.5467
- forward recall: 26%
- left recall: 80%
- right recall: 80%
- post-turn accuracy: 80%

Pre-turn forward behavior:
- correct forward: 13 / 50 = 26%
- false-left: 10 / 50 = 20%
- false-right: 27 / 50 = 54%

Boundary confusion:
- forward [13, 10, 27]
- left [2, 16, 2]
- right [6, 0, 24]

Event-majority rule:
- events passed: 2 / 10 = 20%
- required: >=60%

Per-event results:
1. left: pre 5/5, post 3/5 — PASS
2. left: pre 1/5, post 5/5 — FAIL
3. right: pre 0/5, post 5/5 — FAIL
4. right: pre 0/5, post 3/5 — FAIL
5. right: pre 0/5, post 5/5 — FAIL
6. left: pre 4/5, post 4/5 — PASS
7. left: pre 0/5, post 4/5 — FAIL
8. right: pre 3/5, post 1/5 — FAIL
9. right: pre 0/5, post 5/5 — FAIL
10. right: pre 0/5, post 5/5 — FAIL

## Direct comparison with frozen alpha-0.50 boundary comparator

| Metric | alpha-0.50 comparator | v7 | change |
|---|---:|---:|---:|
| pre-turn forward accuracy | 34% | 26% | -8 pp |
| pre-turn false-left | 14% | 20% | +6 pp |
| pre-turn false-right | 52% | 54% | +2 pp |
| post-turn aggregate accuracy | 74% | 80% | +6 pp |
| left recall | 65% | 80% | +15 pp |
| right recall | 80% | 80% | 0 pp |
| event-majority pass | 10% | 20% | +10 pp |

Paired boundary training improved legitimate turn recognition but did not solve premature turn prediction. It made pre-turn forward recognition worse.

## Frozen offline gate result

- recovery forward recall >=95%: PASS
- recovery left recall >=70%: PASS
- recovery right recall >=70%: PASS
- boundary pre-turn forward accuracy >=70%: FAIL (26%)
- boundary left recall >=70%: PASS
- boundary right recall >=70%: PASS
- boundary event-majority pass >=60%: FAIL (20%)

Overall:
- OFFLINE GATE: FAIL

v7 is NOT eligible for live shadow.
Autonomous Step 6 remains blocked.

## Observability audit of the human-command boundary

A pixel-level audit was run after the frozen v7 gate result.

Mean absolute RGB-frame difference between the last pre-turn frame and first post-turn frame:
- boundary_train_01: 0.00977
- boundary_train_02: 0.00772
- boundary_validation_01: 0.00721

Mean absolute difference between ordinary adjacent PRE-turn frames:
- boundary_train_01: 0.00795
- boundary_train_02: 0.00595
- boundary_validation_01: 0.00718

On the held-out validation session, the visual change exactly at human key-command onset (0.00721) is essentially the same magnitude as ordinary adjacent forward-frame change (0.00718).

This is strong evidence that the exact W->A/D keypress boundary is not represented by a distinct single-frame visual discontinuity. The current static single-frame 3-class CNN is being asked to separate near-identical images according to an action-timing boundary that is partly human-command timing rather than a uniquely observable visual state.

## Decision

Do not:
- run v7 live shadow;
- run autonomous Step 6;
- lower alpha again;
- add more paired pre/post samples under the same exact-keypress labeling rule;
- add controller heuristics merely to conceal the offline boundary failure.

Recommended next stage:
- Step 5I should address target-label observability/consistency rather than class weighting.
- Preserve the 50x50 CNN path as far as practical for assignment alignment.
- Define a visually/physically consistent turn-decision target rather than treating the exact human keypress instant as a uniquely classifiable image state.
- Fix the new labeling/evaluation rule before producing another model.
