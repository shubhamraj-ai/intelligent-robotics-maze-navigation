# Intelligent Robotics Maze Navigation

University of Aberdeen - EG506P Intelligent Robotics for Energy Infrastructure  
Design Project technical archive.

This repository presents the final submission artefacts and compact validation evidence for a PioneerP3DX maze-navigation system in CoppeliaSim.

## Final architecture

The final navigation pipeline is intentionally simple:

50 x 50 camera -> grayscale/normalisation -> 2500-input, 3-output softmax perceptron -> lightweight supervisory checks -> wheel commands

The neural network remains the primary navigator. In the representative clean V2 acceptance run on the original Maze.ttt, 483 of 486 movement pulses used the raw neural-network action directly (99.38% prediction-to-applied-action agreement). Three pulses were corrected at ambiguous right-turn entrances.

This percentage is action agreement, not held-out classification accuracy.

## Repository structure

- final-deliverables/ - frozen seven technical deliverables used for the project submission.
- scenes/ - original maze and Step-7 ultrasonic-sensor scene used for reproducibility/testing.
- baselines/golden/ - first preserved successful full autonomous-navigation evidence.
- baselines/diamond/ - ultrasonic/mapping-capable preserved baseline and Step-7 evidence.
- baselines/platinum/ - simplified traversal baseline that exposed a turn-state bookkeeping issue near the terminal region.
- baselines/platinum-v2/ - corrected simplified baseline that recognised the NN-executed fourth right turn and achieved clean terminal stopping.
- evidence/ - compact final validation and robot-control stability evidence.

The previous development-era repository states are preserved in the legacy branches:
- legacy-development-2026-11-13
- legacy-development-main-2026-11-13

## Milestone summary

### Golden
Established a stable full autonomous traversal with four right-turn events and terminal-wall stopping. The evidence log records STEP6_FOUR_RIGHTS_TERMINAL_STOP_PASS.

### Diamond
Extended the preserved controller to Step-7 ultrasonic acquisition and mapping evidence while retaining validated autonomous-navigation behaviour.

### Platinum
Reduced supervisory complexity and completed the maze traversal, but controller state did not recognise one right turn that the neural network had already executed naturally. This caused the terminal region to be interpreted incorrectly.

### Platinum V2
Corrected state interpretation rather than adding another forced turn. The clean V2 acceptance run completed the maze and terminal stop while applying 483/486 raw NN movement predictions directly (99.38%).

## Reproducibility notes

The final submitted network is a simple perceptron-style classifier, not a CNN. The final dataset contains 426 labelled 50 x 50 images. The final ultrasonic dataset contains 499 pose/range samples. The final MATLAB script reconstructs wall points from fixed sensor mounting geometry plus recorded robot pose and valid sensor distances.

## Citation and access

A CITATION.cff file and REPORT_CITATION_GUIDE.md are included. The repository is currently private. Before using it as a marker-accessible reference, either grant the marker access or publish an approved evidence-only version that does not expose course material that should remain private.

## Historical preservation

Cleaning main did not erase earlier development history. Git history and the two legacy branches retain the pre-archive development states.
