# Step 5G — Paired turn-boundary collection

Purpose: collect both sides of each human turn-onset boundary while keeping the model architecture and class-weight settings unchanged.

Pre-committed session roles:
- `boundary_train_01` — training candidate
- `boundary_train_02` — training candidate
- `boundary_validation_01` — held-out boundary validation

The held-out validation session must not be added to training.

## Low-I/O collector

After the first Step 5G attempt triggered another CoppeliaSim `0xc0000374` crash, the collector was changed to reduce runtime load. It no longer writes every camera frame to JPEG.

Instead it:
- keeps a small rolling camera buffer in RAM;
- logs lightweight metadata;
- detects a stable human-command `forward -> left/right` boundary;
- writes only five stable forward images immediately before onset and five true-turn images immediately after onset;
- performs no CNN inference;
- opens no OpenCV GUI window.

The first crashed `boundary_train_01` attempt is archived as diagnostic evidence and is excluded from training.

Autonomous Step 6 remains blocked during this stage.
