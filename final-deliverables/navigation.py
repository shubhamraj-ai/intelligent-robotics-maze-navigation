from collections import deque
from pathlib import Path
import time

import cv2
import numpy as np
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
from tensorflow.keras.models import load_model

# Load the trained 3-classes NN from the same folder.
MODEL_FILE = Path(__file__).resolve().with_name("network.h5")
LABELS = ("forward", "left", "right")

# Wheel speeds and pulse duration for each autonomous movement.
FORWARD_SPEED = 1.0
TURN_OUTER_SPEED = 1.0
TURN_INNER_SPEED = 0.10
PULSE_SECONDS = 0.50

# Simple image-geometry constant values used only for the lightweight supervisory layer.
SPATIAL_HISTORY = 6
SPATIAL_THRESHOLD = -0.05
BRIGHT_THRESHOLD = 0.62

# Keep a detected right turn stable for a short bounded period, then re-arm after clear forward motion.
MIN_RIGHT_PULSES = 10
MAX_RIGHT_PULSES = 11
FORWARD_CONFIDENCE = 0.55
REARM_FRAMES = 3
NATURAL_RIGHT_STREAK = 6

# These counters help confirm the robot has cleared the left-turn section before looking for the next right turn.
LEFT_PHASE_STREAK = 6
AFTER_LEFT_FORWARD_FRAMES = 4

# Small corridor-clearance limits retained from the previously validated maze runs.
CLEARANCE_SPATIAL = 0.48
CLEARANCE_CENTER = 0.68
EMERGENCY_CENTER = 0.26
EMERGENCY_SPATIAL = 0.35

# Final-wall stopping is enabled only after the fourth right turn and a short stable forward motion.
TERMINAL_ARM_FRAMES = 4
TERMINAL_LEFT_FORWARD_MAX = 0.50

# Overall safety limits prevent the robot from continuing indefinitely if a run goes wrong.
MAX_PULSES = 560
MAX_FINAL_CORRIDOR_PULSES = 130


# Read one camera image from CoppeliaSim and convert it into OpenCV format.
def getframe(sim, camera):
    image, resolution = sim.getVisionSensorImg(camera)
    width, height = resolution
    frame = np.frombuffer(image, dtype=np.uint8).reshape(height, width, 3)
    frame = cv2.flip(frame, 0)
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


# Prepare the camera image exactly as used during training and return the NN prediction probabilities.
def predict(model, frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (50, 50))
    vector = gray.astype(np.float32).reshape(1, -1) / 255.0
    probabilities = model(vector, training=False).numpy()[0]
    return LABELS[int(np.argmax(probabilities))], probabilities


