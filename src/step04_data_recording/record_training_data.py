"""Record W/A/D-labelled camera images using synchronized CoppeliaSim stepping.

Stability-focused Step-4 design:
- uses exactly the same professor-aligned motion profile as Step 2;
- keyboard events update requested motion state without is_pressed() polling;
- motor commands are sent only when requested state changes;
- this recorder owns CoppeliaSim stepping mode and advances one step at a time;
- image capture is deliberately sparse (0.5 Hz) and begins only after a stable
  command has been held for 0.75 seconds;
- camera pixels never cross the ZeroMQ boundary: the simIM plugin reads the
  vision sensor and writes JPEGs inside the CoppeliaSim process;
- live OpenCV preview is disabled.
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

MIN_STABLE_COMMAND_SECONDS = 0.75
FORWARD_SAVE_INTERVAL_SECONDS = 2.00
TURN_SAVE_INTERVAL_SECONDS = 2.00


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
    """Return the deliberately low capture interval for each class."""
    if label == "forward":
        return FORWARD_SAVE_INTERVAL_SECONDS
    if label in ("left", "right"):
        return TURN_SAVE_INTERVAL_SECONDS
    raise ValueError(f"Unknown label: {label}")


def write_sensor_image_with_simim(sim_im, camera_handle, image_path: Path) -> None:
    """Save a vision-sensor frame without transferring pixel data over ZeroMQ."""
    image_handle = None
    try:
        image_handle = sim_im.readFromVisionSensor(camera_handle)
        if not image_handle:
            raise RuntimeError("simIM returned an invalid image handle")
        sim_im.write(image_handle, str(image_path))
    finally:
        if image_handle:
            sim_im.destroy(image_handle)


def print_distribution(counters: dict[str, int]) -> None:
    """Print session distribution so imbalance is visible immediately."""
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
            "Before Step 5, collect additional clean examples for the "
            "underrepresented classes instead of relying immediately on "
            "strong class weighting."
        )


def main():
    print("STEP 4 - Synchronized Training Data Recording")
    print("W - Forward; A - Curved left; D - Curved right.")
    print("Release keys (or press multiple W/A/D keys) to stop.")
    print("IMPORTANT: Open the maze but leave CoppeliaSim SIMULATION STOPPED.")
    print("This recorder starts/stops the simulation and owns stepping mode.")
    print("Use terminal Ctrl+C to exit.")

    sim = None
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
    simulation_started_by_recorder = False
    stepping_enabled = False
    session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    try:
        import keyboard
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
            "Stability policy: synchronized stepping; state-change-only motor "
            "writes; 0.5 Hz simIM in-process image saves; no pixel buffers over ZMQ."
        )

        client = RemoteAPIClient()
        sim = client.require("sim")
        sim_im = client.require("simIM")
        print("SIMIM_PLUGIN_READY")

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
        if state != sim.simulation_stopped:
            raise RuntimeError(
                "Simulation is already running/paused. Stop it in CoppeliaSim "
                "before launching this synchronized recorder."
            )

        sim.setStepping(True)
        stepping_enabled = True
        sim.startSimulation()
        simulation_started_by_recorder = True

        # Warm up several deterministic simulation steps before accepting data.
        last_motor_command = apply_motor_command_if_changed(
            sim, left_motor, right_motor, 0.0, 0.0, last_motor_command
        )
        for _ in range(4):
            sim.step()

        print("SYNCHRONIZED_SIMULATION_RUNNING")

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

            # Advance exactly one simulator step, then (only if due) retrieve
            # the image generated by that synchronized step.
            sim.step()
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
                        capture_label = current_label
                        before_label, _, _ = command_from_held_keys(
                            keyboard_state.snapshot(), profile
                        )

                        if before_label == capture_label:
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

                            write_sensor_image_with_simim(
                                sim_im,
                                handles[CAMERA_PATH],
                                image_path,
                            )

                            after_label, _, _ = command_from_held_keys(
                                keyboard_state.snapshot(), profile
                            )
                            if after_label == capture_label:
                                counters[capture_label] += 1
                                last_save_time[capture_label] = time.monotonic()
                            else:
                                image_path.unlink(missing_ok=True)

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
            try:
                if left_motor is not None and right_motor is not None:
                    last_motor_command = apply_motor_command_if_changed(
                        sim,
                        left_motor,
                        right_motor,
                        0.0,
                        0.0,
                        last_motor_command,
                    )
                    if simulation_started_by_recorder:
                        sim.step()
            except Exception as error:
                print(
                    f"STEP 4 CLEANUP ERROR: Could not stop motors cleanly: {error}",
                    file=sys.stderr,
                )
                exit_status = 1

            if simulation_started_by_recorder:
                try:
                    sim.stopSimulation()
                except Exception as error:
                    print(
                        f"STEP 4 CLEANUP ERROR: Could not stop simulation: {error}",
                        file=sys.stderr,
                    )
                    exit_status = 1

            if stepping_enabled:
                try:
                    sim.setStepping(False)
                except Exception as error:
                    print(
                        f"STEP 4 CLEANUP ERROR: Could not disable stepping: {error}",
                        file=sys.stderr,
                    )
                    exit_status = 1

        print(f"Session ID: {session_id}")
        print_distribution(counters)

    return exit_status


if __name__ == "__main__":
    sys.exit(main())
