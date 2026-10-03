"""Drive the PioneerP3DX manually with the W, A, and D keys."""

import sys
import time

import keyboard
from coppeliasim_zmqremoteapi_client import RemoteAPIClient


FORWARD_SPEED = 2.0
TURN_SPEED = 2.0
CONTROL_INTERVAL_SECONDS = 0.05


def get_wheel_velocities():
    """Return the wheel velocities for the currently held driving key."""
    if keyboard.is_pressed("w"):
        return FORWARD_SPEED, FORWARD_SPEED
    if keyboard.is_pressed("a"):
        return -TURN_SPEED, TURN_SPEED
    if keyboard.is_pressed("d"):
        return TURN_SPEED, -TURN_SPEED
    return 0.0, 0.0


def stop_motors(sim, left_motor, right_motor):
    """Try each motor independently so both receive a stop command."""
    cleanup_succeeded = True

    for motor in (left_motor, right_motor):
        if motor is None:
            continue
        try:
            sim.setJointTargetVelocity(motor, 0.0)
        except Exception as error:
            cleanup_succeeded = False
            print(f"STEP 2 CLEANUP ERROR: Could not stop a motor: {error}", file=sys.stderr)

    return cleanup_succeeded


def main():
    print("STEP 2 — Manual Robot Control")
    print("W - Forward")
    print("A - Left")
    print("D - Right")

    sim = None
    left_motor = None
    right_motor = None
    exit_status = 0

    try:
        try:
            client = RemoteAPIClient()
            sim = client.require("sim")
        except Exception as error:
            raise RuntimeError(
                f"Could not connect to the CoppeliaSim ZMQ Remote API: {error}"
            ) from error

        required_paths = (
            "/PioneerP3DX",
            "/PioneerP3DX/leftMotor",
            "/PioneerP3DX/rightMotor",
        )
        object_handles = {}

        for object_path in required_paths:
            try:
                object_handle = sim.getObject(object_path)
                if object_handle == -1:
                    raise RuntimeError("CoppeliaSim returned an invalid object handle")
            except Exception as error:
                raise RuntimeError(
                    f"Could not resolve scene object {object_path}: {error}"
                ) from error
            object_handles[object_path] = object_handle

            if object_path == "/PioneerP3DX/leftMotor":
                left_motor = object_handle
            elif object_path == "/PioneerP3DX/rightMotor":
                right_motor = object_handle

        while True:
            left_velocity, right_velocity = get_wheel_velocities()
            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)
            time.sleep(CONTROL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f"STEP 2 ERROR: {error}", file=sys.stderr)
        exit_status = 1
    finally:
        if sim is not None and not stop_motors(sim, left_motor, right_motor):
            exit_status = 1

    return exit_status


if __name__ == "__main__":
    sys.exit(main())
