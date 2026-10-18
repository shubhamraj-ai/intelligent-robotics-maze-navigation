"""Step-2 control-rate diagnostic.

This intentionally mirrors src/step02_manual_control/manual_control.py and changes
only the control-loop interval supplied by --interval. It uses no camera,
OpenCV, TensorFlow, CNN inference, or pose telemetry.
"""

import argparse
import sys
import time

import keyboard
from coppeliasim_zmqremoteapi_client import RemoteAPIClient


FORWARD_SPEED = 2.0
TURN_SPEED = 2.0


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=float, default=0.10)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("--interval must be > 0")
    return args


def get_wheel_velocities():
    # Deliberately identical key-priority semantics to the original Step-2 script.
    if keyboard.is_pressed("w"):
        return FORWARD_SPEED, FORWARD_SPEED
    if keyboard.is_pressed("a"):
        return -TURN_SPEED, TURN_SPEED
    if keyboard.is_pressed("d"):
        return TURN_SPEED, -TURN_SPEED
    return 0.0, 0.0


def stop_motors(sim, left_motor, right_motor):
    for motor in (left_motor, right_motor):
        if motor is None:
            continue
        try:
            sim.setJointTargetVelocity(motor, 0.0)
        except Exception:
            pass


def main():
    args = parse_args()
    print("STEP-2 CONTROL-RATE DIAGNOSTIC", flush=True)
    print(f"interval={args.interval:.3f}s", flush=True)
    print("W=forward, A=left, D=right.", flush=True)
    print("No camera/OpenCV/TensorFlow/CNN/pose telemetry.", flush=True)

    sim = None
    left_motor = None
    right_motor = None

    try:
        client = RemoteAPIClient()
        sim = client.require("sim")
        left_motor = sim.getObject("/PioneerP3DX/leftMotor")
        right_motor = sim.getObject("/PioneerP3DX/rightMotor")
        print("READY", flush=True)

        loops = 0
        started = time.monotonic()
        while True:
            left_velocity, right_velocity = get_wheel_velocities()
            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)
            loops += 1
            if loops % max(1, round(5.0 / args.interval)) == 0:
                elapsed = time.monotonic() - started
                print(f"alive t={elapsed:.1f}s loops={loops}", flush=True)
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("STOPPED BY USER", flush=True)
    except Exception as error:
        print(f"DIAGNOSTIC ERROR: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        return 1
    finally:
        if sim is not None:
            stop_motors(sim, left_motor, right_motor)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
