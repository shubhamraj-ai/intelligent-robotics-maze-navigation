"""Drive the PioneerP3DX manually with a simple, tunable motion profile.

This Step-2 controller is deliberately minimal:
- W drives both wheels forward.
- A/D use forward-only differential wheel speeds to create curved turns.
- Keyboard events update the requested motion state.
- Motor commands are sent only when that requested state changes, avoiding
  redundant high-frequency ZMQ writes associated with simulator instability
  during validation.
- The motion profile is shared with Step 4 so training-data collection uses
  exactly the same robot motion that is manually calibrated here.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import keyboard
from coppeliasim_zmqremoteapi_client import RemoteAPIClient


REPO_ROOT = Path(__file__).resolve().parents[2]
MOTION_PROFILE_PATH = REPO_ROOT / "config" / "motion_profile.json"


def load_motion_profile(path: Path = MOTION_PROFILE_PATH) -> dict[str, float]:
    """Load and validate the professor-aligned manual driving parameters."""
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
    """Return one unambiguous W/A/D command from the current held-key set."""
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
            print(
                f"STEP 2 CLEANUP ERROR: Could not stop a motor: {error}",
                file=sys.stderr,
            )
    return cleanup_succeeded


def main():
    print("STEP 2 — Manual Robot Control / Motion Calibration")
    print("W - Forward")
    print("A - Curved left")
    print("D - Curved right")
    print("Release keys (or press multiple W/A/D keys) to stop.")
    print("ESC - Stop motors and exit.")
    print("Motor commands are sent only when the requested motion state changes.")

    sim = None
    left_motor = None
    right_motor = None
    exit_status = 0
    held_keys = set()
    last_motor_command = None

    try:
        profile = load_motion_profile()
        print(f"Motion profile: {MOTION_PROFILE_PATH}")
        print(
            "Speeds: "
            f"forward={profile['forward_speed']:.2f}, "
            f"turn inner={profile['turn_inner_speed']:.2f}, "
            f"turn outer={profile['turn_outer_speed']:.2f}"
        )
        print(
            "These values passed two complete AirGPU full-maze traversals "
            "using state-change/event-driven control."
        )

        try:
            client = RemoteAPIClient()
            sim = client.require("sim")
        except Exception as error:
            raise RuntimeError(
                f"Could not connect to the CoppeliaSim ZMQ Remote API: {error}"
            ) from error

        for object_path in (
            "/PioneerP3DX",
            "/PioneerP3DX/leftMotor",
            "/PioneerP3DX/rightMotor",
        ):
            try:
                object_handle = sim.getObject(object_path)
                if object_handle == -1:
                    raise RuntimeError("CoppeliaSim returned an invalid object handle")
            except Exception as error:
                raise RuntimeError(
                    f"Could not resolve scene object {object_path}: {error}"
                ) from error

            if object_path == "/PioneerP3DX/leftMotor":
                left_motor = object_handle
            elif object_path == "/PioneerP3DX/rightMotor":
                right_motor = object_handle

        last_motor_command = apply_motor_command_if_changed(
            sim, left_motor, right_motor, 0.0, 0.0, last_motor_command
        )

        while True:
            event = keyboard.read_event()
            key = (event.name or "").lower()

            if key == "esc" and event.event_type == keyboard.KEY_DOWN:
                break
            if key not in {"w", "a", "d"}:
                continue

            if event.event_type == keyboard.KEY_DOWN:
                held_keys.add(key)
            elif event.event_type == keyboard.KEY_UP:
                held_keys.discard(key)
            else:
                continue

            _, left_velocity, right_velocity = command_from_held_keys(
                held_keys, profile
            )
            last_motor_command = apply_motor_command_if_changed(
                sim,
                left_motor,
                right_motor,
                left_velocity,
                right_velocity,
                last_motor_command,
            )
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
