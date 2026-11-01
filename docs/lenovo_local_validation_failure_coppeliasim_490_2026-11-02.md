# Lenovo Local Validation Failure — CoppeliaSim 4.9.0 rev6

**Date:** 2026-11-02  
**Branch:** `step-05-06-simplified-baseline`

## Outcome

The validated state-change/event-driven Step-2 controller was tested again on the local Lenovo laptop using **CoppeliaSim Edu 4.9.0 rev6**, matching the AirGPU simulator version.

The short W/A/D smoke test passed.

During the first complete maze traversal, CoppeliaSim crashed shortly before the second turn.

Therefore:

> **The Lenovo local environment is not validated for sustained full-maze simulation, even with CoppeliaSim 4.9.0 rev6 and the validated state-change controller.**

AirGPU remains the validated simulator execution environment.

## Windows crash evidence

A post-crash capture from the Lenovo recorded:

- `Application Error`, Event ID 1000;
- faulting application: `coppeliaSim.exe`;
- faulting module: `ntdll.dll`;
- exception code: `0xc0000374`;
- Windows Error Reporting `APPCRASH`;
- a separate `FaultTolerantHeap` event.

The same exception code had also been recorded for the earlier CoppeliaSim 4.7.0 rev4 local crash.

Microsoft documents `0xc0000374` as `STATUS_HEAP_CORRUPTION`. A fault appearing in `ntdll.dll` does not by itself prove that `ntdll.dll` caused the corruption; Windows can detect corruption there after another module or component damaged process memory earlier.

## Local graphics environment observed

The Lenovo reported:

- NVIDIA GeForce GT 820M
  - driver version: 21.21.13.7654
  - driver date: 2016-12-29
- Intel HD Graphics Family
  - driver version: 20.19.15.4642
  - driver date: 2017-03-28

No display-driver event was recorded in the same short crash window.

These old drivers are a material environment difference from the AirGPU Tesla T4 system, but the available evidence does **not** prove that either graphics driver is the root cause.

## Revised interpretation

The controller change remains valid because:

- the original continuous polling/repeated-command controller crashed on AirGPU;
- controlled AirGPU tests A/B/C passed;
- the event-driven/state-change controller completed two full AirGPU traversals;
- Step 4 and Step 6 now suppress duplicate motor writes as a preventive design measure.

However, the local Lenovo crash with the same controller and the same CoppeliaSim 4.9.0 rev6 build means:

> **The controller architecture was one real stability factor, but it was not the only factor affecting the Lenovo.**

The local machine has an additional environment-specific instability that is not presently isolated.

## Project decision

Do not spend further project time repeatedly retrying CoppeliaSim on the Lenovo.

Use:

- **AirGPU** for simulator-dependent Step 4/Step 6 validation and data-generation sessions;
- **Lenovo** for repository work, code edits, tests, dataset inspection, training, documentation, and other non-simulator tasks where stable.

The local simulator issue may be investigated later as a separate environment/debugging task if project time permits, ideally with crash-dump analysis rather than repeated manual retries.

## Dependency status

Step 2 remains:

**PASS on AirGPU**

The validated dependency remains:

**Step 2 -> Step 4 fresh data -> Step 5 simple NN/perceptron -> Step 6 -> Step 7**

The Lenovo failure does not invalidate the AirGPU Step-2 result.
