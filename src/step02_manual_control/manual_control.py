"""Drive the PioneerP3DX manually with a simple, tunable motion profile.

This Step-2 controller is deliberately minimal:
- W drives both wheels forward.
- A/D use forward-only differential wheel speeds to create curved turns.
- The motion profile is shared with Step 4 so training-data collection uses
  exactly the same robot motion that is manually calibrated here.
"""

from __future__ import annotations

import json
import sys
import time
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


def get_command(keyboard_module, profile: dict[str, float]):
    """Return one unambiguous W/A/D command and its wheel velocities."""
    held = [key for key in ("w", "a", "d") if keyboard_module.is_pressed(key)]
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

    sim = None
    left_motor = None
    right_motor = None
    exit_status = 0

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
            "These are initial calibration values. "
            "Manually validate the full maze before collecting new training data."
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

        while True:
            _, left_velocity, right_velocity = get_command(keyboard, profile)
            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)
            time.sleep(profile["control_interval_seconds"])
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
