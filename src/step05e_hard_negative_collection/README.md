# Step 5E — Targeted hard-negative collection

This collector follows the alpha-0.50 fresh live-shadow run, which materially improved aggregate false-turn behavior but still produced a sustained high-confidence forward->right block.

The human remains in full control of the PioneerP3DX. The alpha-0.50 model is shadow-only. The OpenCV GUI is intentionally not used because the earlier CoppeliaSim crash remains intermittent and the no-display shadow traversal was stable.

The collector saves every nonblank live camera frame, the stable human W/A/D label when available, model probabilities/confidence, robot x/y/yaw, and explicit forward->right markers. Retaining the full chronological stream preserves the frames immediately before and after every false-right event.

Outputs are written under `hard_negative_sessions/hardneg_<timestamp>/` and are ignored by Git.

Do not use a session for retraining until its metadata and false-right events have been reviewed. Do not enable autonomous motor control during this collection stage.
