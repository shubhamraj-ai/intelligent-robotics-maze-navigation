# Step 4 Vision-Pipeline Isolation — 2026-11-03

## Status

Step 2 manual control remains the last reproducibly stable runtime path. On AirGPU, the event-driven/state-change controller completed two full-maze traversals using the accepted motion profile:

- forward speed: 1.00
- turn inner speed: 0.10
- turn outer speed: 1.00

Step 4 remains blocked by CoppeliaSim instability when vision-data acquisition is added.

## Evidence accumulated

The following Step 4 variants were exercised and did not provide a stable full traversal:

1. External ZeroMQ vision-image retrieval at higher capture rates.
2. Reduced-rate image retrieval.
3. Uniform 1 Hz image capture.
4. Uniform 0.5 Hz image capture.
5. State-change-only motor RPC writes.
6. Delayed capture after a stable command.
7. Synchronized/stepping simulation.
8. Remote simIM image read/write, which removed raw image-buffer transfer to Python.

The latest AirGPU failure occurred immediately after motion commenced even with synchronized 0.5 Hz capture and simIM-based image handling.

## Current conclusion

The evidence no longer supports treating capture frequency alone as the primary failure mechanism.

It also weakens the hypothesis that the Lenovo laptop's age/performance is the sole cause, because the same class of failure has been reproduced on the AirGPU machine.

The strongest remaining isolation boundary is the vision-data pipeline itself.

## Next controlled experiment

Move all camera acquisition and JPEG writing into a temporary CoppeliaSim Lua simulation script.

Python responsibilities are restricted to:

- W/A/D keyboard events;
- state-change-only motor commands;
- synchronized simulation stepping;
- a tiny string signal containing the active label.

Python must not:

- resolve the camera object;
- call getVisionSensorImg;
- call simIM;
- receive image buffers;
- write camera images.

The Lua simulation script performs:

- camera resolution inside CoppeliaSim;
- vision-sensor image read;
- JPEG save directly to the dataset path.

The experiment begins with an automatic stationary capture probe before any wheel motion. This provides two outcomes:

- stationary probe fails/crashes: the camera/script path itself is implicated;
- stationary probe passes but motion later crashes: interaction between vision processing and moving simulation state remains implicated.

Only after the stationary probe passes should a short first-turn stress test be attempted.

## Preservation rule

Do not alter the accepted motion profile while running this isolation experiment. Do not replace the maze scene or camera object in the same experiment. Those are separate variables and should be tested only if the in-scene capture architecture still fails.
