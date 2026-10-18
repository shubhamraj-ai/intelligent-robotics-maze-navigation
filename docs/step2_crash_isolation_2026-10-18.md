# Step-2 crash isolation — 2026-10-18

## Observations

1. CoppeliaSim-only baseline: stable.
2. Persistent ZMQ connection-only test for 60 seconds: PASS.
   - 109 samples
   - simulation remained running
   - no motor commands were sent
3. Original Step-2 manual controller (50 ms nominal loop): CoppeliaSim crashed during manual driving before the second/right-turn area.
   - fresh Windows Application Error at 15:42:29 local time
   - coppeliaSim.exe
   - ntdll.dll
   - exception 0xc0000374
4. Route diagnostic with motor commands plus pose/state logging: stable past the prior crash area and through subsequent turns.
   - 2,551 samples over ~249 s before diagnostic stop
   - 772 moving samples
   - commands: forward 683, left 35, right 54
   - actual mean sample interval ~97.7 ms, median ~94 ms
   - no new CoppeliaSim crash event during this run

## Current interpretation

The crash is intermittent rather than deterministically tied to the second-turn maze location.

Persistent ZMQ connectivity alone is not sufficient to trigger the failure.

The stable route diagnostic operated at roughly 10 Hz, while the original Step-2 controller targets a 50 ms / ~20 Hz loop. Control-call cadence is therefore a useful next variable to isolate, but it is not yet proven to be the root cause.

## Next controlled test

Use tools/diagnose_step2_rate.py with --interval 0.10.

The script intentionally mirrors the original Step-2 motor-control logic and key priority while changing only the control-loop interval. It has no camera, OpenCV, TensorFlow, CNN inference, or pose telemetry.

If the 100 ms version is stable through the route where the 50 ms version crashed, repeat evidence before modifying the academic Step-2 controller.

Autonomous Step 6 remains blocked.
