# Step 6 â€” Autonomous CNN navigation

This program is the first autonomous-navigation implementation after the accepted Step-5B v3 CNN and the successful Step-6A-v3 shadow validation.

## What it does

- Reads the live `/PioneerP3DX/cam1` image from CoppeliaSim.
- Reproduces the Step-5 preprocessing contract: top-down RGB, 50x50, float32, scaled to `[0, 1]`.
- Uses the accepted v3 CNN with class order `forward=0, left=1, right=2`.
- Maps each applied CNN navigation command to the established wheel commands:
  - `forward` â†’ left `2.0`, right `2.0`
  - `left` â†’ left `-2.0`, right `2.0`
  - `right` â†’ left `2.0`, right `-2.0`
- Stops both motors on shutdown or error.
- Ignores the initial all-zero vision-sensor frame if CoppeliaSim exposes one.

After the first raw closed-loop run exposed rapid left/right oscillation at a right-hand turn, the controller now requires two consecutive matching turn predictions before applying a left or right motor command. A single unconfirmed turn frame falls back to forward. This is a minimal generic stabilizer based on observed closed-loop behavior; it does **not** add confidence thresholds, route hard-coding, ultrasonic logic, or Step-7 mapping logic.

## Runtime

Use the existing Step-6 Python environment:

- Python 3.11.9
- TensorFlow 2.21.0
- packages pinned in `requirements-step06.txt`

The default model path is:

`models/maze_navigation_model_v3.h5`

The model remains Git-ignored and must not be committed.

## Live run

1. Open `Maze_working_4_7.ttt` in CoppeliaSim Edu 4.7.0 rev4.
2. Leave the simulation stopped.
3. From the repository root, run:

```powershell
& "F:\Shubham Raj\PythonEnvs\intelligent-robotics-step06-py311\Scripts\python.exe" .\src\step06_autonomous_navigation\autonomous_navigation.py
```

4. Wait for:

```text
READY: autonomous navigator is initialized.
Waiting for CoppeliaSim simulation to run...
```

5. Start the CoppeliaSim simulation.
6. Wait for:

```text
SIMULATION RUNNING DETECTED â€” CNN MOTOR CONTROL IS ACTIVE NOW.
```

At that point the CNN controls the robot directly. Do not use W/A/D in this program.

Stop the CoppeliaSim simulation when the run is complete or if the robot becomes stuck or behaves incorrectly. The Python process then exits and stops both motors.

## Automated validation

Run the full repository test suite with:

```powershell
& "F:\Shubham Raj\PythonEnvs\intelligent-robotics-step06-py311\Scripts\python.exe" -m unittest discover -s tests -v
```

## Local evidence

Each autonomous run writes an ignored CSV under autonomous_logs/ with the raw CNN prediction, the applied command after two-frame turn confirmation, class probabilities, and confidence. These logs are for validation evidence and are not committed.
