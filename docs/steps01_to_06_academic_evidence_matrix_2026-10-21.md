# Steps 1–6 Academic Evidence Matrix — 2026-10-21

## Purpose

This is a submission-preparation evidence map for the University of Aberdeen
**Intelligent Robotics for inspection — Design Project Individual**.

It is not the final report and it does not redefine the assignment. The academic
requirements below are taken from the professor's `Project.pdf` (Section 3,
"Your Mission", pp. 3–4, and Section 5, "Deliverables", p. 5).

The matrix separates:

1. what the assignment actually asks for;
2. what has been implemented;
3. what evidence currently exists;
4. the present completion state; and
5. where the evidence/artifact can be found.

This prevents later report writing from relying on memory or accidentally
presenting diagnostic work as an assignment requirement.

---

## Academic authority — concise requirement map

The assignment's seven-step mission is:

1. establish Python–CoppeliaSim communication through the ZMQ Remote API;
2. manually control the robot from Python using keyboard commands;
3. stream the robot camera to Python and use OpenCV;
4. record camera images with associated forward/left/right commands;
5. upload the data to Google Drive and train a neural network in Google Colab;
6. integrate the trained network into Python so the robot autonomously navigates
   the maze from camera input and reaches the end without manual input;
7. add ultrasonic sensing and create an offline map.

This document covers **Steps 1–6 only**. Step 7 remains intentionally outside
this matrix because implementation has not started.

---

# Primary evidence matrix

