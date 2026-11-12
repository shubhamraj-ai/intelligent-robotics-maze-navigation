from pathlib import Path
from datetime import datetime, timezone
import threading
import time

import cv2
import numpy as np

# Wheel speeds used for forward motion and smooth curved turns.
FORWARD_SPEED = 1.0
TURN_OUTER_SPEED = 1.0
TURN_INNER_SPEED = 0.10

# Motor control runs at 20 Hz. Camera updates are limited to 5 Hz to reduce the load on CoppeliaSim during continuous driving.
CONTROL_INTERVAL = 0.05
CAMERA_INTERVAL = 0.20

# Wait for a stable movement command before saving an image, and avoid collecting too many nearly identical frames.
MIN_STABLE_SECONDS = 0.75
SAVE_INTERVAL_SECONDS = 2.00

# Save the dataset beside this script so the program remains portable.
OUTPUT_FOLDER = Path(__file__).resolve().parent / "recordedimages"


# Track which W/A/D movement key is currently being held.
class KeyState:
    def __init__(self):
        self.held = set()
        self.lock = threading.Lock()

    def handle(self, event):
        key = (getattr(event, "name", "") or "").lower()
        if key not in {"w", "a", "d"}:
            return
        with self.lock:
            if event.event_type == "down":
                self.held.add(key)
            elif event.event_type == "up":
                self.held.discard(key)

    def snapshot(self):
        with self.lock:
            return set(self.held)


# Convert one valid W/A/D key press into a label and wheel speeds. Conflicting or missing movement keys stop the robot.
def command(keys):
    active = [key for key in ("w", "a", "d") if key in keys]
    if len(active) != 1:
        return "", 0.0, 0.0

    if active[0] == "w":
        return "forward", FORWARD_SPEED, FORWARD_SPEED
    if active[0] == "a":
        return "left", TURN_INNER_SPEED, TURN_OUTER_SPEED
    return "right", TURN_OUTER_SPEED, TURN_INNER_SPEED


# Send the selected wheel velocities to the PioneerP3DX motors.
def setmotors(sim, leftmotor, rightmotor, leftspeed, rightspeed):
    sim.setJointTargetVelocity(leftmotor, float(leftspeed))
    sim.setJointTargetVelocity(rightmotor, float(rightspeed))


# Read the robot camera through ZMQ and convert it to OpenCV format.
def getframe(sim, camera):
    image, resolution = sim.getVisionSensorImg(camera)
    width, height = resolution
    frame = np.frombuffer(image, dtype=np.uint8).reshape(height, width, 3)
    frame = cv2.flip(frame, 0)
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


# Store each labelled training image in grayscale for the dataset.
def saveimage(frame, filename):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if not cv2.imwrite(str(filename), gray):
        raise RuntimeError(f"Could not save camera image: {filename}")


def main():
    try:
        import keyboard
        from coppeliasim_zmqremoteapi_client import RemoteAPIClient
    except ImportError as error:
        print("Install the required Python packages before running:", error)
        return 1

    for label in ("forward", "left", "right"):
        (OUTPUT_FOLDER / label).mkdir(parents=True, exist_ok=True)

    # Connect external Python to CoppeliaSim through the ZMQ Remote API.
    client = RemoteAPIClient()
    sim = client.require("sim")

    if sim.getSimulationState() != sim.simulation_stopped:
        raise RuntimeError("Stop the CoppeliaSim simulation before starting this program.")

    # Get references to the robot, camera and drive motors in the scene.
    robot = sim.getObject("/PioneerP3DX")
    camera = sim.getObject("/PioneerP3DX/cam1")
    leftmotor = sim.getObject("/PioneerP3DX/leftMotor")
    rightmotor = sim.getObject("/PioneerP3DX/rightMotor")

    if min(robot, camera, leftmotor, rightmotor) < 0:
        raise RuntimeError("Could not find the PioneerP3DX objects.")

    # Keep track of the recording session, labels and capture timing.
    session = datetime.now(timezone.utc).strftime("session_%Y%m%d_%H%M%S")
    counters = {"forward": 0, "left": 0, "right": 0}
    lastcapture = {"forward": None, "left": None, "right": None}
    lastlabel = ""
    labelsince = 0.0
    frame = None
    nextcamera = 0.0

    keys = KeyState()
    hook = keyboard.hook(keys.handle)

    # Stepping mode lets the external Python program control simulation progress.
    sim.setStepping(True)
    sim.startSimulation()

    print("W = forward, A = left, D = right")
    print("Release the key to stop. Press Ctrl+C to finish.")
    print("The robot camera is shown in the OpenCV window.")
    print("Images are stored in forward, left and right folders.")

    try:
        # Main loop: drive the robot, update the camera and record labelled images.
        while True:
            started = time.monotonic()

            label, leftspeed, rightspeed = command(keys.snapshot())
            setmotors(sim, leftmotor, rightmotor, leftspeed, rightspeed)
            sim.step()

            now = sim.getSimulationTime()

            # Update the OpenCV preview at 5 Hz rather than every control step.
            if now >= nextcamera:
                frame = getframe(sim, camera)
                cv2.imshow("PioneerP3DX camera", frame)
                nextcamera = now + CAMERA_INTERVAL

            cv2.waitKey(1)

            # Start timing again whenever the movement label changes.
            if label != lastlabel:
                lastlabel = label
                labelsince = now

            # Save only after the same movement command has remained stable.
            elif label and now - labelsince >= MIN_STABLE_SECONDS:
                previous = lastcapture[label]

                if frame is not None and (previous is None or now - previous >= SAVE_INTERVAL_SECONDS):
                    counters[label] += 1
                    filename = OUTPUT_FOLDER / label / (
                        f"{session}__{label}_{counters[label]:06d}.jpg"
                    )
                    saveimage(frame, filename)
                    lastcapture[label] = now
                    print("Saved:", filename.name)

            # Keep the motor-control loop close to the selected 20 Hz rate.
            remaining = CONTROL_INTERVAL - (time.monotonic() - started)
            if remaining > 0:
                time.sleep(remaining)

    except KeyboardInterrupt:
        pass

    finally:
        # Always stop the robot, camera window and simulation cleanly on exit.
        keyboard.unhook(hook)
        cv2.destroyAllWindows()

        try:
            setmotors(sim, leftmotor, rightmotor, 0.0, 0.0)
            if sim.getSimulationState() != sim.simulation_stopped:
                sim.step()
                sim.stopSimulation()
                time.sleep(0.2)
        finally:
            sim.setStepping(False)

    print("Recording finished:", OUTPUT_FOLDER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
