# Step 6 simple-perceptron local gate — 2026-11-04

## Status

Step 5 is closed and the active Step-6 branch is:

`feature/step06-final-simple-perceptron-navigation`

This checkpoint validates the new Step-6 inference/motion core locally before any live CoppeliaSim actuation.

## Preserved Step-4 balance

The accepted motion profile is unchanged:

- forward: left=1.00, right=1.00
- curved left: left=0.10, right=1.00
- curved right: left=1.00, right=0.10
- control interval: 0.05 s

The Step-6 core fails fast if `config/motion_profile.json` drifts from those values.

Motor writes retain the Step-2/Step-4 state-change-only policy: duplicate velocity pairs are suppressed.

## Preserved Step-4 camera isolation boundary

The stable Step-4 capture tag is:

`step4-stable-capture-2026-11-03`

Its manifest/evidence establishes the successful architecture as scene-owned Lua camera acquisition/JPEG save with Python not receiving camera bytes.

The new Step-6 core therefore deliberately contains no:

- `getVisionSensorImg` call;
- camera object path;
- simIM call;
- Python-side CoppeliaSim image-buffer transfer.

Live frame transport is a separate future adapter and must preserve that isolation boundary.

## Final Step-5 model contract

Verified Colab artifacts copied to Lenovo outside Git:

- `maze_navigation_simple_perceptron_final.h5`
- `maze_navigation_simple_perceptron_final.json`

H5 SHA-256:

`a2ffb9258ef3527b7deadf6d4c5d137b356d573ecfec621c207f84997d976751`

JSON SHA-256:

`7a3d0fb11edcd63bba5f9301524016a9a0e79bf1fdf846a64d1fe139ab4f47e1`

The H5 contains exactly:

- kernel: `(2500, 3)`, float32
- bias: `(3,)`, float32
- one Dense layer with 3 softmax outputs

The active runtime uses h5py + NumPy only. TensorFlow is not required.

## Local implementation

`src/step06_simple_perceptron_navigation/core.py` implements:

- strict H5 contract validation;
- strict Step-5 metadata validation;
- exact OpenCV BGR2GRAY -> float32 /255 -> flatten-2500 preprocessing;
- numerically stable NumPy softmax;
- label order: forward / left / right;
- exact locked wheel mapping;
- state-change-only motor writes;
- best-effort motor stop.

`validate_artifact.py` is an offline acceptance harness. It opens no simulator connection and sends no motor commands.

## Validation

Targeted new Step-6 tests:

- 9 / 9 PASS

Complete repository test suite after the new implementation:

- 49 / 49 PASS

The full suite includes the preserved Step-2/Step-4 motion/camera tests and the final Step-5 submission tests.

Real-artifact smoke check using official Step-4 image:

`session_20261103_01/forward/forward_000001.jpg`

Result:

- prediction: forward
- forward probability: 0.986107
- left probability: 0.009684
- right probability: 0.004210
- mapped wheel target: left=1.00, right=1.00

The artifact harness explicitly reported:

- no CoppeliaSim connection opened;
- no motor command sent.

## Next gate

Do not start AirGPU yet.

The next implementation slice is a scene-owned file-based frame handoff that preserves the proven Step-4 camera isolation boundary. Only after that adapter and its tests pass locally should live CoppeliaSim qualification be considered.
