"""Crash-diagnostic manual route logger for Step 2.

Human W/A/D controls the PioneerP3DX. No camera, OpenCV, TensorFlow, or CNN is used.
Each control sample is flushed to CSV so the last known pose survives a simulator crash.
"""

import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import keyboard
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

FORWARD_SPEED = 2.0
TURN_SPEED = 2.0
CONTROL_INTERVAL_SECONDS = 0.05
ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "diagnostic_logs_step2"


def command_from_keyboard():
    held = [key for key in ("w", "a", "d") if keyboard.is_pressed(key)]
    if len(held) != 1:
        return "none", 0.0, 0.0
    if held[0] == "w":
        return "forward", FORWARD_SPEED, FORWARD_SPEED
    if held[0] == "a":
        return "left", -TURN_SPEED, TURN_SPEED
    return "right", TURN_SPEED, -TURN_SPEED


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    csv_path = LOG_DIR / f"step2_route_{stamp}.csv"

    print("STEP-2 ROUTE CRASH DIAGNOSTIC", flush=True)
    print("W=forward, A=left, D=right; human controls motors.", flush=True)
    print("No camera/OpenCV/TensorFlow/CNN is active.", flush=True)
    print(f"CSV: {csv_path}", flush=True)

    sim = None
    left_motor = right_motor = robot = None
    handle = None

    try:
        client = RemoteAPIClient()
        sim = client.require("sim")
        robot = sim.getObject("/PioneerP3DX")
        left_motor = sim.getObject("/PioneerP3DX/leftMotor")
        right_motor = sim.getObject("/PioneerP3DX/rightMotor")

        handle = csv_path.open("w", newline="", encoding="utf-8")
        writer = csv.writer(handle)
        writer.writerow([
            "utc_timestamp", "elapsed_s", "command",
            "left_velocity", "right_velocity",
            "x", "y", "yaw", "sim_state"
        ])
        handle.flush()

        started = time.monotonic()
        sample = 0

        while True:
            loop_started = time.monotonic()
            command, left_velocity, right_velocity = command_from_keyboard()

            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)

            position = sim.getObjectPosition(robot, sim.handle_world)
            yaw = sim.getObjectOrientation(robot, sim.handle_world)[2]
            state = sim.getSimulationState()
            elapsed = time.monotonic() - started

            writer.writerow([
                datetime.now(timezone.utc).isoformat(),
                f"{elapsed:.3f}",
                command,
                f"{left_velocity:.3f}",
                f"{right_velocity:.3f}",
                f"{position[0]:.6f}",
                f"{position[1]:.6f}",
                f"{yaw:.6f}",
                state,
            ])
            handle.flush()

            sample += 1
            if sample == 1 or sample % 20 == 0:
                print(
                    f"t={elapsed:.1f}s command={command:<7} "
                    f"x={position[0]:.3f} y={position[1]:.3f} yaw={yaw:.3f} state={state}",
                    flush=True,
                )

            remaining = CONTROL_INTERVAL_SECONDS - (time.monotonic() - loop_started)
            if remaining > 0:
                time.sleep(remaining)

    except KeyboardInterrupt:
        print("DIAGNOSTIC STOPPED BY USER", flush=True)
    except Exception as error:
        print(f"DIAGNOSTIC ERROR: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        return 1
    finally:
        if sim is not None:
            for motor in (left_motor, right_motor):
                if motor is not None:
                    try:
                        sim.setJointTargetVelocity(motor, 0.0)
                    except Exception:
                        pass
        if handle is not None:
            handle.close()
        print(f"DIAGNOSTIC LOG PRESERVED: {csv_path}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
