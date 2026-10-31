# Simulator Instability, Step-2 Validation Blocker, and Academic Evidence Record

**Project:** Intelligent Robotics for Energy Infrastructure — Design Project  
**Date:** 2026-10-31  
**Active branch:** `step-05-06-simplified-baseline`  
**Baseline commit before this documentation update:** `f8ca87fac275f94aa19ba9a7abe5f8387b31d278`

## 1. Purpose

This document records the current simulator-related blocker and the evidence collected so far. It is a documentation-only checkpoint. It does **not** change the accepted technical sequence or authorize progression to later project steps.

The current dependency remains:

**Step 2 stable full-maze validation -> Step 4 fresh data collection -> Step 5 simple NN/perceptron baseline -> Step 6 autonomous navigation -> Step 7 ultrasonic mapping**

## 2. Accepted Step-2 motion baseline

The professor-aligned motion profile currently implemented in `config/motion_profile.json` is:

- `forward_speed = 1.0`
- `turn_outer_speed = 1.0`
- `turn_inner_speed = 0.10`
- `control_interval_seconds = 0.05`

Resulting commands:

- Forward: `(1.00, 1.00)`
- Left: `(0.10, 1.00)`
- Right: `(1.00, 0.10)`

These forward-only differential turns replaced the earlier aggressive near-pivot commands. Initial local testing indicated that the forward speed was reasonable and the first curved turn at `turn_inner_speed = 0.10` was promising.

This motion profile is **not yet considered fully validated**, because two complete full-maze manual traversals have not been completed reliably.

## 3. Local CoppeliaSim instability evidence

### CoppeliaSim 4.7

Repeated local crashes were observed during simulator use. A previously captured Windows crash signature included:

- executable: `coppeliaSim.exe`
- faulting module: `ntdll.dll`
- exception: `0xc0000374`

The repeated instability made CoppeliaSim 4.7 unsuitable as a trusted environment for completing the remaining simulator-dependent work.

### CoppeliaSim 4.9.0 rev6

CoppeliaSim 4.9.0 rev6 was more stable initially and allowed useful Step-2 motion calibration.

However, the simulator later also crashed during longer/full-maze traversal attempts. A final clean-reboot attempt, with other software minimized, still crashed during the first traversal.

### Current local decision

Further repeated local simulator retries are paused.

This decision is based on:

1. repeated crashes across two CoppeliaSim versions;
2. failure even after a clean reboot/minimal-software attempt;
3. risk of spending substantial time reproducing the same failure;
4. the user's laptop itself becoming unstable/crashing during this work;
5. emerging evidence that another student is experiencing a similar CoppeliaSim/key-control failure.

This does **not** establish the root cause. It only establishes that the present local environment is not sufficiently reliable for evidence-quality full-maze validation.

## 4. External student evidence

On 2026-10-31, a fellow student posted on the module discussion board describing a similar CoppeliaSim problem.

The student reported that:

- keyboard/key-press functionality appears to trigger CoppeliaSim to crash and close when a key is held for some time;
- frequently releasing keys appears to work around the issue temporarily;
- the student is unsure whether this is a common issue or an inefficient Python-script issue;
- the student has asked Dr San-Millan for guidance.

### Interpretation

This is **corroborating evidence only**.

It increases the plausibility that the instability may not be unique to one laptop, but it must **not** yet be cited as proof of a known CoppeliaSim defect or a confirmed course-wide issue.

The professor's eventual response should be treated as higher-authority evidence for the academic interpretation and any recommended workaround.

## 5. AirGPU fallback attempt

Because local CoppeliaSim was considered unreliable, a cloud Windows machine was prepared through AirGPU as a fallback for simulator-dependent Steps 2, 4, and 6.

Configuration used:

- Region: Asia Pacific (Mumbai)
- GPU: NVIDIA Tesla T4
- vCPU: 8
- RAM: 32 GB
- SSD: 100 GB
- OS: Windows Server 2025
- Stream target: 720p / 60 FPS / 7 Mbit/s
- Normal runtime rate: USD 1.70/hour
- Spare-capacity mode was attempted first, but no spare Tesla T4 capacity was available.

### Moonlight access failure

The VM itself successfully reached `Running`, but Moonlight could not reach the pairing/PIN stage.

Controlled tests included:

