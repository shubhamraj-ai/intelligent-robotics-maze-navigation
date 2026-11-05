# Step 6 second-turn approach — detection PASS, traversal FAIL — 2026-11-05

## Live outcome

The bounded second-turn approach run did not qualify the second corner.

The helper reported a second live turn detection at pulse 92, but human visual observation confirmed that the robot did not complete the second left turn and collided with the wall before safe corner traversal was established.

Therefore:
- second-turn detection: PASS;
- second-corner traversal: FAIL;
- full autonomous navigation: NOT qualified.

## Relevant sequence

The first corner repeated successfully:
- pulse 72: forward -> left;
- pulses 72-81: sustained left;
- pulse 82: left -> forward.

The second-corner region was unstable:
- pulse 92: forward -> left;
- pulse 93: left -> forward;
- pulse 98: forward -> left;
- pulse 99: left;
- pulse 100: left -> forward;
- pulses 100-104: forward.

Representative poses/yaw:
- pulse 91: pose approximately (2.1122, -1.4023), yaw 1.4483 rad;
- pulse 92 left: pose approximately (2.1198, -1.3705), yaw 1.5776 rad;
- pulse 93 forward: yaw 1.5935 rad;
- pulse 98 left: yaw 1.7246 rad;
- pulse 99 left: yaw 1.8716 rad;
- pulse 100 forward: yaw 1.8883 rad;
- pulse 104 forward: pose approximately (2.0353, -0.7888), yaw 1.8902 rad.

The classifier therefore did not sustain the second turn. Unlike the first corner, the second-corner output flickered back to forward before enough rotation had accumulated.

## Interpretation

This is a concrete Step-6 live failure that justifies reopening Step-5 model-balance analysis while preserving:
- the same simple single-layer perceptron architecture;
- the validated Step-4 persistent Lua camera path;
- the validated wheel-speed mapping;
- the successful first-corner evidence.

Do not introduce CNNs, route-specific logic, pose-driven steering, temporal smoothing, or unrestricted navigation as a response.

The failure is most consistent with insufficient turn persistence from the current unweighted model in the second-corner visual regime.

## Existing Step-5 evidence

The current unweighted model was selected because it had:
- forward recall approximately 0.984;
- left recall approximately 0.722-0.750;
- right recall approximately 0.583-0.611;
- forward-to-turn false positives approximately 1.60%.

Full balanced weighting improved left/right recall to approximately 0.944/0.972 but reduced forward recall to approximately 0.863 and raised premature forward-to-turn errors to approximately 13.74%.

Therefore neither extreme should be adopted blindly.

## Next action

Run an offline partial class-weight sweep using the same:
- 385-image official dataset;
- leave-one-session-out cross-validation;
- single 2500->3 softmax perceptron;
- epochs=3200;
- learning_rate=0.01;
- l2=0.0001;
- seed=42.

Evaluate intermediate weighting between unweighted and fully balanced. Select candidates only if they improve turn recall materially while preserving a low forward-to-turn false-positive rate.

No live AirGPU test should resume until an offline candidate is objectively better than the current unweighted baseline.
