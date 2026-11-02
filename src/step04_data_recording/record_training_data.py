"""Step 4 recorder with all vision acquisition executed inside CoppeliaSim.

Python responsibilities are deliberately restricted to:
- W/A/D event handling;
- professor-aligned state-change-only motor commands;
- tiny string signals describing the current class label;
- synchronized simulation stepping.

Python never resolves the camera object, reads camera pixels, calls simIM, or
writes image buffers.  A temporary Lua simulation script, created before the
run and removed afterwards, performs vision-sensor reads and JPEG writes inside
CoppeliaSim itself.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MOTION_PROFILE_PATH = REPO_ROOT / "config" / "motion_profile.json"
DATASET_PATH = REPO_ROOT / "dataset_simplified"
DIAGNOSTIC_NO_VISION = os.environ.get("STEP4_NO_VISION_DIAGNOSTIC") == "1"
CAPTURE_SCRIPT_PATH = Path(__file__).with_name(
    "capture_in_scene_no_vision.lua" if DIAGNOSTIC_NO_VISION else "capture_in_scene.lua"
)

CAPTURE_LABEL_SIGNAL = "step4_capture_label"
DATASET_ROOT_SIGNAL = "step4_dataset_root"
SESSION_ID_SIGNAL = "step4_session_id"

MIN_STABLE_COMMAND_SECONDS = 0.75
SAVE_INTERVAL_SECONDS = 2.00


def load_motion_profile(path: Path = MOTION_PROFILE_PATH) -> dict[str, float]:
    """Load the same manually calibrated motion profile used by Step 2."""
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
    """Return one W/A/D label and matching calibrated wheel speeds."""
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
    """Compatibility helper used by tests/tools exposing is_pressed()."""
    held = {key for key in ("w", "a", "d") if keyboard_module.is_pressed(key)}
    return command_from_held_keys(held, profile)


class KeyboardState:
    """Maintain W/A/D state from events instead of repeated polling."""

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


def set_capture_label_if_changed(sim, label, previous_label):
    """Publish only small state-change labels to the in-scene capture script."""
    normalized = label or ""
    if normalized == previous_label:
        return previous_label
    sim.setStringSignal(CAPTURE_LABEL_SIGNAL, normalized)
    return normalized


def install_internal_capture_script(sim, script_path: Path = CAPTURE_SCRIPT_PATH):
    """Create a temporary Lua simulation script while the simulation is stopped."""
    script_text = script_path.read_text(encoding="utf-8")
    if not script_text.strip():
        raise RuntimeError(f"Capture script is empty: {script_path}")
    script_handle = sim.createScript(
        sim.scripttype_simulation,
        script_text,
        0,
        "lua",
    )
    if script_handle < 0:
        raise RuntimeError("CoppeliaSim could not create the capture script")
    try:
        sim.setObjectAlias(script_handle, "Step4InternalCapture")
    except Exception:
        # Alias is diagnostic only; capture does not depend on it.
        pass
    return script_handle


def prepare_dataset() -> None:
    """Create only the directories required by this session."""
    for label in ("forward", "left", "right", "_probe"):
        (DATASET_PATH / label).mkdir(parents=True, exist_ok=True)


def count_session_images(session_id: str) -> dict[str, int]:
    """Count images produced by the in-scene script for this session."""
    return {
        label: len(list((DATASET_PATH / label).glob(f"{session_id}_{label}_*.jpg")))
        for label in ("forward", "left", "right")
    }


def run_stationary_capture_probe(sim, session_id: str) -> None:
    """Prove one in-scene image can be saved before any wheel motion occurs."""
    probe_dir = DATASET_PATH / "_probe"
    before = set(probe_dir.glob(f"{session_id}_probe_*.jpg"))

    sim.setStringSignal(CAPTURE_LABEL_SIGNAL, "probe")
    probe_start = sim.getSimulationTime()
    target = MIN_STABLE_COMMAND_SECONDS + 0.35

    while sim.getSimulationTime() - probe_start < target:
        sim.step()

    sim.setStringSignal(CAPTURE_LABEL_SIGNAL, "")
    sim.step()

    after = set(probe_dir.glob(f"{session_id}_probe_*.jpg"))
    if len(after - before) < 1:
        raise RuntimeError(
            "Internal stationary capture probe produced no JPEG. Do not drive."
        )


def print_distribution(counters: dict[str, int]) -> None:
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
            "Collect additional clean examples for underrepresented classes "
            "before Step 5."
        )


def main():
    print("STEP 4 - In-scene Training Data Recording")
    print("W - Forward; A - Curved left; D - Curved right.")
    print("Release keys (or press multiple W/A/D keys) to stop.")
    print("IMPORTANT: Open the maze and leave SIMULATION STOPPED.")
    print("Python does not access the camera in this build.")
    if DIAGNOSTIC_NO_VISION:
        print("DIAGNOSTIC MODE: Lua vision read/save is DISABLED.")
        print("DIAGNOSTIC MODE: No training images will be created.")
    print("Use terminal Ctrl+C to finish.")

    sim = None
    capture_script_handle = None
    left_motor = None
    right_motor = None
    last_motor_command = None
    last_capture_label = None
    keyboard_hook = None
    keyboard_state = KeyboardState()
    exit_status = 0
    simulation_started = False
    stepping_enabled = False
    session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    try:
        import keyboard
        from coppeliasim_zmqremoteapi_client import RemoteAPIClient

        profile = load_motion_profile()
        keyboard_hook = keyboard.hook(keyboard_state.handle_event)
        prepare_dataset()

        print(f"Session ID: {session_id}")
        print(f"Motion profile: {MOTION_PROFILE_PATH}")
        print(
            "Speeds: "
            f"forward={profile['forward_speed']:.2f}, "
            f"turn inner={profile['turn_inner_speed']:.2f}, "
            f"turn outer={profile['turn_outer_speed']:.2f}"
        )
        if DIAGNOSTIC_NO_VISION:
            print(
                "Diagnostic policy: same temporary Lua sensing-script lifecycle, "
                "same labels/stepping/motion; vision read and image save disabled."
            )
        else:
            print(
                "Capture policy: handled entirely by temporary Lua simulation script; "
                f"stable command >= {MIN_STABLE_COMMAND_SECONDS:.2f}s; "
                f"one frame every {SAVE_INTERVAL_SECONDS:.2f}s."
            )

        client = RemoteAPIClient()
        sim = client.require("sim")

        robot = sim.getObject("/PioneerP3DX")
        left_motor = sim.getObject("/PioneerP3DX/leftMotor")
        right_motor = sim.getObject("/PioneerP3DX/rightMotor")
        if min(robot, left_motor, right_motor) < 0:
            raise RuntimeError("Could not resolve PioneerP3DX motor objects")

        if sim.getSimulationState() != sim.simulation_stopped:
            raise RuntimeError(
                "Simulation is already running/paused. Stop it before launching "
                "this recorder."
            )

        capture_script_handle = install_internal_capture_script(sim)
        print("INTERNAL_CAPTURE_SCRIPT_INSTALLED")

        sim.setStepping(True)
        stepping_enabled = True
        sim.startSimulation()
        simulation_started = True

        # Signals are set after start because simulation start clears signals.
        sim.setStringSignal(DATASET_ROOT_SIGNAL, DATASET_PATH.as_posix())
        sim.setStringSignal(SESSION_ID_SIGNAL, session_id)
        last_capture_label = set_capture_label_if_changed(sim, None, None)

        last_motor_command = apply_motor_command_if_changed(
            sim, left_motor, right_motor, 0.0, 0.0, last_motor_command
        )

        for _ in range(4):
            sim.step()

        if DIAGNOSTIC_NO_VISION:
            print("RUNNING_NO_VISION_STEPPING_PROBE")
            probe_start = sim.getSimulationTime()
            target = MIN_STABLE_COMMAND_SECONDS + 0.35
            sim.setStringSignal(CAPTURE_LABEL_SIGNAL, "probe")
            while sim.getSimulationTime() - probe_start < target:
                sim.step()
            sim.setStringSignal(CAPTURE_LABEL_SIGNAL, "")
            sim.step()
            print("NO_VISION_STEPPING_PROBE_PASS")
            print("READY_TO_DRIVE_NO_VISION_DIAGNOSTIC")
        else:
            print("RUNNING_STATIONARY_INTERNAL_CAPTURE_PROBE")
            run_stationary_capture_probe(sim, session_id)
            print("INTERNAL_CAPTURE_PROBE_PASS")
            print("READY_TO_DRIVE")

        while True:
            loop_started = time.monotonic()

            current_label, left_velocity, right_velocity = command_from_held_keys(
                keyboard_state.snapshot(), profile
            )

            last_motor_command = apply_motor_command_if_changed(
                sim,
                left_motor,
                right_motor,
                left_velocity,
                right_velocity,
                last_motor_command,
            )
            last_capture_label = set_capture_label_if_changed(
                sim, current_label, last_capture_label
            )

            sim.step()

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
                print(f"STEP 4 CLEANUP ERROR: keyboard hook: {error}", file=sys.stderr)
                exit_status = 1

        if sim is not None:
            try:
                sim.setStringSignal(CAPTURE_LABEL_SIGNAL, "")
            except Exception:
                pass

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
                    if simulation_started:
                        sim.step()
            except Exception as error:
                print(f"STEP 4 CLEANUP ERROR: motor stop: {error}", file=sys.stderr)
                exit_status = 1

            if simulation_started:
                try:
                    sim.stopSimulation()
                    # Give CoppeliaSim a few remote cycles to reach stopped state.
                    for _ in range(30):
                        if sim.getSimulationState() == sim.simulation_stopped:
                            break
                        time.sleep(0.05)
                except Exception as error:
                    print(
                        f"STEP 4 CLEANUP ERROR: stop simulation: {error}",
                        file=sys.stderr,
                    )
                    exit_status = 1

            if stepping_enabled:
                try:
                    sim.setStepping(False)
                except Exception:
                    pass

            if capture_script_handle is not None:
                try:
                    sim.removeObjects([capture_script_handle])
                except Exception as error:
                    print(
                        f"STEP 4 CLEANUP WARNING: temporary script not removed: {error}",
                        file=sys.stderr,
                    )

        print(f"Session ID: {session_id}")
        print_distribution(count_session_images(session_id))

    return exit_status


if __name__ == "__main__":
    sys.exit(main())
