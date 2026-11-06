# Step 5 partial turn-weight candidate selection — 2026-11-06

## Trigger

The selected unweighted simple perceptron successfully completed the first live
corner but failed the second-corner traversal. The live second-corner region
showed short left bursts followed by premature reversion to forward, ending in
a wall collision.

The current final model therefore remains preserved, but Step-5 model balance
was reopened narrowly as an evidence-backed experiment.

## Fixed constraints

The experiment changes only class weighting.

Unchanged:
- official 385-image dataset;
- sessions S01/S02/S03;
- image counts 313 forward / 36 left / 36 right;
- dataset ZIP SHA-256:
  887d4f8e56c2c4274947505984ebab4071512660acce6f28ec5d0b5524a6cb2e;
- grayscale 50x50 -> flatten 2500 preprocessing;
- one linear 2500 -> 3 softmax layer;
- no CNN;
- leave-one-session-out cross-validation;
- learning rate 0.01;
- 3200 epochs;
- L2 0.0001;
- seed-robustness evaluation.

## Existing endpoints

Unweighted:
- forward recall ~0.9840;
- left recall 0.7222-0.7500;
- right recall 0.5833-0.6111;
- forward->turn false-positive rate 1.60%.

Fully balanced:
- forward recall 0.8626;
- left recall 0.9444;
- right recall 0.9722;
- forward->turn false-positive rate 13.74%.

Neither endpoint is suitable for automatic promotion after the observed live
failure.

## Coarse sweep — seed 42

Relative weights are forward=1.0 and left/right=M.

| M | Accuracy | Macro-F1 | Forward recall | Left recall | Right recall | Fwd->turn |
|---|---:|---:|---:|---:|---:|---:|
| 1.5 | 0.9325 | 0.8541 | 0.9776 | 0.8056 | 0.6667 | 2.24% |
| 2.0 | 0.9299 | 0.8585 | 0.9617 | 0.8056 | 0.7778 | 3.83% |
| 2.5 | 0.9351 | 0.8720 | 0.9585 | 0.8333 | 0.8333 | 4.15% |
| 3.0 | 0.9325 | 0.8692 | 0.9521 | 0.8611 | 0.8333 | 4.79% |
| 4.0 | 0.9143 | 0.8405 | 0.9297 | 0.8611 | 0.8333 | 7.03% |

The useful Pareto region is 2.0-3.0. M=4.0 is already too aggressive.

## Five-seed robustness

### M=2.0
All five seeds reproduced:
- accuracy 0.9299;
- macro-F1 0.8585;
- forward recall 0.9617;
- left recall 0.8056;
- right recall 0.7778;
- forward->turn 3.83%.

### M=2.5
Across seeds 1-5:
- mean accuracy 0.9356;
- mean macro-F1 0.8731;
- forward recall 0.9585;
- mean left recall 0.8389;
- right recall 0.8333;
- forward->turn 4.15% for all seeds.

Four of five seeds produced left recall 0.8333; seed 4 produced 0.8611.

### M=3.0
Across seeds 1-5:
- mean accuracy 0.9319;
- mean macro-F1 0.8684;
- mean forward recall 0.9514;
- left recall 0.8611;
- right recall 0.8333;
- mean forward->turn 4.86%;
- maximum forward->turn 5.11%.

## Candidate decision

M=2.5 is selected as the **experimental live-test candidate**, not as the new
final model.

Reason:
- materially stronger left/right recall than the unweighted baseline;
- substantially lower premature-turn rate than full balancing;
- best macro-F1 in the tested intermediate region;
- stable across seeds;
- M=3.0 adds little useful turn recall while reducing forward safety margin.

## Candidate artifact

Output folder:
F:\Shubham Raj\IntelligentRobotics_Results_2026-11-06\step05_partial_weight_candidate_2p5

H5:
maze_navigation_simple_perceptron_turn2p5_candidate.h5

H5 SHA-256:
0616621f18f234d727e8cd944695752836492c1d5faf7406c8d29fe2d544a2de

Metadata JSON:
maze_navigation_simple_perceptron_turn2p5_candidate.json

JSON SHA-256:
7620efd0b22ec95e07400b8d5878c9d819ffcb43c0894147fe37dabd0da8de86

H5/NPZ parity:
- 385 images checked;
- 0 label mismatches;
- maximum probability error 0.

## Runtime isolation

The normal Step-6 metadata validator remains pinned to the selected unweighted
final model.

Experimental candidate metadata is accepted only through an explicit
experimental-turn-multiplier opt-in. The candidate cannot silently replace the
current final model.

Test status after experimental runtime support:
- targeted Step-6 tests: 17/17 PASS;
- complete repository suite: 67/67 PASS.

## Promotion rule

Do not promote M=2.5 based on offline metrics alone.

Next:
1. copy the preserved second-corner live evidence from AirGPU;
2. compare current-final vs M=2.5 predictions on those exact live frames;
3. only if the candidate improves the failed turn sequence without creating
   obvious premature-turn behavior, perform a bounded AirGPU live
   second-corner qualification;
4. preserve the current final model until that live gate passes.
