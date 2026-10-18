# Step 5G — Paired turn-boundary collection

Purpose: collect both sides of each human turn-onset boundary without changing the CNN architecture or class-weight settings.

Pre-committed session roles:
- boundary_train_01 — training candidate
- boundary_train_02 — training candidate
- boundary_validation_01 — held-out boundary validation

The collector records every camera frame, stable W/A/D command, and robot pose. It performs no CNN inference and does not use an OpenCV GUI window. After the run, it identifies forward→left and forward→right command onsets and records five stable forward frames immediately before each onset plus five stable true-turn frames immediately after each onset.

The full chronological session is retained so selection can be audited later. The validation session must not be added to training.

Autonomous Step 6 remains blocked during this stage.
