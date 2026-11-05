# Step 6 accelerated forward-only qualification after 128-pulse corner approach — 2026-11-05

## 128-pulse result

The geometry-informed first-turn gate completed 128 bounded decisions.

All 128 predictions remained `forward`.

The robot started at approximately:
- x = -1.971499
- y = -2.074754
- yaw = -0.002616 rad

The final pose was approximately:
- x = 1.6833
- y = -2.0150
- yaw = 0.0230 rad

The robot therefore reached and passed the first internal-wall endpoint near x = 1.475 while remaining safely inside the corridor and well before the right outer wall.

The classifier responded strongly to the corner region:
- pulse 121: left ~= 0.0577
- pulse 124: left ~= 0.1277
- pulse 126: left ~= 0.1525
- pulse 127: left ~= 0.1905
- pulse 128: left ~= 0.2736

Forward remained the argmax at pulse 128.

## AirGPU-time optimisation

Do not change the validated wheel-speed profile:
- forward = 1.00 / 1.00
- left = 0.10 / 1.00
- right = 1.00 / 0.10

Instead, qualification may use a longer pulse duration for forward only:

- forward pulse = 0.50 s
- left/right pulse = 0.25 s

Both remain within the existing hard qualification maximum of 0.50 s.

This reduces the number of fresh camera decisions needed to reach the first-corner region while preserving:
- the validated wheel velocities;
- the validated turn duration;
- stop-between-frame behavior;
- the same model and camera path.

This is a test-harness acceleration only. It is not a change to the final navigation policy.

## Validation

Targeted pulse tests:
- 5 / 5 PASS

Complete repository suite:
- 64 / 64 PASS

## Next gate

Use:
- forward pulse = 0.50 s
- turn pulse = 0.25 s
- maximum fresh-frame decisions = 68
- stop immediately after first left/right prediction

This should cross the first-corner region more quickly while preserving a meaningful safety margin before the right outer wall if no turn is detected.
