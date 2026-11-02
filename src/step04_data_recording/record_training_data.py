"""Record cleaner W/A/D-labelled camera images for neural-network training.

The code intentionally remains close to the original Step-4 recorder while
addressing the factors highlighted by the professor:
- it uses the exact same tunable speed/curvature profile as Step 2;
- it records only after a command has remained stable briefly;
- it saves forward frames less frequently than turn frames to reduce the
  previous extreme forward-class dominance;
- filenames include a session ID so later training can keep traversals separate.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MOTION_PROFILE_PATH = REPO_ROOT / "config" / "motion_profile.json"
DATASET_PATH = REPO_ROOT / "dataset_simplified"
CAMERA_PATH = "/PioneerP3DX/cam1"

# Conservative recording policy for simulator stability:
# - keyboard/motor control remains responsive locally;
# - CoppeliaSim image RPC calls occur only when a frame is actually due;
# - forward is intentionally sampled less often than turns.
MIN_STABLE_COMMAND_SECONDS = 0.20
FORWARD_SAVE_INTERVAL_SECONDS = 0.40
TURN_SAVE_INTERVAL_SECONDS = 0.20


def load_motion_profile(path: Path = MOTION_PROFILE_PATH) -> dict[str, float]:
    """Load the same motion profile manually calibrated in Step 2."""
    profile = json.loads(path.read_text(encoding="utf-8"))

    required = {
        "forward_speed",
        "turn_outer_speed",
        "turn_inner_speed",
        "control_interval_seconds",
    }
    missing = required - set(profile)
    if missing:
        raise ValueError(f"Motion profile is missing: {sorted(missing)}")

    values = {name: float(profile[name]) for name in required}
    if values["forward_speed"] <= 0:
        raise ValueError("forward_speed must be > 0")
    if values["turn_outer_speed"] <= 0:
        raise ValueError("turn_outer_speed must be > 0")
    if values["turn_inner_speed"] < 0:
        raise ValueError("turn_inner_speed must be >= 0")
    if values["turn_inner_speed"] >= values["turn_outer_speed"]:
        raise ValueError("turn_inner_speed must be lower than turn_outer_speed")
    if values["control_interval_seconds"] <= 0:
        raise ValueError("control_interval_seconds must be > 0")

    return values


def command_from_held_keys(held_keys, profile: dict[str, float]):
    """Return one stable W/A/D label and the matching calibrated wheel speeds."""
    held = [key for key in ("w", "a", "d") if key in held_keys]
    if len(held) != 1:
        return None, 0.0, 0.0

    key = held[0]
    if key == "w":
        speed = profile["forward_speed"]
        return "forward", speed, speed

    inner = profile["turn_inner_speed"]
    outer = profile["turn_outer_speed"]
    if key == "a":
        return "left", inner, outer
    return "right", outer, inner


def get_command(keyboard_module, profile: dict[str, float]):
    """Compatibility helper for tests/tools that expose is_pressed()."""
    held = {key for key in ("w", "a", "d") if keyboard_module.is_pressed(key)}
    return command_from_held_keys(held, profile)


class KeyboardState:
    """Maintain W/A/D state from keyboard events without polling is_pressed()."""

    def __init__(self):
        self._held = set()
        self._lock = threading.Lock()

    def handle_event(self, event):
        key = (getattr(event, "name", "") or "").lower()
        if key not in {"w", "a", "d"}:
            return

        event_type = getattr(event, "event_type", "")
        with self._lock:
            if event_type == "down":
                self._held.add(key)
            elif event_type == "up":
                self._held.discard(key)

    def snapshot(self):
        with self._lock:
            return set(self._held)


def apply_motor_command_if_changed(
    sim,
    left_motor,
    right_motor,
    left_velocity: float,
    right_velocity: float,
    previous_command,
):
    """Write wheel targets only when the requested pair changes."""
    command = (float(left_velocity), float(right_velocity))
    if command == previous_command:
        return previous_command
    sim.setJointTargetVelocity(left_motor, command[0])
    sim.setJointTargetVelocity(right_motor, command[1])
    return command


def save_interval_for(label: str) -> float:
    """Subsample long forward runs more strongly than shorter turn states."""
    if label == "forward":
        return FORWARD_SAVE_INTERVAL_SECONDS
    if label in ("left", "right"):
        return TURN_SAVE_INTERVAL_SECONDS
    raise ValueError(f"Unknown label: {label}")


def convert_image(raw_image, resolution, np, cv2):
    """Validate and convert CoppeliaSim's bottom-up RGB buffer to BGR."""
    if len(resolution) != 2:
        raise ValueError(f"Expected [width, height], received {resolution}")
    width, height = resolution
    if not all(isinstance(value, int) and value > 0 for value in resolution):
        raise ValueError(
            f"Camera resolution must contain positive integers: {resolution}"
        )
    expected_bytes = width * height * 3
    if len(raw_image) != expected_bytes:
        raise ValueError(
            f"Expected {expected_bytes} RGB bytes, received {len(raw_image)}"
        )
    frame = np.frombuffer(raw_image, dtype=np.uint8).reshape(height, width, 3)
    frame = cv2.flip(frame, 0)
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


def print_distribution(counters: dict[str, int]) -> None:
    """Print the session distribution so imbalance is visible immediately."""
    total = sum(counters.values())
    print("Saved images: " + ", ".join(f"{k}={v}" for k, v in counters.items()))
    if not total:
        return

    shares = {label: count / total for label, count in counters.items()}
    print(
        "Class distribution: "
        + ", ".join(f"{label}={share:.1%}" for label, share in shares.items())
    )
    if max(shares.values()) > 0.70:
        print(
            "STEP 4 DATA WARNING: One class exceeds 70% of this session. "
            "Before Step 5, collect additional clean examples for the underrepresented "
            "classes instead of relying immediately on strong class weighting."
        )


