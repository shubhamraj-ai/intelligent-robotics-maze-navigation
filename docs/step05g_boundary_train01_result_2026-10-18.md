# Step 5G boundary_train_01 result — 2026-10-18

## Run status

The low-I/O `boundary_train_01` traversal completed successfully without a new CoppeliaSim crash.

The simulation was stopped cleanly after the user reported traversal completion so the collector could finalize its summary.

## Collector summary

Session:
- boundary_train_01
- role: train

Metadata samples:
- total: 3,771
- stable-command: 1,092
- forward: 983
- left: 56
- right: 53

Boundary events:
- completed left events: 4
- completed right events: 4
- total completed events: 8
- discarded incomplete events: 4

Saved paired images:
- 80 total
- 40 pre-turn forward images
- 40 post-onset turn images
  - 20 left
  - 20 right
- 10 images per completed event
- all 80 referenced image files exist

No CNN inference was used.
No OpenCV GUI display was used.
Continuous JPEG writing was disabled; images were written only after complete paired boundary events were confirmed.

## Event onsets

1. left — frame 2428 — t=304.328 s — pose approximately (1.949, -1.981, yaw -0.026)
2. left — frame 2487 — t=312.484 s — pose approximately (2.004, -1.031, yaw 1.571)
3. right — frame 2684 — t=337.172 s — pose approximately (-1.968, -0.722, yaw 3.051)
4. right — frame 2734 — t=343.578 s — pose approximately (-2.072, -0.056, yaw 1.655)
5. left — frame 2951 — t=369.813 s — pose approximately (1.938, -0.070, yaw 0.183)
6. left — frame 3027 — t=379.422 s — pose approximately (2.108, 0.916, yaw 1.565)
7. right — frame 3239 — t=405.469 s — pose approximately (-1.963, 1.232, yaw 2.990)
8. right — frame 3293 — t=412.219 s — pose approximately (-2.046, 1.980, yaw 1.630)

These are spatially distinct boundary states and are therefore retained as separate physical route events rather than deduplicated.

## Gate

`boundary_train_01`: PASS for Step 5G training-candidate use.

Next:
1. collect `boundary_train_02` with the same low-I/O collector;
2. collect `boundary_validation_01` with the same collector;
3. keep validation isolated from training;
4. do not begin the next model training until all three sessions pass integrity checks.

Autonomous Step 6 remains blocked.
