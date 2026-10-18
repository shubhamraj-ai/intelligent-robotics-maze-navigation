# Step 5E clean hard-negative result and Step 5F v6 plan — 2026-10-18

## Clean Step 5E traversal

Session:
- hardneg_20261018T114532Z

Collector completed cleanly after a full human-controlled traversal.

Scored stable-command frames: 771
- forward: 703
- left: 34
- right: 34

Confusion matrix, rows = human and columns = alpha-0.50 shadow prediction:

| Human \ prediction | forward | left | right |
|---|---:|---:|---:|
| forward | 680 | 6 | 17 |
| left | 5 | 29 | 0 |
| right | 0 | 0 | 34 |

Derived clean-run metrics:
- agreement: 743 / 771 = 96.37%
- forward recall: 96.73%
- left recall: 85.29%
- right recall: 100.00%
- forward -> left: 6 / 703 = 0.85%
- forward -> right: 17 / 703 = 2.42%
- total forward false-turn rate: 23 / 703 = 3.27%

The run contained seven forward->right events. The longest was six frames at approximately 686.313-687.156 s. Distinct higher-confidence false-right states were observed near multiple route locations, including:
- around x=-1.92, y=-0.75, yaw≈3.13
- around x=-1.94, y=1.05, yaw≈3.13
- around x=-1.96, y=1.86, yaw≈1.51
- around x=1.93, y=1.83, yaw≈-0.05

These are useful hard negatives because the human command remained forward while the alpha-0.50 shadow model crossed into a right prediction.

The earlier interrupted/hung Step 5E session is retained for diagnosis but excluded from v6 training because control-state reliability during the laptop hang is uncertain.

## Step 5F targeted selection

Selection rule fixed before v6 training:
1. include all 17 clean stable human=forward/model=right frames;
2. include up to +/-3 chronological frame indices around each false-right frame when the context frame also has stable human=forward;
3. deduplicate overlaps.

Result:
- 17 false-right frames
- 23 forward-context frames
- 40 total added training images

All 40 selected images are labeled forward.

The selection is reproducible through:
- tools/build_step05f_hard_negative_dataset.py
- hard_negative_selection.csv inside the generated package

## Step 5F package

Package:
- training_packages/step05f_hard_negative_dataset_v1.zip

SHA256:
- 785895383612a0ea86b8c03a71a577764e89e1a2dcfde6e6f788d98b1f01a947

Split counts:
- train: 3,701 images = forward 3,330, left 185, right 186
- validation: 633 images = forward 572, left 30, right 31
- reference test: 665 images = forward 601, left 30, right 34

Train sessions:
- original_01
- original_02
- original_03
- recovery_01
- recovery_03
- hardneg_clean_20261018

Validation remains recovery_02.
Reference test remains recovery_04.

## v6 training experiment

Notebook:
- notebooks/step05f_hard_negative_v6_training.ipynb

Controlled change:
- targeted hard-negative training data only

Fixed:
- CNN architecture
- 50x50 RGB preprocessing
- optimizer
- random seed
- early stopping
- validation session
- reference-test session
- class-weight alpha = 0.50

Expected model output:
- maze_navigation_model_v6.h5

Autonomous Step 6 remains blocked. After v6 offline evaluation, a fresh no-display human-controlled shadow traversal is mandatory before autonomous control can be reconsidered.
