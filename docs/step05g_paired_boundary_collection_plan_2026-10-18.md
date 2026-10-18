# Step 5G paired turn-boundary collection plan — 2026-10-18

## Motivation

Step 5F v6 reduced some forward->right errors on the repeat recovery_04 reference but degraded legitimate turn recall, especially right recall, on the independent recovery_02 validation session.

This indicates a turn-onset boundary problem rather than a simple class-frequency problem. Forward-only hard negatives push the decision boundary away from premature turns, but also make the classifier less willing to recognize true turn states.

## Controlled next experiment

Keep fixed:
- CNN architecture
- 50x50 RGB preprocessing
- class-weight alpha 0.50
- optimizer / random seed / early-stopping policy

Change only the boundary data.

Pre-committed session roles:
- boundary_train_01 — training candidate
- boundary_train_02 — training candidate
- boundary_validation_01 — held-out boundary validation

The held-out boundary validation session must not be used for training.

## Collection protocol

Each session is one clean natural human-controlled traversal.

Collector:
- src/step05g_boundary_collection/record_boundary_session.py

During collection:
- human W/A/D commands control motors;
- CNN inference is OFF;
- OpenCV GUI display is OFF;
- every nonblank 50x50 RGB camera frame is saved;
- stable human command and robot x/y/yaw are logged.

After each session, forward->left and forward->right command onsets are detected from stable human labels.

A valid boundary event contributes:
- five stable forward frames immediately before onset;
- five stable true-turn frames immediately after onset.

Both left and right boundaries are retained.

## Why this is different from Step 5E

Step 5E selected forward-only hard negatives after observing model mistakes.

Step 5G selects matched human-command boundary states independently of model predictions. This prevents another one-sided shift that suppresses legitimate turn recognition.

## Gate

Do not train the next model until:
- boundary_train_01 completes cleanly;
- boundary_train_02 completes cleanly;
- boundary_validation_01 completes cleanly;
- each session contains usable left and right boundary events.

Do not run autonomous Step 6 during this stage.
