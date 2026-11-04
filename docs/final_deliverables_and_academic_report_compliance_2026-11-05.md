# Final deliverables and academic-report compliance ledger — 2026-11-05

## Purpose

This document prevents the Intelligent Robotics Design Project from drifting away from the professor's published requirements while preserving the experimentally validated architecture that finally proved stable.

It is a project-closeout ledger, not a replacement for the official question paper.

## Professor guidance to preserve in the final report

Course-team guidance dated 25 October 2026 explicitly states that final neural-network driving behaviour depends on multiple factors, including:

- turning radius / curvature;
- robot travelling speed;
- amount of training data;
- distribution of training data;
- quality of training data;
- neural-network architecture;
- random initial weights / initialization.

The professor also states that the exercise expects students to experiment with these factors until a working balance is found.

Critically, the guidance says a CNN is not required and that a simple perceptron is usually sufficient. Excessively complex neural-network structures can worsen robot behaviour and may reduce the final grade unless there is a proper reason that is clearly justified and documented.

This guidance is directly aligned with the final project direction:
- no CNN;
- simple perceptron;
- explicit motion-profile calibration;
- documented data-distribution and class-balance experiments;
- documented simulator-instability investigation;
- justified architecture choices.

## Project-step compliance status

### Step 1 — Python/CoppeliaSim communication

Official intent:
- establish Python/CoppeliaSim communication through the ZMQ Remote API Client.

Current project state:
- implemented and validated;
- Python connects through RemoteAPIClient;
- required robot, motor and camera objects are resolved;
- robot pose can be read.

Status:
- CLOSED.
- No redesign planned.
- Preserve evidence for final report.

### Step 2 — Manual Python keyboard control

Official intent:
- manually navigate the robot through the maze using Python keyboard input.

Current project state:
- implemented and validated;
- final accepted motion profile:
  - forward = 1.00 / 1.00;
  - curved left = 0.10 / 1.00;
  - curved right = 1.00 / 0.10;
- state-change/event-driven motor writes;
- two complete AirGPU full-maze traversals passed.

Status:
- CLOSED.
- Do not re-tune unless Step-6 live evidence demonstrates a real requirement.
- This balance is part of the final academic narrative.

### Step 3 — Camera stream to Python/OpenCV

Official intent:
- stream real-time robot-camera images into Python;
- process/analyse the feed with OpenCV.

Current project state:
- direct Python implementation exists in:
  src/step03_camera_stream/camera_stream.py
- it uses:
  - ZMQ Remote API;
  - sim.getVisionSensorImg();
  - NumPy buffer conversion;
  - vertical image correction;
  - OpenCV RGB-to-BGR conversion;
  - OpenCV live display.

Important nuance:
- later combined vision + motion + recording experiments exposed simulator instability.
- the stable Step-4 architecture therefore moved camera acquisition/saving into scene-owned persistent Lua.

Status:
- IMPLEMENTED, but FINAL COMPLIANCE EVIDENCE STILL REQUIRED.
- Before submission, perform one short isolated Step-3 revalidation/evidence run.
- Do not replace the stable Step-4 pipeline with this direct camera path unless a new stability result justifies it.

Academic-report obligation:
- explain that direct Python/OpenCV camera integration was achieved;
- explain why it was isolated from the later high-reliability recording/autonomy path;
- document simulator-instability evidence rather than hiding the architectural deviation.

### Step 4 — Record camera images + forward/left/right commands

Official intent:
- during manual navigation, record camera images and associate them with forward/left/right commands;
- final submission wording also describes a Python application controlling the robot and storing the images into the three class folders.

Current project state:
- final stable dataset was successfully produced using:
  - Python for manual motion/control;
  - a small Python-to-Lua class-label signal;
  - persistent scene-owned Lua for camera acquisition and JPEG saving;
- final official Step-5 dataset:
  - 385 images total;
  - forward = 313;
  - left = 36;
  - right = 36;
- stable capture history is preserved by the tag:
  step4-stable-capture-2026-11-03

Important nuance:
- the architecture is functionally correct and experimentally stable;
- it is not a literal one-process interpretation of the strongest wording in the final deliverables section.

Status:
- DATA COLLECTION: COMPLETE.
- STABILITY BASELINE: LOCKED.
- FINAL SUBMISSION-COMPLIANCE PACKAGING: PENDING.

Required closeout work:
1. do not recollect or replace the validated dataset by default;
2. preserve the exact stable Lua capture architecture;
3. perform a final Step-4 deliverable audit after Step 6;
4. if needed, add a thin Python launcher/orchestrator around the stable components;
5. if a direct-Python recording demonstration is academically useful, make it a small separate compliance demonstration, not a replacement dataset.

Academic-report obligation:
- document the instability that forced architecture separation;
- document the diagnostic experiments and why the persistent Lua camera path was selected;
- explain that this architecture preserved the required labels/dataset while avoiding repeated simulator crashes;
- distinguish "functional requirement achieved" from "implementation architecture differs from the simplest literal reading."

