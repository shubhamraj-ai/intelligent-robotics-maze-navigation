# Step 6 scene-owned frame-handoff gate — 2026-11-04

## Purpose

This checkpoint extends the active simple-perceptron Step-6 path while preserving the stable Step-4 camera isolation boundary.

No AirGPU/CoppeliaSim live run was performed in this checkpoint.

## Camera transport

New scene-owned Lua writer:

`src/step06_simple_perceptron_navigation/step06_scene_frame_writer.lua`

It preserves the proven Step-4 architecture:

- persistent scene-owned Lua;
- Lua resolves `/PioneerP3DX/cam1`;
- Lua calls `sim.getVisionSensorImg`;
- Lua calls `sim.saveImage`;
- Python receives no image buffers from CoppeliaSim;
- Python does not call camera APIs.

Initial qualification constants are deliberately conservative and match the stable Step-4 capture timing:

- startup/stability delay: 0.75 s
- JPEG save interval: 2.00 s

Do not reduce the save interval in the same experiment that introduces autonomous motor actuation.

## Python frame handoff

`frame_source.py` watches only completed `step6_frame_*.jpg` files.

The watcher:

- snapshots and ignores pre-existing files at startup;
- treats a changed file version as new by name/mtime/size signature;
- retries JPEG reads if a file is temporarily incomplete;
- never deletes captured evidence;
- contains no simulator or motor API.

## Observation-only first live mode

`frame_handoff_monitor.py` is physically separated from the motor adapter.

It:

- loads the final H5/JSON contract;
- watches new scene-owned JPEGs;
- runs exact simple-perceptron NumPy inference;
- prints the wheel command that *would* be used;
- never imports RemoteAPIClient;
- cannot command motors.

This is the required first AirGPU qualification mode.

## Autonomous adapter

`autonomous_navigation.py` exists for the later actuation gate but has not been run.

It:

- never accesses the camera;
- does not start/stop the simulation;
- does not enable stepping;
- uses only left/right motor object handles;
- waits for a new scene-owned JPEG;
- applies argmax prediction directly to the locked motion profile;
- sends motor writes only when the velocity pair changes;
- stops both motors on exit.

It contains no confidence threshold, temporal smoothing, commitment timer, route-specific logic, ultrasonic logic, CNN, or TensorFlow runtime.

## Local validation

Targeted frame-handoff tests:

- 6 / 6 PASS

Complete repository test suite:

- 55 / 55 PASS

The full suite still includes and passes the Step-4 tests proving Python does not access the camera in the stable collection path.

## Observation-monitor integration smoke

The real final H5 was loaded.

A new official Step-4 JPEG was injected into the watcher *after* the monitor readiness marker.

Result:

- monitor exit: 0
- observation-only mode confirmed no simulator connection and no motor capability
- prediction: forward
- probabilities: forward=0.688168, left=0.298218, right=0.013613
- would-command: (1.00, 1.00)

The injected source image came from the left training folder. This single misclassification is consistent with the known imperfect turn recall and was investigated further below.

## Final H5 full-training-set sanity check

The exported final H5 was evaluated on all 385 official training images.

Confusion matrix (rows=true forward/left/right; cols=predicted forward/left/right):

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

This is only a full-training-set sanity check. The leave-one-session-out Step-5 cross-validation remains the authoritative generalization evidence.

The result confirms that the single observation-smoke error is not an H5/runtime corruption issue; the final model retains the previously documented turn-class limitations.

## Next gate

AirGPU is still OFF.

The next live experiment must be observation-only:

1. use the stable maze/robot/camera scene;
2. install/use the persistent Step-6 Lua frame writer without changing camera or motion parameters;
3. keep motors stationary;
4. run `frame_handoff_monitor.py` only;
5. verify multiple scene-owned JPEGs arrive without simulator instability;
6. verify model predictions/log output;
7. stop and review before any autonomous motor actuation.

Only after that observation-only gate passes should the autonomous adapter be considered.
