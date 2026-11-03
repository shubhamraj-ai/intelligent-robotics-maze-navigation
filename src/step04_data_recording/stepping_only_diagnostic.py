"""Step-4 stepping-only stability diagnostic.

Purpose:
- keep the Step-4 event-driven keyboard/state-change motor pattern;
- keep synchronized stepping via sim.setStepping(True) and sim.step();
- remove ALL temporary Lua scripts;
- remove ALL string signals/label traffic;
- remove ALL camera/vision/image handling.

This isolates synchronized stepping/control-loop timing from the Lua/script/signal
machinery that remains in the no-vision Step-4 diagnostic.
"""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MOTION_PROFILE_PATH = REPO_ROOT / "config" / "motion_profile.json"
CAPTURE_LABEL_SIGNAL = "step4_capture_label"


def load_motion_profile(path: Path = MOTION_PROFILE_PATH) -> dict[str, float]:
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


class KeyboardState:
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
    command = (float(left_velocity), float(right_velocity))
    if command == previous_command:
        return previous_command
    sim.setJointTargetVelocity(left_motor, command[0])
    sim.setJointTargetVelocity(right_motor, command[1])
    return command


def main():
    print("STEP 4 DIAGNOSTIC - PERSISTENT LUA + SIGNAL WRITE ONLY")
    print("W - Forward; A - Curved left; D - Curved right.")
    print("Release keys (or press multiple W/A/D keys) to stop.")
    print("IMPORTANT: Open the maze and leave SIMULATION STOPPED.")
    print("Persistent Lua script must already be stored in the loaded scene.")
    print("Python writes ONE dynamic W/A/D label string signal.")
    print("Persistent Lua does NOT read the signal in this test.")
    print("NO runtime Lua creation/removal. NO camera/image calls.")
    print("Use terminal Ctrl+C to finish.")

    sim = None
    left_motor = None
    right_motor = None
    last_motor_command = None
    keyboard_hook = None
    keyboard_state = KeyboardState()
    simulation_started = False
    stepping_enabled = False
    last_capture_label = None
    exit_status = 0

    try:
        import keyboard
        from coppeliasim_zmqremoteapi_client import RemoteAPIClient

        profile = load_motion_profile()
        keyboard_hook = keyboard.hook(keyboard_state.handle_event)

        print(f"Motion profile: {MOTION_PROFILE_PATH}")
        print(
            "Speeds: "
            f"forward={profile['forward_speed']:.2f}, "
            f"turn inner={profile['turn_inner_speed']:.2f}, "
            f"turn outer={profile['turn_outer_speed']:.2f}"
        )
        print(
            "Diagnostic policy: event-driven keys + state-change-only motor writes "
            "+ synchronized stepping + one dynamic Python string-signal write; "
            "persistent Lua is scene-owned and does not read the signal; no vision."
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
                "this diagnostic."
            )

        sim.setStepping(True)
        stepping_enabled = True
        sim.startSimulation()
        simulation_started = True

        sim.setStringSignal(CAPTURE_LABEL_SIGNAL, "")
        last_capture_label = ""

        last_motor_command = apply_motor_command_if_changed(
            sim, left_motor, right_motor, 0.0, 0.0, last_motor_command
        )

        for _ in range(4):
            sim.step()

        print("PERSISTENT_SIGNAL_WRITE_PROBE_PASS")
        print("READY_TO_DRIVE_PERSISTENT_SIGNAL_WRITE_ONLY")

        while True:
            loop_started = time.monotonic()

            current_label, left_velocity, right_velocity = command_from_held_keys(
                keyboard_state.snapshot(), profile
            )

            normalized_label = current_label or ""
            if normalized_label != last_capture_label:
                sim.setStringSignal(CAPTURE_LABEL_SIGNAL, normalized_label)
                last_capture_label = normalized_label

            last_motor_command = apply_motor_command_if_changed(
                sim,
                left_motor,
                right_motor,
                left_velocity,
                right_velocity,
                last_motor_command,
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
        print(f"STEPPING-ONLY ERROR: {error}", file=sys.stderr)
        exit_status = 1
    finally:
        if keyboard_hook is not None:
            try:
                keyboard.unhook(keyboard_hook)
            except Exception as error:
                print(
                    f"STEPPING-ONLY CLEANUP ERROR: keyboard hook: {error}",
                    file=sys.stderr,
                )
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
                print(
                    f"STEPPING-ONLY CLEANUP ERROR: motor stop: {error}",
                    file=sys.stderr,
                )
                exit_status = 1

            if simulation_started:
                try:
                    sim.stopSimulation()
                    for _ in range(30):
                        if sim.getSimulationState() == sim.simulation_stopped:
                            break
                        time.sleep(0.05)
                except Exception as error:
                    print(
                        f"STEPPING-ONLY CLEANUP ERROR: stop simulation: {error}",
                        file=sys.stderr,
                    )
                    exit_status = 1

            if stepping_enabled:
                try:
                    sim.setStepping(False)
                except Exception:
                    pass

        print("PERSISTENT_SIGNAL_WRITE_ONLY_DIAGNOSTIC_FINISHED")

    return exit_status


if __name__ == "__main__":
    sys.exit(main())
