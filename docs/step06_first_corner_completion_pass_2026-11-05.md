# Step 6 first-corner completion PASS — 2026-11-05

## Result

The first-corner completion qualification passed.

Configuration:
- camera: unchanged persistent Step-4 Lua save-only path;
- model: final simple perceptron;
- wheel speeds: locked 1.00 / 0.10 / 1.00;
- forward pulse: 0.50 s;
- left/right pulse: 0.50 s;
- motors stopped after every pulse;
- no confidence threshold, smoothing, commitment timer, route logic, pose steering, or CNN.

## Camera-driven corner sequence

The first left decision occurred again at pulse 72.

Pulse sequence near the corner:
- pulse 72: left, yaw 0.1429 rad
- pulse 73: left, yaw 0.2795 rad
- pulse 74: left, yaw 0.4216 rad
- pulse 75: left, yaw 0.5678 rad
- pulse 76: left, yaw 0.7143 rad
- pulse 77: left, yaw 0.8607 rad
- pulse 78: left, yaw 1.0063 rad
- pulse 79: left, yaw 1.1518 rad
- pulse 80: left, yaw 1.2969 rad
- pulse 81: left, yaw 1.4528 rad
- pulse 82: forward, yaw 1.4570 rad

At pulse 82 the model naturally transitioned back to forward:
- forward = 0.520164
- left = 0.478663
- right = 0.001173
- command = (1.00, 1.00)
- pose approximately (2.0540, -1.8963, 0.1387)
- yaw approximately 1.4570 rad (~83.5 degrees)

Human observation confirmed that the robot completed the visible left-corner maneuver and then progressed into the new corridor.

## Interpretation

This closes the first-corner completion milestone as PASS.

It demonstrates a full camera-driven behavioral sequence:
1. approach the corner while predicting forward;
2. transition to left from live imagery;
3. sustain repeated left decisions through the turn;
4. physically rotate through approximately 83.5 degrees;
5. naturally transition back to forward without route-specific logic;
6. advance into the next corridor;
7. stop after every individual bounded pulse.

The result remains professor-aligned and uses only the final simple perceptron.

## Next milestone

The next milestone is a bounded second-corridor / second-turn approach qualification.

Do not jump directly to unrestricted continuous navigation.

Use the existing 0.50 s pulse durations and locked wheel speeds. Traverse the already-qualified first corner and continue only far enough into the second corridor to inspect the next turn transition with a conservative geometry-based stopping margin.

If the second turn is detected cleanly, then extend to a bounded second-turn continuation gate.
