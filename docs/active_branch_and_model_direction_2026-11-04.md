# Active branch and model-direction policy — 2026-11-04

## Purpose

This file defines the only active engineering direction for the Intelligent Robotics Design Project after Step 5 was closed successfully.

The goal is to prevent historical diagnostic, CNN-era, or superseded experimental branches from being mixed back into the active project line.

## Active source-of-truth branches

### `main`

Canonical completed project baseline through Step 5.

Current Step-5 model direction:

- simple linear softmax perceptron only;
- input: 50x50 camera frame;
- OpenCV grayscale conversion;
- float32 normalization by 255;
- flatten to 2500 features;
- one 3-output softmax layer;
- labels: forward / left / right;
- final configuration: epochs=3200, learning_rate=0.01, L2=0.0001, seed=42, class_weighting=none.

### `feature/step06-final-simple-perceptron-navigation`

The only active Step-6 development branch.

All new autonomous-navigation work must be created here from the final simple-perceptron Step-5 model.

## Explicitly forbidden in the active Step-6 implementation

Do not introduce or reuse:

- CNN / Conv2D architectures;
- hidden neural-network layers;
- pooling layers;
- dropout;
- the historical CNN autonomous controller;
- TensorFlow-based image resizing or CNN preprocessing;
- the historical 1.20-second CNN turn-commitment controller;
- route-specific maze logic;
- ultrasonic sensing or Step-7 mapping logic;
- old CNN model files such as maze_navigation_model_v2.h5 / v3 / v4 / v5 / v6 / v7.

The final Step-6 runtime should remain simple and coursework-aligned.

Preferred inference path:

camera frame
-> validated CoppeliaSim/OpenCV frame conversion
-> OpenCV grayscale
-> float32 / 255
-> flatten 2500
-> load final Dense(3, softmax) weights from the Step-5 H5 artifact
-> NumPy softmax inference
-> forward / left / right
-> wheel command

TensorFlow is not required for the active Step-6 runtime. The final H5 contains a single 2500x3 kernel and a 3-element bias, so the runtime can read those weights with HDF5 tooling and perform inference directly in NumPy.

## Historical / isolated branches — preserve, do not merge into active line

The following branches remain valuable evidence but are not active development sources:

- `archive/main-pre-step05-final-2026-11-04`
- `step-05c-session-aware-retraining`
- `step-06-autonomous-navigation`
- `feature/step05-simple-mlp-baseline`
- `feature/step05-balanced-perceptron`
- `feature/step05-simple-perceptron-baseline`
- `feature/step04-stable-session-recorder`
- `step-05-06-simplified-baseline`
- every `diagnostic/step04-*` branch.

These branches may be read for historical evidence, debugging context, or report provenance only.

They must not be merged, rebased, cherry-picked, or used as the source of new Step-6 code without a fresh explicit reconciliation decision.

## Legacy files still present on main

Some CNN-era files remain in repository history/current main because they are evidence from earlier project phases, including:

- `src/step06_shadow_inference/shadow_inference.py`
- `requirements-step06.txt`

They are historical only.

New Step-6 code must not import, extend, copy from, or depend on those files.

New implementation should live under:

`src/step06_simple_perceptron_navigation/`

with separate tests under:

`tests/test_step06_simple_perceptron_navigation.py`

## Step boundaries

- Step 5: CLOSED / validated.
- Step 6: active next phase, not yet completed.
- Step 7: not started.

No AirGPU live qualification should begin until the new simple-perceptron Step-6 implementation passes local/static/unit validation first.