### Step 5 — Google Drive/Colab neural-network training

Official intent:
- upload the dataset;
- train a neural network in Google Colab;
- submit the training notebook and trained .h5 model.

Current project state:
- CLOSED successfully;
- executed Colab notebook preserved;
- final model:
  2500 -> Dense(3, softmax)
- labels:
  forward / left / right
- final configuration:
  epochs = 3200
  learning_rate = 0.01
  L2 = 0.0001
  seed = 42
  class_weighting = none
- leave-one-session-out validation retained;
- final .h5 and JSON evidence verified independently.

Status:
- CLOSED.
- Do not replace with CNN.
- Do not reopen model architecture unless Step-6 evidence demonstrates a concrete failure that cannot be solved within the professor-aligned simple model direction.

Academic-report obligation:
- document why the simple perceptron was selected;
- document class-balance experiments and why the final unweighted model was chosen;
- discuss random initialization/convergence sensitivity;
- include the professor's explicit guidance that a simple perceptron is generally sufficient.

### Step 6 — Autonomous navigation

Official intent:
- load the trained neural-network model into Python;
- use camera input to make autonomous forward/left/right decisions;
- navigate the maze without manual control;
- reach the maze end.

Current project state:
- active branch:
  feature/step06-final-simple-perceptron-navigation
- CNN-era branches remain isolated and must not be merged;
- final H5 loader implemented with h5py/NumPy;
- exact Step-5 OpenCV preprocessing implemented;
- NumPy softmax inference implemented;
- locked Step-2 motion mapping implemented;
- stable Step-4 scene-owned camera path reused;
- full local repository suite passed before live qualification;
- first live gate is observation-only and intentionally contains no motor actuation.

Status:
- ACTIVE / NOT YET COMPLETE.

Completion criteria:
1. observation-only AirGPU gate passes with stable frame capture;
2. controlled autonomous actuation gate passes;
3. full autonomous maze traversal completes;
4. final Python navigation code and evidence are frozen;
5. only then may Step 6 be marked CLOSED.

Academic-report obligation:
- distinguish safety/engineering qualification gates from the final autonomous result;
- report failures and tuning decisions factually;
- do not overclaim offline model metrics as live autonomous success.

### Step 7 — Ultrasonic mapping

Official intent:
- add ultrasonic/distance sensing;
- log robot coordinates/orientation + sensor readings over time;
- generate an offline map/visual representation.

Current project state:
- not started by design.

Status:
- PENDING AFTER STEP 6.
- Do not mix Step-7 sensing/mapping logic into the active Step-6 navigation controller prematurely.

## Final deliverables closeout checklist

Before submission, verify all of the following against the official paper:

- [ ] Python keyboard-control application;
- [ ] direct Step-3 Python/OpenCV camera-stream evidence;
- [ ] final Step-4 data-recording application/packaging compliance;
- [ ] ZIP dataset with forward/left/right folders;
- [ ] executed Google Colab .ipynb;
- [ ] trained .h5 neural network;
- [ ] final Python autonomous-navigation code;
- [ ] successful full autonomous maze traversal evidence;
- [ ] robot coordinates/orientation + distance-sensor readings text file;
- [ ] Python/Matlab mapping code;
- [ ] generated maze visualization;
- [ ] original Maze.ttt provenance retained;
- [ ] final working-scene lineage documented;
- [ ] final academic report completed with evidence-backed rationale.

## Academic-report evidence themes

The final report must explain, with evidence:

1. why the final motion profile is 1.00 / 0.10 / 1.00;
2. why state-change-only motor writes were adopted;
3. what simulator crashes occurred and how they were isolated;
4. why direct Python camera access was retained for Step-3 compliance but not used as the final high-reliability capture architecture;
5. why persistent scene-owned Lua capture was selected for stable Step-4 recording;
6. how dataset quantity/distribution/quality affected model behaviour;
7. why balanced class weighting was tested but the final unweighted perceptron was selected;
8. why the final network is a simple perceptron rather than a CNN;
9. how initialization/convergence sensitivity was addressed;
10. what offline validation can and cannot prove;
11. how Step-6 live qualification was performed;
12. any final deviations from the question paper, with technical justification rather than omission.

## Source/evidence preservation

Do not delete or overwrite the historical evidence.

Retain:
- question paper;
- original Maze.ttt;
- working scene variants;
- AirGPU setup logs;
- CoppeliaSim crash diagnostics;
- Step-4 failure/stability records;
- saved project-context/checkpoint files;
- Git tags and historical diagnostic branches;
- final Step-5 Colab/H5/JSON artifacts;
- Step-6 qualification evidence.

Historical branches are evidence, not active implementation sources.

## Project-close rule

The project must not be declared submission-ready merely because Step 6 eventually works.

After Step 7 is complete, perform a final literal comparison against the official deliverables and this ledger, then perform an academic-report evidence audit before packaging the final submission.
