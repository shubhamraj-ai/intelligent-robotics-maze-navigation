# Step 6 first live turn PASS — 2026-11-05

## Result

The bounded live Step-6 first-turn qualification achieved the first genuine camera-driven turn.

Configuration:
- camera: unchanged persistent Step-4 Lua save-only path;
- model: final simple perceptron;
- wheel speeds: locked 1.00 / 0.10 / 1.00;
- forward pulse duration: 0.50 s;
- left/right pulse duration: 0.25 s;
- motors stopped after every pulse;
- no confidence threshold, smoothing, commitment timer, pose control or route logic.

At pulse 71:
- label: forward;
- forward probability: 0.521454;
- left probability: 0.377680;
- right probability: 0.100866;
- pose: approximately (1.7906, -2.0821, 0.1387);
- yaw: approximately -0.0011 rad.

At pulse 72:
- label changed to left;
- forward probability: 0.332662;
- left probability: 0.439240;
- right probability: 0.228098;
- command: (0.10, 1.00);
- duration: 0.25 s;
- motors stopped immediately afterward;
- resulting pose: approximately (1.8078, -2.0846, 0.1387);
- resulting yaw: approximately +0.0613 rad.

The program reported:
STEP6_FIRST_TURN_DETECTED pulse=72 label=left frame=forward_000072.jpg
FIRST LIVE TURN DETECTED: PASS

Human visual observation independently confirmed that the final movement was a brief left turn and looked correct.

## Interpretation

This closes the first-live-turn qualification milestone.

It demonstrates:
1. fresh scene-owned JPEG acquisition;
2. final simple-perceptron inference;
3. forward-to-left class transition from live camera imagery;
4. correct locked left wheel command mapping;
5. physical left rotation in CoppeliaSim;
6. immediate motor stop after the bounded turn pulse.

It does not yet prove a complete 90-degree corner traversal or full autonomous maze navigation.

## Next milestone

The next gate is bounded turn continuation:
- continue consuming fresh camera frames after the first left prediction;
- preserve camera-driven decisions only;
- preserve stop-between-frame behavior;
- allow multiple bounded left/forward/right decisions so the robot can negotiate the corner;
- remain visually supervised;
- stop before any unrestricted continuous-navigation run.

Do not replace the simple perceptron or introduce CNN, route-specific logic, pose-driven steering, temporal smoothing or confidence heuristics at this stage.
