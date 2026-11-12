"""Final neural-network navigation controller for the PioneerP3DX."""

from collections import deque
from pathlib import Path
import time

import cv2
import numpy as np
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
from tensorflow.keras.models import load_model

MODEL_FILE = Path(__file__).resolve().with_name("network.h5")

LABELS = ("forward", "left", "right")

FORWARD_SPEED = 1.0
TURN_OUTER_SPEED = 1.0
TURN_INNER_SPEED = 0.10

FORWARD_PULSE = 0.50
TURN_PULSE = 0.50

SPATIAL_HISTORY = 6
SPATIAL_THRESHOLD = -0.05
BRIGHT_THRESHOLD = 0.62

MIN_RIGHT_PULSES = 10
MAX_RIGHT_PULSES = 11
RELEASE_FORWARD_THRESHOLD = 0.55

REARM_FORWARD_THRESHOLD = 0.55
EVENT2_REARM_FRAMES = 3
EVENT4_REARM_FRAMES = 3

LEFT_PHASE_STREAK = 6
CORRIDOR4_FORWARD_FRAMES = 4

CORRIDOR3_CLEARANCE_SPATIAL = 0.48
CORRIDOR3_CLEARANCE_CENTER = 0.68
CORRIDOR3_EMERGENCY_CENTER = 0.26
CORRIDOR3_EMERGENCY_SPATIAL = 0.35

TERMINAL_ARM_FORWARD_FRAMES = 4
TERMINAL_BRIGHT_PIXEL = 0.60
TERMINAL_CENTER_BRIGHT = 0.30
TERMINAL_PREVIOUS_BRIGHT = 0.36
TERMINAL_FORWARD_THRESHOLD = 0.60
TERMINAL_SPATIAL_THRESHOLD = 0.12

MAX_PULSES = 560
MAX_CORRIDOR5_PULSES = 130


def getframe(sim, camera):
    image, resolution = sim.getVisionSensorImg(camera)
    width, height = resolution
    frame = np.frombuffer(image, dtype=np.uint8).reshape(height, width, 3)
    frame = cv2.flip(frame, 0)
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


def predict(model, frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (50, 50))
    vector = gray.astype(np.float32).reshape(1, -1) / 255.0
    probabilities = model(vector, training=False).numpy()[0]
    index = int(np.argmax(probabilities))
    return LABELS[index], probabilities


