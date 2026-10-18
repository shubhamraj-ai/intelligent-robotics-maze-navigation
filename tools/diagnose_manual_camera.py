"""Manual-control + raw camera-acquisition crash diagnostic.

Human W/A/D controls the PioneerP3DX. The script also fetches the raw 50x50 RGB
vision-sensor frame. It deliberately excludes OpenCV display, TensorFlow, and
CNN inference so those layers remain isolated.
"""

import sys
import time

import keyboard
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

FORWARD_SPEED = 2.0
TURN_SPEED = 2.0
LOOP_INTERVAL_SECONDS = 0.10
CAMERA_PATH = "/PioneerP3DX/cam1"


def get_wheel_velocities():
    if keyboard.is_pressed("w"):
        return "forward", FORWARD_SPEED, FORWARD_SPEED
    if keyboard.is_pressed("a"):
        return "left", -TURN_SPEED, TURN_SPEED
    if keyboard.is_pressed("d"):
        return "right", TURN_SPEED, -TURN_SPEED
    return "none", 0.0, 0.0


def stop_motors(sim, left_motor, right_motor):
    for motor in (left_motor, right_motor):
        if motor is None:
            continue
        try:
            sim.setJointTargetVelocity(motor, 0.0)
        except Exception:
            pass


def main():
    print("MANUAL + CAMERA ACQUISITION DIAGNOSTIC", flush=True)
    print("W=forward, A=left, D=right.", flush=True)
    print("Raw camera acquisition ON; OpenCV/TensorFlow/CNN OFF.", flush=True)

    sim = None
    left_motor = right_motor = None

    try:
        client = RemoteAPIClient()
        sim = client.require("sim")
        left_motor = sim.getObject("/PioneerP3DX/leftMotor")
        right_motor = sim.getObject("/PioneerP3DX/rightMotor")
        camera = sim.getObject(CAMERA_PATH)

        loops = 0
        started = time.monotonic()
        first_resolution = None
        print("READY", flush=True)

        while True:
            loop_started = time.monotonic()
            command, left_velocity, right_velocity = get_wheel_velocities()

            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)

            raw_image, resolution = sim.getVisionSensorImg(camera)
            if len(resolution) != 2:
                raise RuntimeError(f"bad resolution: {resolution}")
            expected = resolution[0] * resolution[1] * 3
            if len(raw_image) != expected:
                raise RuntimeError(
                    f"bad frame bytes: got={len(raw_image)} expected={expected}"
                )
            if first_resolution is None:
                first_resolution = tuple(resolution)
            elif tuple(resolution) != first_resolution:
                raise RuntimeError(
                    f"resolution changed: first={first_resolution} now={resolution}"
                )

            loops += 1
            if loops == 1 or loops % 50 == 0:
                elapsed = time.monotonic() - started
                print(
                    f"alive t={elapsed:.1f}s loops={loops} command={command} "
                    f"res={resolution}",
                    flush=True,
                )

            remaining = LOOP_INTERVAL_SECONDS - (time.monotonic() - loop_started)
            if remaining > 0:
                time.sleep(remaining)

    except KeyboardInterrupt:
        print("STOPPED BY USER", flush=True)
    except Exception as error:
        print(
            f"DIAGNOSTIC ERROR: {type(error).__name__}: {error}",
            file=sys.stderr,
            flush=True,
        )
        return 1
    finally:
        if sim is not None:
            stop_motors(sim, left_motor, right_motor)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
