# Step-2 AirGPU Validation and Controller-Stability Evidence

**Project:** Intelligent Robotics for Energy Infrastructure â€” Design Project
**Date:** 2026-11-01
**Branch:** step-05-06-simplified-baseline

## Outcome

Step 2 is now validated on AirGPU using the accepted professor-aligned motion profile:

- Forward: (1.00, 1.00)
- Curved left: (0.10, 1.00)
- Curved right: (1.00, 0.10)

Two complete full-maze manual traversals were completed successfully with no CoppeliaSim crash when the controller used event-driven/state-change motor commands.

## Cloud environment

The successful validation environment was:

- AirGPU, Asia Pacific (Mumbai)
- Windows Server 2025
- NVIDIA Tesla T4
- 8 vCPU
- 32 GB RAM
- 100 GB SSD
- CoppeliaSim Edu 4.9.0 rev6
- Python 3.11.9
- Git 2.56.0
- repository branch step-05-06-simplified-baseline

Microsoft Remote Desktop (RDP) provided the reliable interactive access path. Moonlight had failed earlier, and Parsec was abandoned after poor/locked-screen behaviour. RDP was sufficient for the successful CoppeliaSim validation.

## Controlled isolation sequence

After the original Step-2 controller also caused CoppeliaSim to disappear on the AirGPU VM, three controlled tests were run.

### Test A â€” simulation only

The maze simulation ran without the Python controller.

**Result: PASS.**

### Test B â€” idle ZMQ connection

Python connected to CoppeliaSim, resolved the PioneerP3DX and both motor objects, and remained connected without issuing motor commands.

**Result: PASS.**

### Test C â€” one bounded movement

Python issued one forward wheel command, waited briefly, issued one stop command, then remained idle.

**Result: PASS.**

These results show that the scene/physics alone, basic ZMQ connectivity, object lookup, and a single bounded motor actuation were individually stable on the cloud VM.

## Original loop versus validated workaround

The earlier Step-2 controller continuously polled keyboard state and sent both wheel velocities every 0.05 seconds even when the requested motion had not changed.

The successful experimental controller changed two related behaviours:

1. keyboard handling used key events/state transitions rather than continuous is_pressed polling; and
2. wheel commands were sent only when the requested motion state changed.

With that controller:

- the short W/A/W/D smoke test passed;
- Traversal 1 completed the full maze;
- Traversal 2 completed the full maze;
- no CoppeliaSim crash occurred.

## Interpretation â€” cautious wording required

The evidence supports the following engineering conclusion:

> **The original continuous polling / repeated-command control loop is the likely crash trigger, and event-driven state-change control is the validated workaround.**

Do not claim that 20 Hz ZMQ writes alone are a proven root cause.

The successful controller changed both keyboard handling and motor-write frequency, so the exact lower-level cause could still be:

- redundant/high-frequency ZMQ motor writes;
- repeated keyboard polling;
- an interaction between the two; or
- another timing effect in that loop.

Further root-cause isolation is not currently required because a stable project-compatible workaround has been validated.

## Cross-machine significance

The instability was previously observed on the local Lenovo laptop and was then reproduced on a substantially different environment: Windows Server 2025 with a Tesla T4.

That makes a laptop-specific hardware cause substantially less likely.

The successful event-driven/state-change controller on AirGPU therefore has a strong basis for a later local-laptop smoke validation.

The local validation should remain conservative:

1. one short 30-second W/A/D smoke test;
2. if stable, one complete full-maze traversal;
3. stop immediately if CoppeliaSim disappears or crashes.

## Repository design response

The repository now adopts this rule:

> **Continuous camera/data/inference loops may keep their required sampling frequency, but wheel target commands should only be transmitted when the requested left/right velocity pair changes.**

Applied scope:

- Step 2: event-driven keyboard state plus state-change motor writes;
- Step 4: continuous camera/data recording remains, W/A/D state is maintained from keyboard events rather than repeated is_pressed polling, and duplicate motor writes are suppressed;
- Step 6 shadow/manual control: continuous inference/logging remains, W/A/D state is maintained from keyboard events, and duplicate manual motor writes are suppressed.

The calibrated Step-2/Step-4 motion profile itself is unchanged.

## Automated validation

After implementing the controller changes:

- git diff --check passed;
- the project dependencies were installed into a temporary isolated Python 3.11 virtual environment;
- the initial state-change suite passed 19 tests; after extending event-driven keyboard-state handling to Steps 4 and 6, the full unittest suite passed **21/21 tests**;
- the temporary test environment was removed afterward.

The new regression tests specifically verify that repeated identical wheel commands do not generate repeated CoppeliaSim motor writes.

## Dependency gate

With the two successful full-maze traversals:

**Step 2 = PASS on AirGPU.**

The dependency can now advance to:

**Step 4 fresh data collection -> Step 5 simple NN/perceptron baseline -> Step 6 autonomous validation -> Step 7 ultrasonic mapping**

Step 4 should begin after the short local-laptop validation if practical. AirGPU remains a known-good fallback if local execution is still unstable.

## Academic-writing significance

This episode should be retained in the final report as an example of:

- controlled fault isolation;
- cross-machine reproduction;
- separating observation from root-cause claims;
- reducing unnecessary communication/control traffic;
- reproducibility;
- cloud fallback and cost management;
- evidence-based iteration rather than increasing controller or model complexity.

The report should state that the workaround was validated experimentally while the exact low-level root cause remained unproven.

## AirGPU data/security close-out

Before stopping the successful AirGPU session:

- reusable GitHub HTTPS credentials were erased from Git Credential Manager;
- there was no GitHub browser session in Edge;
- Parsec hosting/account access was disabled/logged out;
- the repository, Python environment, CoppeliaSim installation, working scene, and diagnostic files were intentionally preserved on the stopped VM for possible future fallback use.

No AirGPU runtime is required for the code/test/documentation stage that follows.

## Local Lenovo follow-up â€” 2026-11-02

The validated Step-2 controller was retested on the Lenovo using **CoppeliaSim Edu 4.9.0 rev6**, matching the successful AirGPU simulator build.

- the short W/A/D smoke test passed;
- the first full-maze traversal then crashed shortly before the second turn;
- Windows recorded `Application Error` / WER with `coppeliaSim.exe`, `ntdll.dll`, and exception `0xc0000374` (`STATUS_HEAP_CORRUPTION`);
- the same exception family had also been observed with the older local CoppeliaSim 4.7 build.

Therefore the event-driven/state-change controller remains the validated workaround for the AirGPU failure mode, but it is **not sufficient to make the Lenovo simulator environment reliable**.

Project decision: retain **AirGPU as the validated simulator environment** and avoid further repeated local CoppeliaSim retries during the core project. The detailed local evidence is recorded in `docs/lenovo_local_validation_failure_coppeliasim_490_2026-11-02.md`.


