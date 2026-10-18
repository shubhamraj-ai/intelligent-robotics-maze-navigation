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


## 100 ms control-rate result

The explicit `--interval 0.10` Step-2 rate diagnostic remained stable past the previous failure area.

Observed process evidence:
- at least 2,200 control loops completed
- approximately 307 seconds of runtime before the diagnostic controller was stopped
- CoppeliaSim process remained alive
- no new CoppeliaSim Application Error / Windows Error Reporting crash event occurred during this run

This strengthens, but does not yet prove, the hypothesis that the failure may be control-rate sensitive. The next controlled A/B check is to run the same diagnostic script with `--interval 0.05` from a clean scene reset. If the 50 ms variant reproduces the crash while the 100 ms variant remains stable, the control-call cadence hypothesis becomes substantially stronger. If 50 ms also remains stable, the crash should be treated as intermittent and another variable must be isolated.


## 50 ms A/B comparison result

The same control-rate diagnostic also remained stable with `--interval 0.05` past the prior failure area.

Observed process evidence:
- at least 2,700 control loops completed
- approximately 249 seconds of runtime before cleanup
- CoppeliaSim remained alive
- no new CoppeliaSim crash event occurred during this run

This materially weakens the simple control-rate hypothesis. The 50 ms cadence alone is not sufficient to reproduce the crash.

Current interpretation: the CoppeliaSim `0xc0000374` failure is intermittent. It is not deterministically tied to the second-turn maze location, persistent ZMQ connectivity, or 50 ms motor-command cadence.

The next isolation layer is vision-sensor acquisition without motor control, OpenCV display, TensorFlow, or CNN inference. If that is stable, the next combined diagnostic should add manual motor control plus camera acquisition while still excluding TensorFlow/CNN inference.