def spatialvalue(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    height, width = gray.shape
    region = gray[int(height * 0.40):, :]
    third = width // 3
    left = np.mean(region[:, :third] > BRIGHT_THRESHOLD)
    right = np.mean(region[:, 2 * third:] > BRIGHT_THRESHOLD)
    return float(right - left)


def centerbrightness(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    height, width = gray.shape
    y0 = int(height * 0.50)
    x0 = int(width * 0.30)
    x1 = int(width * 0.70)
    return float(np.mean(gray[y0:, x0:x1] > TERMINAL_BRIGHT_PIXEL))


def wheelcommand(label):
    if label == "forward":
        return FORWARD_SPEED, FORWARD_SPEED
    if label == "left":
        return TURN_INNER_SPEED, TURN_OUTER_SPEED
    if label == "right":
        return TURN_OUTER_SPEED, TURN_INNER_SPEED
    return 0.0, 0.0


def setmotors(sim, leftmotor, rightmotor, leftspeed, rightspeed):
    sim.setJointTargetVelocity(leftmotor, float(leftspeed))
    sim.setJointTargetVelocity(rightmotor, float(rightspeed))


def move(sim, leftmotor, rightmotor, label):
    leftspeed, rightspeed = wheelcommand(label)
    setmotors(sim, leftmotor, rightmotor, leftspeed, rightspeed)
    time.sleep(FORWARD_PULSE if label == "forward" else TURN_PULSE)
    setmotors(sim, leftmotor, rightmotor, 0.0, 0.0)


def main():
    if not MODEL_FILE.is_file():
        raise FileNotFoundError(f"network.h5 was not found beside navigation.py: {MODEL_FILE}")

    model = load_model(MODEL_FILE, compile=False)

    client = RemoteAPIClient()
    sim = client.require("sim")

    if sim.getSimulationState() == sim.simulation_stopped:
        raise RuntimeError("Start the CoppeliaSim simulation before running navigation.py.")

    robot = sim.getObject("/PioneerP3DX")
    camera = sim.getObject("/PioneerP3DX/cam1")
    leftmotor = sim.getObject("/PioneerP3DX/leftMotor")
    rightmotor = sim.getObject("/PioneerP3DX/rightMotor")

    if min(robot, camera, leftmotor, rightmotor) < 0:
        raise RuntimeError("Could not find the PioneerP3DX objects.")

    setmotors(sim, leftmotor, rightmotor, 0.0, 0.0)

    history = deque(maxlen=SPATIAL_HISTORY)
    previous = None
    previous2 = None

    rightevents = 0
    turning = False
    rightpulses = 0
    armed = True
    rearmcount = 0

    leftphaseseen = False
    leftstreak = 0
    corridor4forward = 0

    terminalarmed = False
    terminalforward = 0
    terminalprevious = None
    corridor5pulses = 0

    print("Neural navigation started.")
    print("The network predicts forward, left and right from the camera.")
    print("Press Ctrl+C if manual stopping is required.")

    try:
        for pulse in range(1, MAX_PULSES + 1):
            if sim.getSimulationState() == sim.simulation_stopped:
                raise RuntimeError("The CoppeliaSim simulation stopped.")

            frame = getframe(sim, camera)
            raw, probabilities = predict(model, frame)
            forward, left, right = [float(value) for value in probabilities]

            spatial = spatialvalue(frame)
            centre = centerbrightness(frame)
            prior = float(np.mean(history)) if len(history) == SPATIAL_HISTORY else float("nan")

            if rightevents == 4 and not turning:
                if not terminalarmed:
                    if raw == "forward" and forward >= REARM_FORWARD_THRESHOLD:
                        terminalforward += 1
                        if terminalforward >= TERMINAL_ARM_FORWARD_FRAMES:
                            terminalarmed = True
                            print(f"Terminal detector armed at pulse {pulse}.")
                    else:
                        terminalforward = 0
                else:
                    terminal = (
                        terminalprevious is not None
                        and centre <= TERMINAL_CENTER_BRIGHT
                        and terminalprevious <= TERMINAL_PREVIOUS_BRIGHT
                        and forward <= TERMINAL_FORWARD_THRESHOLD
                        and abs(spatial) <= TERMINAL_SPATIAL_THRESHOLD
                    )
                    if terminal:
                        setmotors(sim, leftmotor, rightmotor, 0.0, 0.0)
                        position = sim.getObjectPosition(robot, sim.handle_world)
                        orientation = sim.getObjectOrientation(robot, sim.handle_world)
                        print("Terminal wall detected. Navigation complete.")
                        print(
                            f"Final pose: x={position[0]:.4f}, y={position[1]:.4f}, "
                            f"yaw={orientation[2]:.4f}"
                        )
                        return 0

            normaltrigger = (
                armed
                and not turning
                and rightevents < 4
                and raw == "left"
                and previous == "forward"
                and len(history) == SPATIAL_HISTORY
                and prior > SPATIAL_THRESHOLD
            )

            event2trigger = (
                armed
                and not turning
                and rightevents == 1
                and raw == "left"
                and previous == "right"
                and previous2 == "forward"
                and len(history) == SPATIAL_HISTORY
                and prior > SPATIAL_THRESHOLD
                and abs(spatial) <= 0.12
                and centre <= 0.34
            )

            trigger = normaltrigger or event2trigger

            if turning:
                if rightpulses < MIN_RIGHT_PULSES:
                    rightpulses += 1
                    applied = "right"
                elif raw == "forward" and forward >= RELEASE_FORWARD_THRESHOLD:
                    turning = False
                    rightevents += 1
                    rightpulses = 0
                    armed = False
                    rearmcount = 0
                    applied = "forward"
                    print(f"Right turn {rightevents} completed at pulse {pulse}.")

                    if rightevents == 2:
                        leftphaseseen = False
                        leftstreak = 0
                        corridor4forward = 0
                    elif rightevents == 4:
                        terminalarmed = False
                        terminalforward = 0
                        terminalprevious = None
                        corridor5pulses = 0

                elif rightpulses < MAX_RIGHT_PULSES:
                    rightpulses += 1
                    applied = "right"
                else:
                    setmotors(sim, leftmotor, rightmotor, 0.0, 0.0)
                    raise RuntimeError("A committed right turn reached its safety limit.")

            elif trigger:
                turning = True
                armed = False
                rearmcount = 0
                rightpulses = 1
                applied = "right"
                print(f"Right turn {rightevents + 1} started at pulse {pulse}.")

            else:
                emergency = (
                    rightevents == 2
                    and not leftphaseseen
                    and centre <= CORRIDOR3_EMERGENCY_CENTER
                    and spatial >= CORRIDOR3_EMERGENCY_SPATIAL
                )

                if emergency:
                    setmotors(sim, leftmotor, rightmotor, 0.0, 0.0)
                    raise RuntimeError("Corridor 3 wall safety stop.")

                clearance = (
                    rightevents == 2
                    and not leftphaseseen
                    and spatial >= CORRIDOR3_CLEARANCE_SPATIAL
                    and centre <= CORRIDOR3_CLEARANCE_CENTER
                    and raw in ("forward", "right")
                )

                applied = "right" if clearance else raw

                if rightevents in (1, 3) and not armed:
                    if raw == "forward" and forward >= REARM_FORWARD_THRESHOLD:
                        rearmcount += 1
                        needed = EVENT2_REARM_FRAMES if rightevents == 1 else EVENT4_REARM_FRAMES
                        if rearmcount >= needed:
                            armed = True
                    else:
                        rearmcount = 0

                elif rightevents == 2 and not armed:
                    if not leftphaseseen:
                        if raw == "left":
                            leftstreak += 1
                            if leftstreak >= LEFT_PHASE_STREAK:
                                leftphaseseen = True
                                corridor4forward = 0
                        else:
                            leftstreak = 0
                    else:
                        if raw == "forward" and forward >= REARM_FORWARD_THRESHOLD:
                            corridor4forward += 1
                            if corridor4forward >= CORRIDOR4_FORWARD_FRAMES:
                                armed = True
                                rearmcount = 0
                        else:
                            corridor4forward = 0

            move(sim, leftmotor, rightmotor, applied)

            if rightevents == 4:
                corridor5pulses += 1
                if corridor5pulses >= MAX_CORRIDOR5_PULSES:
                    raise RuntimeError("Final corridor safety limit reached.")

            position = sim.getObjectPosition(robot, sim.handle_world)
            orientation = sim.getObjectOrientation(robot, sim.handle_world)

            print(
                f"Pulse {pulse}: predicted={raw}, applied={applied}, "
                f"F={forward:.3f}, L={left:.3f}, R={right:.3f}, "
                f"x={position[0]:.3f}, y={position[1]:.3f}, yaw={orientation[2]:.3f}"
            )

            history.append(spatial)
            previous2 = previous
            previous = raw

            if rightevents == 4:
                terminalprevious = centre

        raise RuntimeError("Maximum pulse limit reached before terminal stop.")

    except KeyboardInterrupt:
        print("Navigation interrupted by user.")
        return 130
    finally:
        setmotors(sim, leftmotor, rightmotor, 0.0, 0.0)


if __name__ == "__main__":
    raise SystemExit(main())
