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


## Crash during first train-01 attempt

The first `boundary_train_01` attempt crashed CoppeliaSim at approximately 18:34:39 local time before the first turn was reached.

Windows recorded:
- application: coppeliaSim.exe
- module: ntdll.dll
- exception: 0xc0000374

The partial session contained 915 captured frames but only 131 stable forward-command frames and no turn boundary. It is archived as:
- boundary_train_01_crashed_20261018T183439

This partial session is excluded from training and validation.

Because the crash occurred with CNN inference OFF and OpenCV GUI display OFF, neither CNN inference nor the GUI display path is required to trigger the intermittent simulator failure.

Compared with the previously stable manual+raw-camera diagnostic, the main extra runtime load in the first Step 5G collector was continuous JPEG encoding/writing plus metadata/pose logging. Continuous JPEG writing is therefore an actionable remaining difference, but it is not proven to be the root cause.

## Low-I/O revision

The Step 5G collector now:
- keeps a small rolling camera buffer in memory;
- writes lightweight metadata only every sample;
- flushes metadata in batches;
- writes JPEGs only after a complete turn-boundary event is confirmed;
- saves exactly five stable forward frames before onset and five true-turn frames after onset;
- keeps CNN inference OFF;
- keeps OpenCV GUI display OFF.

A fresh `boundary_train_01` attempt should use only this low-I/O collector.
