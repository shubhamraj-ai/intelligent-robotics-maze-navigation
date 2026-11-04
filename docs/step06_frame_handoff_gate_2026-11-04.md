# Step 6 exact Step-4 capture-reuse gate — 2026-11-04

## Purpose

This checkpoint defines the first live Step-6 path while preserving the exact
camera architecture that finally worked in Step 4.

No AirGPU/CoppeliaSim live run was performed in this checkpoint.

## Final capture decision

The active Step-6 branch will NOT install a new camera writer for the first
live qualification.

Instead it reuses the already validated Step-4 persistent scene-owned script:

`src/step04_data_recording/persistent_camera_save_only.lua`

That script is part of the tagged stable Step-4 line:

`step4-stable-capture-2026-11-03`

The stable script keeps:

- persistent scene-owned Lua;
- camera handle `/PioneerP3DX/cam1`;
- `sim.getVisionSensorImg` inside Lua;
- `sim.saveImage` inside Lua;
- minimum stable signal duration: 0.75 s;
- save interval: 2.00 s;
- no Python camera-byte transfer;
- no simIM;
- no motor writes inside the camera script.

A temporary Step-6-specific Lua writer was developed during local design but
was removed from the active branch before any live run because reusing the exact
proven Step-4 script is the stricter preservation choice.

## Capture enable bridge

The stable Step-4 Lua script only saves while the small string signal
`step4_capture_label` contains a known label.

For Step 6, `capture_bridge.py` publishes the value `forward` strictly as a
capture-enable token.

This does NOT mean the Step-6 observation frame is a ground-truth forward
training example.

Runtime Step-6 frames must never be re-finalized into the Step-5 training
dataset merely because their filenames begin with `forward_`.

The bridge:

- writes only the already-proven small string signal;
- does not resolve the camera;
- does not read camera bytes;
- does not access motor handles;
- does not start/stop the simulation.

## File watcher

`frame_source.py` watches the existing stable-capture filenames:

`forward_*.jpg`

It:

- snapshots and ignores pre-existing files at startup;
- treats a changed file version as new using name/mtime/size;
- retries reads if a JPEG is temporarily incomplete;
- never deletes captured evidence;
- has no CoppeliaSim API.

## Live observation-only wrapper

`observe_existing_step4_capture.py` is the required first AirGPU Step-6 gate.

It may connect to CoppeliaSim only to:

- verify the simulation is running;
- set/clear the proven `step4_capture_label` string signal.

It never resolves:

- left motor;
- right motor;
- camera.

It never calls:

- `setJointTargetVelocity`;
- `getVisionSensorImg`;
- `startSimulation`;
- `stopSimulation`;
- `setStepping`.

It loads the final simple-perceptron H5, reads only new JPEG files saved by the
existing Step-4 Lua script, and prints predictions plus the wheel command that
would be used.

## Autonomous adapter

`autonomous_navigation.py` exists for the later actuation gate but has not
been run.

It:

- uses the same existing Step-4 capture signal/script;
- never touches the camera;
- does not start/stop the simulation;
- does not enable stepping;
- resolves only left/right motor handles;
- uses argmax directly from the final simple perceptron;
- maps labels to the locked 1.00 / 0.10 / 1.00 curved-turn motion profile;
- suppresses duplicate motor writes;
- stops motors and clears the capture signal on exit.

There is no:

- CNN;
- TensorFlow runtime;
- confidence threshold;
- temporal smoothing;
- turn commitment timer;
- route-specific logic;
- ultrasonic / Step-7 logic.

## Model and motion validation

The final H5/JSON artifacts were independently copied from Drive to Lenovo and
verified by SHA-256.

H5:

`a2ffb9258ef3527b7deadf6d4c5d137b356d573ecfec621c207f84997d976751`

JSON:

`7a3d0fb11edcd63bba5f9301524016a9a0e79bf1fdf846a64d1fe139ab4f47e1`

The active Step-6 core rejects any drift from:

- forward speed = 1.00
- turn outer speed = 1.00
- turn inner speed = 0.10
- control interval = 0.05 s

## Local validation

Final targeted capture-handoff tests:

- 9 / 9 PASS

Complete repository suite after exact Step-4 reuse revision:

- 58 / 58 PASS

The full suite includes the historical/stable tests proving the Step-4 Python
path does not access the camera.

## Decoupled monitor integration smoke

Using the real final H5 and the exact stable-capture filename pattern:

`forward_000001.jpg`

Result:

- monitor exit: 0
- no CoppeliaSim connection opened
- no motor capability
- prediction: forward
- probabilities:
  - forward=0.986107
  - left=0.009684
  - right=0.004210
- would-command: left=1.00, right=1.00

## Final H5 full-training-set sanity check

All 385 official Step-4 images were evaluated through the exported H5.

Confusion matrix
(rows=true forward/left/right; cols=predicted forward/left/right):

```text
[[312,  0,  1],
 [  9, 27,  0],
 [ 13,  0, 23]]
```

Training-set accuracy:

- 0.9402597403

Recall:

- forward: 0.9968051118
- left: 0.7500000000
- right: 0.6388888889

This is only a full-training-set sanity check. The Step-5 leave-one-session-out
cross-validation remains the authoritative generalization evidence.

## Next gate

AirGPU remains OFF.

The next live experiment is observation-only:

1. use the same stable maze/robot/camera scene that contains the validated
   persistent Step-4 Lua capture script;
2. do not alter the motion profile;
3. start the simulation with the robot stationary;
4. run `observe_existing_step4_capture.py` for a small bounded number of frames;
5. verify JPEG creation remains stable;
6. verify predictions are produced;
7. clear the capture signal and stop/review.

No autonomous motor actuation should occur until that gate passes.
