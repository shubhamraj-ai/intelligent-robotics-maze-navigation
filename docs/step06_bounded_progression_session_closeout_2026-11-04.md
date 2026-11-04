# Step 6 bounded progression gate — session closeout 2026-11-04

## Session result

The AirGPU bounded autonomous-progression gate completed successfully after the runtime probe-frame namespace fix.

Stable scene:
`Maze_working_4_7_persistent_camera_save_only.ttt`

Active Step-6 source:
`77119179e1ac9362686fd9de47f699b3adda3cf1`

Architecture retained:
- existing persistent Step-4 Lua camera-save-only path;
- final Step-5 simple perceptron;
- locked wheel speeds 1.00 / 0.10 / 1.00;
- 0.25 s bounded motor pulse;
- full motor stop after every fresh-frame decision;
- no CNN, no TensorFlow runtime, no route-specific logic, no confidence threshold, no temporal smoothing.

## Runtime frame-lifecycle correction

The stable Lua capture script resets its filename counter to 000001 every time the simulation starts.

Earlier Step-6 probe JPEGs remained in:
`dataset_simplified/_persistent_save_probe`

Because the corrected watcher intentionally rejects filenames that existed at startup, a restarted simulation had to overwrite old names until it eventually reached a previously unused filename. With the stable 2.00 s save interval, this could exceed the 15 s watcher timeout.

The AirGPU live-gate PowerShell helpers were therefore changed to:
1. preserve all existing runtime probe JPEGs;
2. move them into the current run-evidence directory under `preexisting_probe_frames`;
3. start each live qualification with an empty active probe directory.

This changes only runtime evidence-file lifecycle. It does not alter:
- the official 385-image dataset;
- the stable Lua capture code;
- model preprocessing;
- motion mapping;
- model architecture.

## Bounded progression result

The corrected run archived 9 pre-existing probe JPEGs and then generated a fresh sequence:

`forward_000001.jpg` through `forward_000012.jpg`

All 12 distinct frames were classified as:
`forward`

All 12 commands were:
`(1.00, 1.00)`

Each command duration was:
`0.25 s`

Each pulse ended with:
`STOPPED`

Completion marker:
`STEP6_PULSE_ACTUATION_COMPLETE pulses=12`

Reported turn decisions:
`0`

The gate completed normally.

## Human visual observation

The operator visually confirmed:
- the robot moved forward in short bounded increments;
- the robot remained on track;
- the robot did not reach or collide with a wall;
- no unexpected turn occurred;
- the simulation was manually stopped after the completed gate.

## Interpretation

This is a PASS for:
- repeated fresh-frame acquisition;
- repeated final-H5 inference;
- repeated forward motor actuation;
- mandatory stop-between-frame behavior;
- CoppeliaSim stability during a longer bounded closed-loop progression.

This gate does NOT yet prove:
- live left-turn actuation;
- live right-turn actuation;
- first-corner handling;
- continuous autonomous navigation;
- complete maze traversal.

No continuous autonomous-navigation run is authorized yet.

## Next-session starting point

Resume from the stable Step-6 branch and preserved AirGPU setup.

The next experiment should remain bounded and should advance far enough to encounter the first meaningful turn while preserving:
- the same camera architecture;
- the same final simple perceptron;
- the same 1.00 / 0.10 / 1.00 speeds;
- the same stop-between-frame safety behavior.

Do not retune earlier Step-2/Step-4 baselines simply because the 12-pulse run produced only forward decisions. The robot had not yet reached a wall or demonstrated an incorrect decision.

The next-session objective is:
**obtain the first genuine live left/right decision and verify the corresponding bounded curved motor actuation before considering any continuous Step-6 run.**