# Measure a simple left-versus-right brightness difference for the few ambiguous right-turns.
def imagefeatures(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    height, width = gray.shape

    lower = gray[int(height * 0.40):, :]
    third = width // 3
    left = np.mean(lower[:, :third] > BRIGHT_THRESHOLD)
    right = np.mean(lower[:, 2 * third:] > BRIGHT_THRESHOLD)
    spatial = float(right - left)

    center = gray[int(height * 0.50):, int(width * 0.30):int(width * 0.70)]
    centre = float(np.mean(center > 0.60))
    return spatial, centre


# Convert the selected forward/left/right label into the corresponding wheel speeds.
def wheelcommand(label):
    if label == "forward":
        return FORWARD_SPEED, FORWARD_SPEED
    if label == "left":
        return TURN_INNER_SPEED, TURN_OUTER_SPEED
    if label == "right":
        return TURN_OUTER_SPEED, TURN_INNER_SPEED
    return 0.0, 0.0


# Send wheel velocities to the PioneerP3DX drive motors.
def setmotors(sim, leftmotor, rightmotor, leftspeed, rightspeed):
    sim.setJointTargetVelocity(leftmotor, float(leftspeed))
    sim.setJointTargetVelocity(rightmotor, float(rightspeed))


# Apply one movement pulse, then stop the wheels before processing the next camera frame.
def move(sim, leftmotor, rightmotor, label):
    leftspeed, rightspeed = wheelcommand(label)
    setmotors(sim, leftmotor, rightmotor, leftspeed, rightspeed)
    time.sleep(PULSE_SECONDS)
    setmotors(sim, leftmotor, rightmotor, 0.0, 0.0)


def main():
    # The trained model file stays right beside navigation.py so the submission remains portable.
    if not MODEL_FILE.is_file():
        raise FileNotFoundError(f"network.h5 was not found beside navigation.py: {MODEL_FILE}")

    model = load_model(MODEL_FILE, compile=False)

    # Connect to the running CoppeliaSim scene through the ZMQ Remote API.
    client = RemoteAPIClient()
    sim = client.require("sim")

    if sim.getSimulationState() == sim.simulation_stopped:
        raise RuntimeError("Start the CoppeliaSim simulation before running navigation.py.")

    # Get the robot, camera and two wheel-motor objects from the maze scene.
    robot = sim.getObject("/PioneerP3DX")
    camera = sim.getObject("/PioneerP3DX/cam1")
    leftmotor = sim.getObject("/PioneerP3DX/leftMotor")
    rightmotor = sim.getObject("/PioneerP3DX/rightMotor")

    if min(robot, camera, leftmotor, rightmotor) < 0:
        raise RuntimeError("Could not find the PioneerP3DX objects.")

    setmotors(sim, leftmotor, rightmotor, 0.0, 0.0)

    # Store only the short visual history needed by the supervisory right-turn checks.
    history = deque(maxlen=SPATIAL_HISTORY)

    # Track right-turn progress and whether the next right-turn trigger is allowed.
    turns = 0
    turning = False
    turnpulses = 0
    armed = True
    rearmcount = 0

    # Track progress through the middle left-turn section before re-arming the next right turn.
    leftphaseseen = False
    leftstreak = 0
    afterleftforward = 0

    # Track the final corridor so the robot can stop cleanly at the terminal wall.
    terminalarmed = False
    terminalforward = 0
    naturalrightstreak = 0
    finalcorridorpulses = 0

    print("Neural navigation started.")
    print("The network predicts forward, left and right from the camera.")
    print("Press Ctrl+C if manual stopping is required.")

    try:
        # Main autonomous loop: read the camera, ask the NN for a direction, apply only the validated lightweight checks, then move.
        for pulse in range(1, MAX_PULSES + 1):
            if sim.getSimulationState() == sim.simulation_stopped:
                raise RuntimeError("The CoppeliaSim simulation stopped.")

            # The neural network is the primary navigator and proposes forward, left or right from the current camera frame.
            frame = getframe(sim, camera)
            raw, probabilities = predict(model, frame)
            forward, left, right = [float(value) for value in probabilities]

            # These image features are used only when the supervisor needs to resolve a known ambiguous right-turn situation.
            spatial, centre = imagefeatures(frame)
            prior = float(np.mean(history)) if len(history) == SPATIAL_HISTORY else float("nan")

            # After turn 3, the network can perform the next right turn all by itself.
            # Count that natural turn when a sustained right sequence returns to forward.
            if turns == 3 and not turning:
                if raw == "right":
                    naturalrightstreak += 1
                elif raw == "forward" and naturalrightstreak >= NATURAL_RIGHT_STREAK:
                    turns = 4
                    armed = False
                    rearmcount = 0
                    naturalrightstreak = 0
                    terminalarmed = False
                    terminalforward = 0
                    finalcorridorpulses = 0
                    print(f"Right turn 4 completed naturally at pulse {pulse}.")
                else:
                    naturalrightstreak = 0

            # After the 4th right turn, a low-confidence left prediction marks the final wall.
            if turns == 4 and not turning:
                if not terminalarmed:
                    if raw == "forward" and forward >= FORWARD_CONFIDENCE:
                        terminalforward += 1
                        if terminalforward >= TERMINAL_ARM_FRAMES:
                            terminalarmed = True
                    else:
                        terminalforward = 0
                elif raw == "left" and forward <= TERMINAL_LEFT_FORWARD_MAX:
                    setmotors(sim, leftmotor, rightmotor, 0.0, 0.0)
                    position = sim.getObjectPosition(robot, sim.handle_world)
                    orientation = sim.getObjectOrientation(robot, sim.handle_world)
                    print("Terminal wall detected. Navigation complete.")
                    print(
                        f"Final pose: x={position[0]:.4f}, y={position[1]:.4f}, "
                        f"yaw={orientation[2]:.4f}"
                    )
                    return 0

            # The network can briefly call a right-turn entrance "left".
            # The spatial cue identifies the actual right opening.
            trigger = (
                armed
                and not turning
                and turns < 4
                and raw == "left"
                and len(history) == SPATIAL_HISTORY
                and prior > SPATIAL_THRESHOLD
            )

            # The 2nd right turn uses the same cue with one extra visual check.
            if trigger and turns == 1:
                trigger = abs(spatial) <= 0.12 and centre <= 0.34

            # Once a supervised right turn has started, keep it stable briefly before releasing back to the NN.
            if turning:
                if turnpulses < MIN_RIGHT_PULSES:
                    turnpulses += 1
                    applied = "right"
                elif raw == "forward" and forward >= FORWARD_CONFIDENCE:
                    turning = False
                    turns += 1
                    turnpulses = 0
                    armed = False
                    rearmcount = 0
                    applied = "forward"
                    print(f"Right turn {turns} completed at pulse {pulse}.")

                    if turns == 2:
                        leftphaseseen = False
                        leftstreak = 0
                        afterleftforward = 0
                    elif turns == 4:
                        naturalrightstreak = 0
                        terminalarmed = False
                        terminalforward = 0
                        finalcorridorpulses = 0

                elif turnpulses < MAX_RIGHT_PULSES:
                    turnpulses += 1
                    applied = "right"
                else:
                    raise RuntimeError("A committed right turn reached its safety limit.")

            elif trigger:
                turning = True
                armed = False
                rearmcount = 0
                turnpulses = 1
                applied = "right"
                print(f"Right turn {turns + 1} started at pulse {pulse}.")

            else:
                # Small correction used before the long middle section.
                emergency = (
                    turns == 2
                    and not leftphaseseen
                    and centre <= EMERGENCY_CENTER
                    and spatial >= EMERGENCY_SPATIAL
                )
                if emergency:
                    raise RuntimeError("Corridor 3 wall safety stop.")

                clearance = (
                    turns == 2
                    and not leftphaseseen
                    and spatial >= CLEARANCE_SPATIAL
                    and centre <= CLEARANCE_CENTER
                    and raw in ("forward", "right")
                )
                applied = "right" if clearance else raw

                # Re-arm after the first and third right turns.
                if turns in (1, 3) and not armed:
                    if raw == "forward" and forward >= FORWARD_CONFIDENCE:
                        rearmcount += 1
                        if rearmcount >= REARM_FRAMES:
                            armed = True
                    else:
                        rearmcount = 0

                # After turn 2, wait for the left phase and the following straight.
                elif turns == 2 and not armed:
                    if not leftphaseseen:
                        if raw == "left":
                            leftstreak += 1
                            if leftstreak >= LEFT_PHASE_STREAK:
                                leftphaseseen = True
                                afterleftforward = 0
                        else:
                            leftstreak = 0
                    elif raw == "forward" and forward >= FORWARD_CONFIDENCE:
                        afterleftforward += 1
                        if afterleftforward >= AFTER_LEFT_FORWARD_FRAMES:
                            armed = True
                    else:
                        afterleftforward = 0

            # Execute the NN command unless one of the small validated supervisory conditions changed it.
            move(sim, leftmotor, rightmotor, applied)

            if turns == 4:
                finalcorridorpulses += 1
                if finalcorridorpulses >= MAX_FINAL_CORRIDOR_PULSES:
                    raise RuntimeError("Final corridor safety limit reached.")

            position = sim.getObjectPosition(robot, sim.handle_world)
            orientation = sim.getObjectOrientation(robot, sim.handle_world)
            print(
                f"Pulse {pulse}: predicted={raw}, applied={applied}, "
                f"F={forward:.3f}, L={left:.3f}, R={right:.3f}, "
                f"x={position[0]:.3f}, y={position[1]:.3f}, yaw={orientation[2]:.3f}"
            )

            history.append(spatial)

        raise RuntimeError("Maximum pulse limit reached before terminal stop.")

    except KeyboardInterrupt:
        # Ctrl+C provides a safe manual way to stop an experimental run.
        print("Navigation interrupted by user.")
        return 130
    finally:
        # Always leave the robot motors stopped when the program finishes or exits early.
        setmotors(sim, leftmotor, rightmotor, 0.0, 0.0)


if __name__ == "__main__":
    raise SystemExit(main())
