# Step 6 live observation gate 2 and bounded pulse-actuation readiness — 2026-11-04

## Observation gate 2 outcome

The corrected AirGPU observation-only gate completed successfully using the unchanged stable scene:

`Maze_working_4_7_persistent_camera_save_only.ttt`

The existing Step-4 persistent scene-owned Lua script remained the camera owner.

The corrected watcher consumed three distinct live JPEG filenames:

- `forward_000003.jpg`
- `forward_000004.jpg`
- `forward_000005.jpg`

All three frames were processed by the final simple perceptron.

Predictions:

1. `forward_000003.jpg`
   - forward = 0.986603
   - left = 0.009113
   - right = 0.004284
   - would-command = (1.00, 1.00)

2. `forward_000004.jpg`
   - forward = 0.986677
   - left = 0.009042
   - right = 0.004281
   - would-command = (1.00, 1.00)

3. `forward_000005.jpg`
   - forward = 0.986658
   - left = 0.009074
   - right = 0.004268
   - would-command = (1.00, 1.00)

The robot remained stationary because the observation program resolves no motor handles and sends no motor command.

The simulation remained stable and was stopped manually after completion.

## Observation gate 2 status

- simulator stability: PASS
- exact stable Step-4 camera architecture retained: PASS
- three distinct fresh frame filenames: PASS
- final H5 inference path: PASS
- no-motor safety: PASS

The duplicate-frame concern from gate 1 is therefore closed.

## Why continuous autonomous actuation is not the next immediate gate

The stable Step-4 camera-save interval is deliberately conservative:

- 2.00 s between JPEG saves.

The validated robot motion profile uses:

- forward = 1.00 / 1.00
- left = 0.10 / 1.00
- right = 1.00 / 0.10

Allowing the robot to continue moving at those wheel speeds for the entire interval between sparse 2-second observations would introduce a large new control variable immediately.

The first actuation gate therefore does not change the camera architecture, motion speeds, model architecture, or prediction logic.

Instead it bounds only the *duration* of each test actuation.

## Bounded pulse-actuation qualification

New module:

`src/step06_simple_perceptron_navigation/pulse_actuation_qualification.py`

For each fresh JPEG:

1. infer forward / left / right with the final simple perceptron;
2. map the label to the locked 1.00 / 0.10 / 1.00 wheel speeds;
3. apply that predicted wheel command for 0.25 s;
4. immediately command both motors to 0.0;
5. remain stopped while waiting for the next distinct fresh JPEG.

Safety limits:

- default pulse = 0.25 s
- hard qualification maximum = 0.50 s
- pulse values <= 0 or > 0.50 s are rejected
- camera remains scene-owned Lua
- no Python camera-byte transfer
- no simulation lifecycle control
- no stepping mode
- no TensorFlow/CNN
- no confidence threshold
- no temporal smoothing
- no turn-commitment timer
- no route-specific logic

This pulse is an engineering qualification mechanism, not the final Step-6 navigation policy.

## Validation

Pulse-specific tests:

- 2 / 2 PASS

Complete repository suite after adding pulse qualification:

- 61 / 61 PASS

All prior stable Step-2/Step-4 motion/camera tests and Step-5 final-submission tests remain passing.

## Next gate

The next AirGPU experiment is a bounded 3-pulse qualification.

Requirements:

1. use the unchanged stable Step-4 scene;
2. start the simulation manually;
3. run the dedicated pulse-qualification helper;
4. visually observe the robot;
5. allow exactly three fresh-frame decisions;
6. each decision may actuate for only 0.25 s;
7. motors must stop after every pulse;
8. stop the simulation and review evidence before any continuous autonomous run.

No continuous autonomous navigation is authorized yet.