1. AirGPU-provided hostname;
2. the currently assigned public IP for that session;
3. a later clean restart with Moonlight settings verified;
4. a second hostname test;
5. a second current-public-IP test.

Both controlled access paths failed before pairing.

The AirGPU hostname was independently observed to resolve to the current public IP during the later controlled session, so the failure cannot presently be explained simply as a stale hostname.

No firewall weakening, router port-forwarding, GPU switching, destructive VM recreation, or repeated blind paid retries were performed.

AirGPU was stopped after the controlled failures to preserve project budget.

## 6. AirGPU cost/control evidence

The project treats cost optimization as a constraint equal in importance to successful completion.

The initial AirGPU attempt consumed approximately USD 0.51 before successful desktop access was achieved.

After the controlled troubleshooting attempts, the machine was stopped and left Off. The remaining AirGPU credit is being preserved while support investigates the access failure.

AirGPU support has been contacted with the technical details and asked to:

- verify the host-side Moonlight/Sunshine service;
- verify required network/streaming access;
- identify any machine/region-side issue;
- advise whether RDP, Parsec, or another supported access method is available;
- consider crediting failed troubleshooting runtime where appropriate.

No further paid AirGPU runtime should be consumed until support provides useful guidance or a new evidence-backed access path is identified.

## 7. Current selective-blocked project state

### Blocked

- Completion of Step-2 full-maze manual validation.
- Step-4 fresh dataset collection, because the accepted motion profile must be fully validated first.
- Step-5 simplified model work, because the intended clean dataset does not yet exist.
- Step-6 autonomous navigation.
- Step-7 ultrasonic mapping.

### Not blocked

- Documentation and evidence capture.
- Review of existing code and repository state.
- Academic write-up preparation.
- Planning the next simulator environment.
- Cost/risk evaluation of fallback execution environments.
- Waiting for authoritative technical guidance without altering the accepted project sequence.

### External inputs currently awaited

1. Professor/course-team response to the student discussion-board report about CoppeliaSim/key-control crashes.
2. AirGPU support response regarding Moonlight/Sunshine connectivity and alternative access methods.

## 8. Academic significance and report-ready lessons

These events should be preserved as engineering evidence because they demonstrate more than a simple software failure.

Potential academic themes include:

### Experimental environment reliability

A control or machine-learning result cannot be treated as valid if the simulator repeatedly crashes before a complete traversal can be reproduced.

### System-level diagnosis

Earlier Step-6 instability was initially treated primarily as an ML-model problem. The professor's guidance motivated a return to system-level variables such as speed, turn curvature, data quality, and model simplicity. The simulator instability adds another system-level variable: the reliability of the execution environment itself.

### Evidence-based decision making

The project did not simply abandon local execution after one failure. Multiple simulator versions and a clean-reboot attempt were tried before the local environment was classified as unreliable.

### Reproducibility and limitations

The inability to complete repeatable full-maze traversals is a genuine experimental limitation and should be stated transparently rather than hidden.

### Resource and cost management

The cloud fallback was bounded by an explicit project budget. Failed connection attempts were stopped rather than repeated indefinitely, preserving resources for later validated work.

### External corroboration

A similar report from another student is relevant contextual evidence, but it is being treated cautiously until the professor provides authoritative guidance. This is preferable to prematurely attributing the problem to CoppeliaSim, Python, the `keyboard` library, or hardware without evidence.

## 9. Academic-writing caution

When this material is incorporated into final academic writing:

- describe observed facts precisely;
- distinguish observations from hypotheses;
- do not claim that CoppeliaSim has a confirmed defect unless the professor/vendor evidence supports that statement;
- do not present another student's report as proof of root cause;
- explain troubleshooting choices and why each decision was made;
- connect technical difficulties to engineering lessons, reproducibility, limitations, and design decisions;
- avoid framing the issue merely as an excuse for incomplete work;
- record the eventual professor/AirGPU responses and update this evidence chain accordingly.

## 10. Immediate next decision gate

No simulator-dependent development should resume until at least one of the following produces a credible path:

1. the professor identifies a supported workaround or known cause;
2. AirGPU restores/clarifies reliable remote desktop access;
3. a different execution environment is selected based on evidence, cost, and compatibility.

Once a stable simulator environment is available, resume from **Step 2 full-maze validation**. Do not skip directly to Step 4, Step 5, Step 6, or Step 7.
