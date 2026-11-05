# Step 6 first-turn gate — 36-pulse no-turn result and pose-diagnostic follow-up — 2026-11-05

## Live result

The AirGPU first-turn qualification completed a full 36-pulse bounded batch using:

- unchanged persistent Step-4 Lua camera-save path;
- final simple perceptron;
- locked wheel speeds 1.00 / 0.10 / 1.00;
- 0.25 s pulse duration;
- full STOP after every pulse;
- automatic stop-on-first-turn enabled.

No left/right decision occurred.

All 36 distinct fresh frames were classified as forward and all 36 pulses ended STOPPED.

Human visual observation confirmed:
- robot moved forward only;
- robot did not visibly deviate;
- robot remained on track;
- robot did not approach or collide with a wall;
- simulation was stopped manually after gate completion.

## Probability trend

The left probability increased gradually through the middle of the run, peaking around 0.030758 near pulse 18, while forward remained dominant.

Later, left probability decreased and forward confidence rose again above 0.99.

This demonstrates changing visual input, not a frozen-frame condition, but does not by itself establish whether the robot physically reached the first corner.

## Interpretation

This is a PASS for:
- 36 distinct fresh-frame acquisitions;
- repeated final-H5 inference;
- repeated bounded forward actuation;
- mandatory stop-between-frame behavior;
- simulator stability;
- absence of false left/right decisions during the observed straight corridor.

It does NOT yet prove:
- that the robot reached the first corner;
- live left-turn classification;
- live right-turn classification;
- curved actuation.

## Diagnostic follow-up

The pulse qualification now logs robot pose after every bounded pulse:

- world x;
- world y;
- world z;
- yaw.

Pose is diagnostics-only evidence.

It is NOT used:
- to classify frames;
- to choose forward/left/right;
- to modify wheel speeds;
- to trigger a turn;
- to implement route logic.

The navigation decision remains exclusively:
camera JPEG -> final simple perceptron -> label -> locked wheel mapping.

## Validation after pose logging

Targeted Step-6 pulse tests:

- 4 / 4 PASS

Complete repository suite:

- 63 / 63 PASS

## Next gate

Repeat the bounded first-turn qualification with pose logging enabled.

The next result must answer:
1. how far the robot actually travels during the bounded batch;
2. whether yaw remains essentially straight;
3. whether the robot reaches the first corner before the batch ends;
4. whether the first genuine left/right prediction occurs.

Do not retune the model, motion profile or camera path before this evidence is collected.
