# Step 6 consolidated evidence checkpoint — 2026-10-21

## Purpose

This checkpoint freezes the current Step 6 evidence while awaiting clarification from the course professor. It is an internal project record, not a claim that Step 6 is complete.

No further model retraining, live shadow runs, autonomous runs, or new driving-data collection should be started until the professor's guidance is reviewed against this evidence.

## Current project position

- Steps 1–5: completed and previously validated.
- Step 6 integration code: implemented and exercised.
- Autonomous Step 6: not yet accepted because closed-loop navigation is unstable near turn onset.
- Step 7: intentionally not started to avoid introducing a second interacting subsystem before navigation is stable.

Current branch:
- step-05c-session-aware-retraining

Current Step 6 PR:
- PR #13 remains OPEN and DRAFT.
- Do not merge until the Step 6 direction is resolved and validated.

## What the evidence now says

The problem is not simply that the CNN cannot recognise turns.

The v7 session-aware validation result on recovery_02 was strong:
- accuracy: 96.37%
- forward recall: 98.43%
- left recall: 83.33%
- right recall: 70.97%

The independent paired boundary holdout exposed the actual failure:
- pre-turn forward accuracy: 26%
- pre-turn false-left: 20%
- pre-turn false-right: 54%
- post-turn aggregate accuracy: 80%
- left recall: 80%
- right recall: 80%
- event-majority pass: 2/10 = 20%

Interpretation:
- once the robot is clearly in a turn state, the CNN can often recognise the turn;
- immediately before the human initiates the turn, the CNN frequently predicts a turn too early;
- this premature turn decision is the failure most relevant to autonomous closed-loop navigation.

## Sequence of Step 6 diagnostic work

### v3 autonomous attempts

Three autonomous attempts failed around the same broad turn region. Raw predictions oscillated and controller commitment heuristics did not solve the problem. One turn-commitment controller amplified erroneous turn decisions.

Conclusion:
- do not continue tuning v3 controller heuristics.

### Dataset leakage diagnosis

The original Step 5 dataset consisted of sequential frames sampled at roughly 0.10 s intervals from only three sessions.

Frame-level random train/validation/test splitting placed temporally adjacent near-duplicate frames across partitions.

A simulation of the same random-frame strategy showed that approximately 94% of test frames could have a same-class training frame within 0.5 s.

Conclusion:
- the original high held-out score was not a strong independent estimate of closed-loop generalisation.

### v4 session-aware recovery retraining

Whole-session splits replaced random frame splitting.

Offline v4 improved substantially over v3 on a held-out recovery session, but fresh live shadow still showed unacceptable forward false-turn behaviour.

Conclusion:
- session-aware evaluation was necessary but did not by itself solve turn timing.

### Step 5D alpha calibration / alpha 0.50

Alpha 0.50 materially improved aggregate live-shadow performance compared with v4, but a sustained high-confidence forward->right block remained.

Conclusion:
- class weighting improved the trade-off but did not solve the underlying boundary problem.

### Step 5E / Step 5F targeted forward hard negatives

Clean false-right states were captured and used as targeted forward examples.

v6 reduced some forward->right errors on a repeat reference but degraded legitimate turn recall on independent validation.

Conclusion:
- forward-only hard negatives moved the decision boundary in the desired direction for some states but suppressed valid turns.

### Step 5G paired boundary collection

A low-I/O collector was created to capture both sides of turn onset:
- five stable forward frames immediately before turn onset;
- five true-turn frames immediately after onset.

Training:
- boundary_train_01: 8 events / 80 images
- boundary_train_02: 10 events / 100 images

Held-out boundary validation:
- boundary_validation_01: 10 events / 100 images

### Step 5H paired-boundary v7

v7 improved legitimate turn-state recognition but did not improve pre-turn forward discrimination.

Frozen offline gate:
- recovery forward recall: PASS
- recovery left recall: PASS
- recovery right recall: PASS
- boundary pre-turn forward accuracy: FAIL
- boundary left recall: PASS
- boundary right recall: PASS
- boundary event pass rate: FAIL

Overall:
- OFFLINE GATE FAIL
- v7 is not eligible for live shadow.

## Observability finding

A pixel-level audit compared the exact W->A/D command boundary with ordinary adjacent forward frames.

On boundary_validation_01:
- mean RGB difference at the human command boundary: 0.00721
- mean RGB difference between ordinary adjacent pre-turn forward frames: 0.00718

These are essentially the same magnitude.

Working interpretation:
- the exact human keypress transition is not represented by a uniquely observable single-frame visual discontinuity;
- near-identical camera images can receive different labels because the human command changed between them;
- the static single-frame CNN is therefore being asked to learn a partly human-timing boundary rather than a purely visual boundary.

This is now the main technical question for Step 6.

## Professor clarification requested

The professor has been asked whether Step 6 should:
1. use each individual camera-frame prediction directly; or
2. allow visually defined turn regions instead of exact W/A/D transition labels; and/or
3. allow prediction smoothing or temporal confirmation.

Until that guidance is received, the project should not commit to another Step 6 architecture.

## Current hold rules

Do not:
- train v8/v9 under the same exact-keypress labeling rule;
- collect more driving data using the same labeling rule;
- run v7 live shadow;
- run autonomous Step 6;
- merge PR #13;
- start Step 7 implementation.

Safe work while waiting:
- documentation and evidence consolidation;
- report-ready technical notes;
- preparation of alternative implementation plans without executing them;
- simulator-crash documentation and operational safeguards.
