# Step 6A — Shadow inference validation

This is a safety/quality gate before autonomous motor control.

- The human operator still drives the PioneerP3DX with **W/A/D**.
- The v2 CNN receives the live camera frame and predicts **forward/left/right**.
- The model prediction is logged and compared with the stable human command.
- **The model never actuates the motors in this program.**
- Frames with no key or multiple simultaneous W/A/D keys are logged but excluded from scored metrics.
- Startup all-zero camera frames are ignored so the first CoppeliaSim sensor cycle is not counted as a prediction.

The summary focuses especially on the v2 model's known offline failure mode: predicting **left** on some true-forward frames.

## Runtime

The existing project virtual environment uses Python 3.14, which is not the TensorFlow runtime used for this validation. A separate Python 3.11 environment is used so Steps 1–5 remain undisturbed.

The tested local runtime is:

- Python 3.11.9
- TensorFlow 2.21.0
- NumPy 2.4.6
- OpenCV 5.0.0.93
- CoppeliaSim ZMQ Remote API client 2.0.4
- keyboard 0.13.5

Install the pinned packages from `requirements-step06.txt`.

Place a local copy of `maze_navigation_model_v2.h5` at `models/maze_navigation_model_v2.h5`, or supply another path with `--model`. The `.h5` file and runtime CSV logs are intentionally ignored by Git.

## Validation run

1. Open `Maze_working_4_7.ttt` in CoppeliaSim Edu 4.7.0 rev4.
2. Start the simulation.
3. Run the shadow program with the Python 3.11 environment.
4. Manually navigate the same clean route with W/A/D.
5. At the destination, press **Ctrl+C in the terminal first**, then stop CoppeliaSim.

On the current laptop the command is:

    & "F:\Shubham Raj\PythonEnvs\intelligent-robotics-step06-py311\Scripts\python.exe" .\src\step06_shadow_inference\shadow_inference.py

The run writes a CSV containing each live prediction and a text summary containing:

- overall human/model agreement;
- a three-class confusion matrix;
- per-class precision, recall and F1;
- the false-left rate while the human command is `forward`;
- the longest consecutive false-left streak.

The decision gate is based on sequential live behavior. An isolated false-left prediction is materially different from a persistent sequence of false-left predictions while the robot should continue straight.
