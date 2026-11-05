# Step 6 bounded turn-continuation PASS — 2026-11-05

## Result

The bounded turn-continuation qualification passed.

Configuration:
- camera: unchanged persistent Step-4 Lua save-only path;
- model: final simple perceptron;
- wheel speeds: locked 1.00 / 0.10 / 1.00;
- forward pulse: 0.50 s;
- left/right pulse: 0.50 s;
- motors stopped after every pulse;
- maximum total decisions: 80;
- maximum additional fresh decisions after first turn: 6;
- no confidence threshold, smoothing, route logic, pose steering, or CNN.

The first live turn was detected again at pulse 72.

Camera-driven turn sequence:
- pulse 72: left=0.423972, yaw=0.1374 rad
- pulse 73: left=0.759672, yaw=0.2934 rad
- pulse 74: left=0.917449, yaw=0.4294 rad
- pulse 75: left=0.946694, yaw=0.5706 rad
- pulse 76: left=0.979665, yaw=0.7165 rad
- pulse 77: left=0.991769, yaw=0.8623 rad
- pulse 78: left=0.990149, yaw=1.0182 rad

All seven turn decisions used the locked left command (0.10, 1.00), duration 0.50 s, and stopped both motors afterward.

Human visual observation independently confirmed that the robot visibly progressed through the left turn before the bounded gate stopped.

## Interpretation

This closes the bounded turn-continuation gate as PASS.

The robot achieved approximately 58 degrees of camera-driven left rotation by pulse 78. The behavior was stable and increasingly confident, but the approximately 90-degree first corner was not yet fully completed.

## Next gate

Run a bounded first-corner completion qualification:
- keep forward pulse at 0.50 s;
- keep left/right pulse at 0.50 s;
- retain locked wheel speeds;
- allow up to 10 additional fresh decisions after first turn;
- cap the total batch conservatively;
- preserve STOP after every pulse and visual supervision.

Do not introduce route logic, pose-driven control, confidence thresholds, smoothing, CNNs, or unrestricted continuous navigation.
