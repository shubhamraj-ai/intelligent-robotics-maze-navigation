"""Record labelled camera images during W/A/D manual navigation."""

import sys
import time
from datetime import datetime, timezone
from pathlib import Path


FORWARD_SPEED = 2.0
TURN_SPEED = 2.0
SAVE_INTERVAL_SECONDS = 0.10
DATASET_PATH = Path(__file__).resolve().parents[2] / "dataset"
CAMERA_PATH = "/PioneerP3DX/cam1"


def get_command(keyboard):
    """Take one key snapshot; ambiguous input must stop the robot."""
    held_keys = [key for key in ("w", "a", "d") if keyboard.is_pressed(key)]
    if len(held_keys) != 1:
        return None, 0.0, 0.0
    if held_keys[0] == "w":
        return "forward", FORWARD_SPEED, FORWARD_SPEED
    if held_keys[0] == "a":
        return "left", -TURN_SPEED, TURN_SPEED
    return "right", TURN_SPEED, -TURN_SPEED


def convert_image(raw_image, resolution, np, cv2):
    """Validate and convert CoppeliaSim's bottom-up RGB buffer to BGR."""
    if len(resolution) != 2:
        raise ValueError(f"Expected [width, height], received {resolution}")
    width, height = resolution
    if not all(isinstance(value, int) and value > 0 for value in resolution):
        raise ValueError(f"Camera resolution must contain positive integers: {resolution}")
    expected_bytes = width * height * 3
    if len(raw_image) != expected_bytes:
        raise ValueError(f"Expected {expected_bytes} RGB bytes, received {len(raw_image)}")
    frame = np.frombuffer(raw_image, dtype=np.uint8).reshape(height, width, 3)
    frame = cv2.flip(frame, 0)
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


def main():
    print("STEP 4 - Training Data Recording")
    print("W - Forward; A - Left; D - Right. Release keys to stop.")
    print("Start the simulation in CoppeliaSim; use terminal Ctrl+C to exit.")
    sim = None
    cv2 = None
    left_motor = None
    right_motor = None
    counters = {"forward": 0, "left": 0, "right": 0}
    last_save_time = None
    exit_status = 0

    try:
        import cv2
        import keyboard
        import numpy as np
        from coppeliasim_zmqremoteapi_client import RemoteAPIClient

        client = RemoteAPIClient()
        sim = client.require("sim")
        handles = {}
        for path in ("/PioneerP3DX", "/PioneerP3DX/leftMotor",
                     "/PioneerP3DX/rightMotor", CAMERA_PATH):
            handle = sim.getObject(path)
            if handle < 0:
                raise RuntimeError(f"Could not resolve scene object {path}")
            handles[path] = handle
            if path == "/PioneerP3DX/leftMotor":
                left_motor = handle
            elif path == "/PioneerP3DX/rightMotor":
                right_motor = handle

        for label in counters:
            (DATASET_PATH / label).mkdir(parents=True, exist_ok=True)

        while True:
            if sim.getSimulationState() in (sim.simulation_stopped, sim.simulation_paused):
                raise RuntimeError("Simulation is stopped or paused; start it in CoppeliaSim.")

            label, left_velocity, right_velocity = get_command(keyboard)
            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)
            raw_image, resolution = sim.getVisionSensorImg(handles[CAMERA_PATH])
            frame = convert_image(raw_image, resolution, np, cv2)
            cv2.imshow("PioneerP3DX Training Data", frame)
            cv2.waitKey(1)

            # Recheck keys after image acquisition so released/changed keys are not saved.
            current_label, left_velocity, right_velocity = get_command(keyboard)
            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)
            now = time.monotonic()
            if label is not None and current_label == label:
                if last_save_time is None or now - last_save_time >= SAVE_INTERVAL_SECONDS:
                    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                    counter = counters[label] + 1
                    filename = f"{label}_{timestamp}_{counter:06d}.jpg"
                    image_path = DATASET_PATH / label / filename
                    # Never overwrite a file from an earlier recording session.
                    while image_path.exists():
                        counter += 1
                        filename = f"{label}_{timestamp}_{counter:06d}.jpg"
                        image_path = DATASET_PATH / label / filename
                    if not cv2.imwrite(str(image_path), frame):
                        raise RuntimeError(f"Could not save image {image_path}")
                    counters[label] += 1
                    last_save_time = now
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f"STEP 4 ERROR: {error}", file=sys.stderr)
        exit_status = 1
    finally:
        if sim is not None:
            for motor in (left_motor, right_motor):
                if motor is not None:
                    try:
                        sim.setJointTargetVelocity(motor, 0.0)
                    except Exception as error:
                        print(f"STEP 4 CLEANUP ERROR: Could not stop a motor: {error}", file=sys.stderr)
                        exit_status = 1
        if cv2 is not None:
            try:
                cv2.destroyAllWindows()
            except Exception as error:
                print(f"STEP 4 CLEANUP ERROR: Could not close OpenCV windows: {error}", file=sys.stderr)
                exit_status = 1
        print("Saved images: " + ", ".join(f"{label}={count}" for label, count in counters.items()))

    return exit_status


if __name__ == "__main__":
    sys.exit(main())
