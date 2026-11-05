# Step 6 first-turn bounded qualification readiness — 2026-11-06

## Purpose

Continue from the validated 12-pulse forward-progression gate without changing
the stable Step-4/Step-5/Step-6 baseline.

The next objective is to obtain the first genuine live left/right prediction and
verify the corresponding bounded curved motor actuation.

## Preserved baseline

Unchanged:

- persistent Step-4 scene-owned Lua camera-save path;
- final Step-5 simple perceptron;
- OpenCV/NumPy preprocessing;
- wheel speeds 1.00 / 0.10 / 1.00;
- 0.25 s bounded qualification pulse;
- full motor stop after every pulse;
- no CNN/TensorFlow runtime;
- no confidence threshold;
- no smoothing;
- no route-specific logic.

## New safety option

The bounded pulse qualification now supports:

`--stop-on-turn`

When enabled:

1. fresh frame is captured;
2. final perceptron predicts forward / left / right;
3. the locked wheel command is applied for the same 0.25 s pulse;
4. both motors are stopped;
5. if the prediction was left or right, the program prints
   `STEP6_FIRST_TURN_DETECTED` and exits cleanly.

The turn therefore receives one bounded curved pulse only. The program does not
continue deeper into the maze after the first turn decision.

## Validation

Targeted pulse qualification tests:

- 3 / 3 PASS

Complete repository suite:

- 62 / 62 PASS

## Next AirGPU gate

Use a bounded batch large enough to reach the first turn, but stop
automatically on the first left/right decision.

No unrestricted continuous autonomous run is authorized yet.
