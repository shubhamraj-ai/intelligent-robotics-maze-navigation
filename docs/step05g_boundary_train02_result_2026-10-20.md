# Step 5G boundary_train_02 result — 2026-10-20

## Run status

The low-I/O `boundary_train_02` traversal completed successfully without a new CoppeliaSim crash.

The simulation was stopped cleanly after traversal completion so the collector could finalize the session.

## Collector summary

Session:
- boundary_train_02
- role: train

Metadata samples:
- total: 2,036
- stable-command: 1,051
- forward: 950
- left: 47
- right: 54

Boundary events:
- completed left events: 5
- completed right events: 5
- total completed events: 10
- discarded incomplete events: 3

Saved paired images:
- 100 total
- 50 pre-turn forward images
- 50 post-onset turn images
  - 25 left
  - 25 right
- 10 images per completed event
- all 100 referenced image files exist

No CNN inference was used.
No OpenCV GUI display was used.
Continuous JPEG writing was disabled.

## Integrity checks

- boundary_samples.csv contains exactly 100 rows
- all 10 event IDs contain exactly 10 rows
- all referenced image files exist
- no new CoppeliaSim Application Error / Windows Error Reporting crash event occurred during this traversal

## Event onsets

1. left — frame 761 — t=108.391 s — pose approximately (1.745, -2.117, yaw 0.012)
2. left — frame 823 — t=117.094 s — pose approximately (2.008, -1.064, yaw 1.408)
3. right — frame 1049 — t=146.500 s — pose approximately (-1.930, -0.873, yaw -3.130)
4. right — frame 1103 — t=154.141 s — pose approximately (-1.961, -0.008, yaw 1.538)
5. left — frame 1292 — t=178.547 s — pose approximately (1.854, 0.045, yaw -0.122)
6. left — frame 1329 — t=183.328 s — pose approximately (2.058, 0.464, yaw 1.242)
7. left — frame 1362 — t=187.985 s — pose approximately (1.884, 1.008, yaw 1.968)
8. right — frame 1520 — t=208.141 s — pose approximately (-1.559, 0.834, yaw -3.080)
9. right — frame 1558 — t=212.891 s — pose approximately (-1.972, 1.227, yaw 2.303)
10. right — frame 1605 — t=218.453 s — pose approximately (-2.056, 1.975, yaw 1.645)

Some nearby same-turn events reflect separate human forward->turn command edges during correction/turn completion. They remain valid paired boundary observations, but the later dataset builder should avoid unintentionally overweighting one physical turn; selection/weighting should be fixed before model training.

## Gate

`boundary_train_02`: PASS for Step 5G training-candidate use.

Training-side collection is now complete:
- boundary_train_01 — PASS
- boundary_train_02 — PASS

Next:
1. collect `boundary_validation_01` with the same low-I/O collector;
2. keep it completely isolated from training;
3. run integrity checks;
4. only then build the paired-boundary training/validation package.

Autonomous Step 6 remains blocked.