| Step | Professor requirement | Our implementation | Verification / evidence | Current status | Canonical file / artifact location |
|---|---|---|---|---|---|
| **1 — Communication with Simulator** | Establish communication between CoppeliaSim and Python using the **ZMQ Remote API Client** so Python can access/control the simulated robot. | A Python connection test creates a `RemoteAPIClient`, requires the `sim` API, resolves the floor, PioneerP3DX, wheel motors and camera, and reads the robot world pose. | Successful connection/object-resolution/pose validation was completed before proceeding to robot control. Git history explicitly records **"Add Step 1B CoppeliaSim connection test"** and **"Complete Step 1 simulator validation"**. | **COMPLETE** | Code: `src/step01_connection/connection_test.py`  • commits `5615d65`, `cdf7284` |
| **2 — Robot Control via Python and Keyboard Input** | Create a Python application for manual maze navigation using keyboard commands such as **forward, left and right**. | `W` drives both wheels forward; `A` and `D` command opposite wheel velocities for left/right turns; motor-stop cleanup is included. Current control interval is 50 ms. | Manual W/A/D traversal was demonstrated successfully. Later simulator-crash isolation independently re-tested motor control at 100 ms and 50 ms and confirmed those control loops themselves could run stably. | **COMPLETE** | Code: `src/step02_manual_control/manual_control.py` • original commit `92773d7` • stability evidence: `docs/step2_crash_isolation_2026-10-18.md`, `diagnostic_logs_step2/` |
| **3 — Camera Streaming / OpenCV** | Stream real-time images from the robot camera to Python and use **OpenCV** to process/analyse the images. | The camera stream resolves `/PioneerP3DX/cam1`, retrieves the CoppeliaSim vision-sensor buffer, validates dimensions, flips bottom-up RGB to top-down orientation, converts RGB→BGR for OpenCV and displays the live feed. | Step 3 was manually validated with the live robot camera. Camera-only and manual-control-plus-camera combinations were also exercised during later simulator isolation. | **COMPLETE** | Code: `src/step03_camera_stream/camera_stream.py` • commit `e71767a` • stability evidence: `docs/step2_crash_isolation_2026-10-18.md` |
| **4 — Recording Data for Neural Network Training** | During manual navigation, record camera images and the associated **forward / left / right** commands for later NN training. | A single Python program drives the robot with W/A/D while capturing camera frames. Stable single-key inputs are mapped to `forward`, `left`, `right`; images are written into class folders at a controlled interval using unique timestamped filenames. Ambiguous/no-key input is not saved as a class image. | The project produced a real three-class image dataset from manual maze traversal. The base repository currently retains the original class folders locally (Git-ignored), while cleaned/uploaded dataset ZIPs are preserved in the project Google Drive. | **COMPLETE** | Code: `src/step04_data_recording/record_training_data.py` • commit `113472f` • local base dataset: `F:\Shubham Raj\GitHub\intelligent-robotics-maze-navigation\dataset\{forward,left,right}\` • Drive clean archive: `dataset_v2_clean_2383.zip` |
| **5 — Google Drive + Google Colab NN Training** | Upload collected images/commands to Google Drive and train a neural network in **Google Colab** to predict driving commands from camera input; preserve the notebook and trained `.h5` model. | A Colab notebook loads the three-class image dataset, applies 50×50 RGB preprocessing, trains a 3-class CNN and saves an H5 model. Subsequent v3–v7 notebooks are controlled diagnostic/retraining work arising from Step-6 failures; they do not negate completion of the assignment's Step 5 training task. | Original Colab training completed successfully and generated a usable H5 model. The accepted early artifact `maze_navigation_model_v2.h5` is preserved in Drive. Later session-aware experiments produced v4–v7 models/metrics and materially strengthened the engineering evidence around generalisation. | **COMPLETE** | Notebook: `notebooks/step05_train_neural_network.ipynb` • initial training commit `3837a45` • Drive model: `maze_navigation_model_v2.h5` • Drive dataset: `dataset_v2_clean_2383.zip` • later diagnostic notebooks in `notebooks/` and metrics/models in Drive |
| **6 — Implementing Autonomous Navigation** | Download/integrate the trained NN into Python so the robot makes decisions from the **camera feed**, navigates **without manual input**, and **reaches the end of the maze on its own**. | Step 6 has two implementation layers: (a) a shadow-inference validator that runs the CNN on live camera frames while the human still drives, and (b) a closed-loop autonomous branch where CNN predictions actuate the wheel motors. Multiple controlled model/data refinements were then tested after premature-turn failures. | The integration itself exists and has been exercised. However, autonomous trials are not yet successful enough to satisfy the professor's actual Step-6 outcome: near turns the robot can predict a turn too early, oscillate and fail to complete the maze reliably. v7 passes ordinary recovery validation but fails the independent boundary gate (pre-turn forward accuracy 26%; event pass 20%). A professor clarification has therefore been requested before changing the control/labeling interpretation further. | **IN PROGRESS / NOT YET ACADEMICALLY COMPLETE** | Shadow code: `src/step06_shadow_inference/shadow_inference.py` • shadow commit `3d83fa6` • autonomous code on branch `step-06-autonomous-navigation`: `src/step06_autonomous_navigation/autonomous_navigation.py` • draft PR #12 **DO NOT MERGE** • current diagnostic/recovery work: draft PR #13 and `docs/step05c_*–step05h_*` |

---

# Step-by-step evidence notes

## Step 1 — evidence strength

**Requirement coverage:** complete.

The Step 1 code does more than merely test a socket connection. It verifies the
specific scene objects required by all later stages:

- `/PioneerP3DX`
- `/PioneerP3DX/leftMotor`
- `/PioneerP3DX/rightMotor`
- `/PioneerP3DX/cam1`

It also reads the robot world position and orientation. This is useful evidence
that the Python-to-simulator integration was operational before movement,
vision or ML were introduced.

**Submission evidence candidate:** one short code excerpt plus a screenshot or
terminal output showing successful connection/object resolution. If the final
submission format allows only code rather than screenshots, the source file and
commit history are sufficient technical provenance.

---

## Step 2 — evidence strength

**Requirement coverage:** complete.

The implementation is deliberately simple and assignment-aligned:

- `W` → forward;
- `A` → left;
- `D` → right;
- no key → stop.

No unnecessary autonomous logic is part of Step 2.

Later CoppeliaSim crash investigation should be kept in the report only if it
supports an engineering discussion; it is **not required** to prove Step 2.

**Submission evidence candidate:** `manual_control.py` plus a screenshot/video
frame of manual traversal.

---

## Step 3 — evidence strength

**Requirement coverage:** complete.

The implementation explicitly handles CoppeliaSim's image-buffer convention:

- validates width/height and byte count;
- reshapes RGB bytes into an image;
- vertically flips the bottom-up buffer;
- converts RGB to BGR for OpenCV display.

This is a useful technical detail for the final write-up because it shows that
the OpenCV integration was not just a generic webcam example; it was adapted to
the simulator's camera format.

**Submission evidence candidate:** live camera screenshot plus the conversion
section of `camera_stream.py`.

---

## Step 4 — evidence strength

**Requirement coverage:** complete.

The professor's deliverable language specifically asks for images stored in
three folders corresponding to:

- `forward` for W;
- `left` for A;
- `right` for D.

The implementation follows that exact three-class structure.

Current local base repository counts observed on 2026-10-21:

- forward: 2,139 files
- left: 122 files
- right: 125 files
- total raw/local base-folder count: 2,386 images

The accepted Drive archive `dataset_v2_clean_2383.zip` is a cleaned packaged
artifact and should be treated as the submission-oriented dataset candidate
unless the final Step-6 solution requires a revised final training dataset.

**Important:** the later recovery, hard-negative and boundary datasets are
engineering diagnostics. They should not obscure the simple fact that the
required Step-4 three-folder dataset was successfully created.

---

## Step 5 — evidence strength

**Requirement coverage:** complete.

The professor requires:

- uploaded data;
- Google Colab training;
- a Colab notebook;
- a trained `.h5` neural network.

All four exist.

Primary assignment-aligned artifacts:

- `notebooks/step05_train_neural_network.ipynb`
- Google Drive `dataset_v2_clean_2383.zip`
- Google Drive `maze_navigation_model_v2.h5`

Later artifacts — v3, v4, v5, alpha-0.50, v6 and v7 — are best presented as
**engineering refinement / validation evidence** rather than pretending the
professor explicitly required multiple model generations.

This distinction will keep the final report focused.

---

## Step 6 — evidence strength and unresolved gap

**Implementation coverage:** substantial.

**Outcome coverage:** not yet complete.

The professor's requirement is outcome-based: the trained model should be
integrated into Python, make camera-based decisions without manual input, and
reach the maze end autonomously.

We have already satisfied the **integration** portion technically. The remaining
gap is reliable closed-loop behavior.

Evidence accumulated so far shows:

1. random frame-level evaluation had temporal leakage and overstated
   generalisation;
2. whole-session validation corrected the methodology;
3. class weighting improved aggregate behavior but did not remove premature
   turns;
4. one-sided hard-negative retraining suppressed legitimate turns;
5. paired pre/post turn training improved true-turn recognition but still did
   not distinguish the exact pre-turn boundary reliably;
6. the independent v7 boundary evaluation failed the pre-committed promotion
   gate;
7. pixel-level audit suggests the precise human W→A/D transition is often not a
   uniquely observable single-frame visual boundary.

Therefore the project is **not stuck because Step 6 code is missing**. It is
stuck at the final policy/label interpretation needed to produce stable
autonomous behavior.

Current decision:

- do not run v7 live shadow;
- do not run another autonomous trial merely for another attempt;
- do not merge autonomous PR #12;
- do not merge recovery/retraining PR #13;
- wait for the professor's guidance on per-frame control vs visually defined
  turn regions and/or temporal smoothing.

---

# Submission deliverable crosswalk

The professor's deliverables on p. 5 can already be mapped as follows:

| Required deliverable | Current artifact | Readiness |
|---|---|---|
| Python app controlling robot by keyboard and streaming/storing camera images in forward/left/right folders | `src/step04_data_recording/record_training_data.py` | **Ready** |
| ZIP dataset with three classes | Drive `dataset_v2_clean_2383.zip` (candidate; may be superseded only if final Step-6 training requires a newer submission dataset) | **Ready / final choice pending Step 6** |
| Google Colab training notebook `.ipynb` | `notebooks/step05_train_neural_network.ipynb` | **Ready** |
| Trained neural network `.h5` | Drive `maze_navigation_model_v2.h5`; later models also retained | **Artifact exists; final model choice pending Step 6** |
| Final Python NN navigation code | autonomous branch `src/step06_autonomous_navigation/autonomous_navigation.py` | **Implemented but not final/accepted** |
| Text file with robot coordinates/orientation and distance-sensor readings while NN drives | Step 7 work | **Not started** |
| Matlab/Python code that creates visual maze map from coordinate/distance data | Step 7 work | **Not started** |

---

# Evidence locations — quick reference

## GitHub / local repository

Primary repository:
`shubhamraj-ai/intelligent-robotics-maze-navigation`

Current recovery/evidence branch:
`step-05c-session-aware-retraining`

Current evidence branch checkpoint at matrix preparation:
`f965e7268fc61b5a1021ba987ac3cd0e9cbd71a7`

Step-6 autonomous experiment branch:
`step-06-autonomous-navigation`

Draft PRs:
- PR #12 — autonomous closed-loop experiment — **DO NOT MERGE**
- PR #13 — session-aware recovery / paired-boundary retraining — **OPEN + DRAFT**

## Google Drive project folder

Project folder:
`Intelligent_Robotics_Design_Project`

Key preserved artifacts include:
- `dataset_v2_clean_2383.zip`
- `maze_navigation_model_v2.h5`
- v3–v7 model artifacts
- session-aware metrics JSON files
- confusion matrices
- training histories
- Step 5H paired-boundary dataset package and v7 outputs

## Local non-Git evidence

Base dataset:
`F:\Shubham Raj\GitHub\intelligent-robotics-maze-navigation\dataset\`

Local model/debug evidence is intentionally partly Git-ignored.

Recovery branch evidence directories include:
- `recovery_sessions/`
- `hard_negative_sessions/`
- `boundary_sessions/`
- `shadow_logs_v4/`
- `shadow_logs_alpha050/`
- `shadow_logs_alpha050_nodisplay/`
- `diagnostic_logs_step2/`
- `training_packages/`

---

# Evidence gaps to close later — not work to do now

The following should be addressed during final submission preparation, not by
changing the robotics implementation while professor guidance is pending:

1. choose the **final** dataset ZIP after Step 6 is solved;
2. choose the **final** trained H5 model that actually supports the successful
   autonomous implementation;
3. capture/retain one clean successful Step-6 autonomous run as final behavioral
   evidence;
4. ensure the final Step-6 Python file matches the successful model and control
   strategy;
5. complete Step 7 sensor logging and maze mapping;
6. create the final report/appendix narrative from this evidence matrix rather
   than reproducing every diagnostic experiment.

---

# Current academic status summary

| Step | Status |
|---|---|
| Step 1 — Python/CoppeliaSim ZMQ communication | **COMPLETE** |
| Step 2 — manual W/A/D control | **COMPLETE** |
| Step 3 — camera streaming + OpenCV | **COMPLETE** |
| Step 4 — labelled image recording | **COMPLETE** |
| Step 5 — Google Drive + Colab CNN training | **COMPLETE** |
| Step 6 — autonomous camera/CNN navigation | **IN PROGRESS — professor guidance pending** |
| Step 7 — ultrasonic mapping | **NOT STARTED** |

The correct project focus remains: **finish Step 6 cleanly, then proceed to
Step 7**. No completed Step 1–5 work needs to be repeated.