def main():
    print("STEP 4 - Training Data Recording")
    print("W - Forward; A - Curved left; D - Curved right.")
    print("Release keys (or press multiple W/A/D keys) to stop.")
    print("Start the simulation in CoppeliaSim; use terminal Ctrl+C to exit.")

    sim = None
    cv2 = None
    left_motor = None
    right_motor = None
    counters = {"forward": 0, "left": 0, "right": 0}
    last_save_time = {label: None for label in counters}
    active_label = None
    active_since = None
    last_motor_command = None
    keyboard_hook = None
    keyboard_state = KeyboardState()
    exit_status = 0
    session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    try:
        import cv2
        import keyboard
        import numpy as np
        from coppeliasim_zmqremoteapi_client import RemoteAPIClient

        profile = load_motion_profile()
        keyboard_hook = keyboard.hook(keyboard_state.handle_event)
        print(f"Session ID: {session_id}")
        print(f"Motion profile: {MOTION_PROFILE_PATH}")
        print(
            "Speeds: "
            f"forward={profile['forward_speed']:.2f}, "
            f"turn inner={profile['turn_inner_speed']:.2f}, "
            f"turn outer={profile['turn_outer_speed']:.2f}"
        )
        print(
            "Recording policy: "
            f"stable command >= {MIN_STABLE_COMMAND_SECONDS:.2f}s; "
            f"forward every {FORWARD_SAVE_INTERVAL_SECONDS:.2f}s; "
            f"turn every {TURN_SAVE_INTERVAL_SECONDS:.2f}s."
        )
        print(
            "Stability policy: motor RPC writes occur only on command changes; "
            "camera RPC reads occur only when a dataset frame is due; "
            "live OpenCV preview is disabled."
        )

        client = RemoteAPIClient()
        sim = client.require("sim")
        handles = {}

        for path in (
            "/PioneerP3DX",
            "/PioneerP3DX/leftMotor",
            "/PioneerP3DX/rightMotor",
            CAMERA_PATH,
        ):
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

        state = sim.getSimulationState()
        if state in (sim.simulation_stopped, sim.simulation_paused):
            raise RuntimeError(
                "Simulation is stopped or paused; start it in CoppeliaSim."
            )

        while True:
            loop_started = time.monotonic()

            held_snapshot = keyboard_state.snapshot()
            current_label, left_velocity, right_velocity = command_from_held_keys(
                held_snapshot, profile
            )
            last_motor_command = apply_motor_command_if_changed(
                sim,
                left_motor,
                right_motor,
                left_velocity,
                right_velocity,
                last_motor_command,
            )

            now = time.monotonic()

            if current_label is None:
                active_label = None
                active_since = None
            else:
                if current_label != active_label:
                    active_label = current_label
                    active_since = now
                elif (
                    active_since is not None
                    and now - active_since >= MIN_STABLE_COMMAND_SECONDS
                ):
                    interval = save_interval_for(current_label)
                    last_saved = last_save_time[current_label]

                    if last_saved is None or now - last_saved >= interval:
                        # Request a camera frame only when we are actually due
                        # to save one. Re-check keyboard state after the RPC so
                        # a command transition during capture cannot be mislabeled.
                        capture_label = current_label
                        raw_image, resolution = sim.getVisionSensorImg(
                            handles[CAMERA_PATH]
                        )
                        after_label, _, _ = command_from_held_keys(
                            keyboard_state.snapshot(), profile
                        )

                        if after_label == capture_label:
                            frame = convert_image(raw_image, resolution, np, cv2)
                            timestamp = datetime.now(timezone.utc).strftime(
                                "%Y%m%dT%H%M%S%fZ"
                            )
                            counter = counters[capture_label] + 1
                            filename = (
                                f"{session_id}_{capture_label}_{timestamp}_"
                                f"{counter:06d}.jpg"
                            )
                            image_path = DATASET_PATH / capture_label / filename

                            while image_path.exists():
                                counter += 1
                                filename = (
                                    f"{session_id}_{capture_label}_{timestamp}_"
                                    f"{counter:06d}.jpg"
                                )
                                image_path = DATASET_PATH / capture_label / filename

                            if not cv2.imwrite(str(image_path), frame):
                                raise RuntimeError(
                                    f"Could not save image {image_path}"
                                )

                            counters[capture_label] += 1
                            last_save_time[capture_label] = time.monotonic()

            remaining = (
                profile["control_interval_seconds"]
                - (time.monotonic() - loop_started)
            )
            if remaining > 0:
                time.sleep(remaining)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f"STEP 4 ERROR: {error}", file=sys.stderr)
        exit_status = 1
    finally:
        if keyboard_hook is not None:
            try:
                keyboard.unhook(keyboard_hook)
            except Exception as error:
                print(
                    f"STEP 4 CLEANUP ERROR: Could not remove keyboard hook: {error}",
                    file=sys.stderr,
                )
                exit_status = 1

        if sim is not None:
            for motor in (left_motor, right_motor):
                if motor is not None:
                    try:
                        sim.setJointTargetVelocity(motor, 0.0)
                    except Exception as error:
                        print(
                            f"STEP 4 CLEANUP ERROR: Could not stop a motor: {error}",
                            file=sys.stderr,
                        )
                        exit_status = 1

        print(f"Session ID: {session_id}")
        print_distribution(counters)

    return exit_status


if __name__ == "__main__":
    sys.exit(main())
