# Step 5G boundary validation result and Step 5H v7 plan — 2026-10-21

## boundary_validation_01 run status

The fresh low-I/O held-out boundary-validation traversal completed successfully.

Session:
- boundary_validation_01
- role: validation

Collector summary:
- metadata samples: 2,114
- stable-command samples: 866
- forward samples: 778
- left samples: 47
- right samples: 41
- completed left-boundary events: 4
- completed right-boundary events: 6
- total completed events: 10
- discarded incomplete events: 1
- saved paired images: 100
- boundary frames per side: 5

Integrity:
- exactly 100 boundary sample rows
- exactly 10 event IDs
- exactly 10 rows per event
- all referenced image files exist
- class labels: forward 50, left 20, right 30
- boundary sides: 50 pre-forward, 50 post-turn
- no new CoppeliaSim crash event occurred during the completed traversal

This session remains isolated from training and early stopping.

## Frozen alpha-0.50 comparator on the boundary holdout

The paired-boundary training design was fixed before inspecting model performance on this held-out session.

The existing alpha-0.50 model was then evaluated on boundary_validation_01 to establish a frozen comparator.

Confusion matrix, rows = human label and columns = model prediction:

| Human \ prediction | forward | left | right |
|---|---:|---:|---:|
| forward | 17 | 7 | 26 |
| left | 4 | 13 | 3 |
| right | 6 | 0 | 24 |

Boundary comparator:
- pre-turn forward accuracy: 17/50 = 34%
- pre-turn false-left: 7/50 = 14%
- pre-turn false-right: 26/50 = 52%
- post-turn aggregate accuracy: 74%
- left recall: 65%
- right recall: 80%
- event majority pass rule: 1/10 = 10%

Event majority pass means:
- at least 3/5 pre-turn frames predicted forward; AND
- at least 3/5 post-turn frames predicted the correct turn.

This directly confirms the boundary-timing defect: the alpha-0.50 model often predicts a turn too early immediately before the human actually initiates the turn.

## Step 5H paired-boundary v7 package

Controlled experiment:
- start from step05c_session_dataset_v1.zip;
- do not include the Step 5F forward-only hard-negative session;
- add paired boundary_train_01 and boundary_train_02 samples to training;
- keep recovery_02 as training-time validation;
- keep recovery_04 as the repeat reference;
- package boundary_validation_01 separately for post-training evaluation only.

Paired training additions:
- boundary_train_01: 80 images
- boundary_train_02: 100 images
- total: 180 images
- forward: 90
- left: 45
- right: 45

Main split after additions:
- train: 3,841 = forward 3,380, left 230, right 231
- validation: 633 = forward 572, left 30, right 31
- repeat reference: 665 = forward 601, left 30, right 34

Boundary holdout:
- 100 images
- forward 50
- left 20
- right 30
- 10 events
- never passed to model.fit()
- never used by early stopping

Generated package:
- training_packages/step05h_paired_boundary_dataset_v1.zip
- SHA256: 8e822142fd20cad4ee2d4e28f4d93f117a70756dbd477a0395f2bcee63aea148

Notebook:
- notebooks/step05h_paired_boundary_v7_training.ipynb

Expected model:
- maze_navigation_model_v7.h5

## Pre-committed offline promotion gate

Fixed before v7 training:
- recovery_02 forward recall >= 95%
- recovery_02 left recall >= 70%
- recovery_02 right recall >= 70%
- boundary holdout pre-turn forward accuracy >= 70%
- boundary holdout post-turn left recall >= 70%
- boundary holdout post-turn right recall >= 70%
- boundary event majority pass rate >= 60%

Passing this gate permits a fresh human-controlled no-display live shadow traversal only.

It does not permit autonomous motor control.

Autonomous Step 6 remains blocked until fresh sequential live-shadow evidence is satisfactory.
