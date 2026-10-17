# Step 5C — Session-aware v4 retraining

This notebook is the replacement training path after the failed closed-loop v3 autonomous attempts.

## Fixed split

Whole sessions are isolated:

- Train: original_01, original_02, original_03, recovery_01, recovery_03
- Validation: recovery_02
- Test: recovery_04

No session is divided across train, validation, and test.

## Dataset package

Build locally with:

    python tools/build_step05c_session_dataset.py --original-dataset "F:\Shubham Raj\GitHub\intelligent-robotics-maze-navigation\dataset" --recovery-root "F:\Shubham Raj\GitHub\intelligent-robotics-maze-navigation-worktrees\step-05c-session-aware-retraining\recovery_sessions" --output-dir "F:\Shubham Raj\GitHub\intelligent-robotics-maze-navigation-worktrees\step-05c-session-aware-retraining\training_packages"

Expected package:

    step05c_session_dataset_v1.zip

Current package SHA256:

    1241b54cd3f6936c88e3fd659c729c69389df4ae67c11141cc9829757f164148

Expected counts:

- Train: 3,661 images — forward 3,290, left 185, right 186
- Validation: 633 images — forward 572, left 30, right 31
- Test: 665 images — forward 601, left 30, right 34
- Total: 4,959 images

## Colab

Upload the ZIP to:

    /content/drive/MyDrive/Intelligent_Robotics_Design_Project/

Then run:

    notebooks/step05c_session_aware_v4_training.ipynb

The notebook keeps the existing 50x50 three-class CNN architecture and fixes class-weight alpha at 0.75. It saves a new model as:

    maze_navigation_model_v4.h5

The v4 model must pass a new human-controlled shadow validation before another autonomous Step-6 attempt.
