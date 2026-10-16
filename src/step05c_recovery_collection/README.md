# Step 5C — Session-aware recovery data

The first three closed-loop autonomous attempts showed that the current v3 model does not generalize reliably once the robot drifts away from the human training trajectory. This stage moves back to data/evaluation rather than adding more motor-control heuristics.

## Why this stage exists

The original data was recorded at about 10 frames per second and the Step-5 notebooks randomly split individual images into train/validation/test sets. Adjacent frames from the same manual lap can therefore land in different splits.

For the next model:

1. treat each manual collection run as a separate session;
2. keep complete sessions together during evaluation;
3. collect additional human demonstrations around the difficult right-turn and recovery states;
4. keep the accepted Step-4 dataset unchanged;
5. retrain only after the new sessions are preserved and audited.

## Recovery collector

record_recovery_session.py is human-controlled W/A/D driving. The accepted v3 CNN runs in shadow mode only. Every stable human-command frame is stored under a new timestamped recovery_sessions/ folder with metadata containing the v3 prediction, probabilities, agreement, and robot pose.

This keeps new evidence separate from the accepted dataset until it has been reviewed.

Run it with the existing Python 3.11 Step-6 environment and accepted v3 model:

    & "F:\Shubham Raj\PythonEnvs\intelligent-robotics-step06-py311\Scripts\python.exe" .\src\step05c_recovery_collection\record_recovery_session.py --model "F:\Shubham Raj\GitHub\intelligent-robotics-maze-navigation\models\maze_navigation_model_v3.h5"

Do not merge new recovery images into dataset/ manually. They will be incorporated only by the later session-aware retraining workflow.
