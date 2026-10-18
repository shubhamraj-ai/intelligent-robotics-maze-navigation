"""Collect paired turn-boundary data for Step 5G.

Human W/A/D commands control the PioneerP3DX. No CNN inference is performed.
Every nonblank camera frame is saved with the stable human command and robot
pose. After the run, turn-onset events are identified from the human-command
sequence so matched pre-turn forward frames and post-onset true-turn frames can
be selected later without changing the labels after seeing model predictions.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

CLASS_NAMES = ("forward", "left", "right")
FORWARD_SPEED = 2.0
TURN_SPEED = 2.0
LOOP_INTERVAL_SECONDS = 0.10
CAMERA_PATH = "/PioneerP3DX/cam1"
BOUNDARY_FRAMES = 5
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "boundary_sessions"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Human-controlled paired turn-boundary data collection."
    )
    parser.add_argument("--session-id", required=True)
    parser.add_argument(
        "--role",
        choices=("train", "validation"),
        required=True,
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args(argv)


def get_human_command(keyboard_module):
    held = [key for key in ("w", "a", "d") if keyboard_module.is_pressed(key)]
    if len(held) != 1:
        return None, 0.0, 0.0
    if held[0] == "w":
        return "forward", FORWARD_SPEED, FORWARD_SPEED
    if held[0] == "a":
        return "left", -TURN_SPEED, TURN_SPEED
    return "right", TURN_SPEED, -TURN_SPEED


def convert_raw_image_rgb(raw_image, resolution, np_module):
    if len(resolution) != 2:
        raise ValueError(f"Expected [width, height], received {resolution}")
    width, height = resolution
    if not all(isinstance(value, int) and value > 0 for value in resolution):
        raise ValueError(f"Camera resolution must contain positive integers: {resolution}")
    expected = width * height * 3
    if len(raw_image) != expected:
        raise ValueError(f"Expected {expected} RGB bytes, received {len(raw_image)}")
    frame = np_module.frombuffer(raw_image, dtype=np_module.uint8).reshape(
        height, width, 3
    )
    return np_module.flipud(frame).copy()


def stop_motors(sim, left_motor, right_motor):
    ok = True
    for motor in (left_motor, right_motor):
        if motor is None:
            continue
        try:
            sim.setJointTargetVelocity(motor, 0.0)
        except Exception as error:
            ok = False
            print(f"BOUNDARY CLEANUP ERROR: {error}", file=sys.stderr)
    return ok


def detect_boundary_events(rows, boundary_frames=BOUNDARY_FRAMES):
    """Identify forward->left/right command boundaries from stable labels.

    Blank/unstable frames are ignored when determining the previous stable human
    command. A valid event must have at least boundary_frames stable forward
    samples immediately before the onset in stable-command order and at least
    boundary_frames stable samples of the turn command starting at the onset.
    """

    stable = [
        (index, row)
        for index, row in enumerate(rows)
        if row["human_command"] in CLASS_NAMES
    ]
    events = []

    for pos, (row_index, row) in enumerate(stable):
        turn = row["human_command"]
        if turn not in ("left", "right") or pos == 0:
            continue
        if stable[pos - 1][1]["human_command"] != "forward":
            continue

        pre = []
        cursor = pos - 1
        while cursor >= 0 and stable[cursor][1]["human_command"] == "forward":
            pre.append(stable[cursor])
            cursor -= 1
            if len(pre) == boundary_frames:
                break
        pre.reverse()

        post = []
        cursor = pos
        while cursor < len(stable) and stable[cursor][1]["human_command"] == turn:
            post.append(stable[cursor])
            cursor += 1
            if len(post) == boundary_frames:
                break

        if len(pre) != boundary_frames or len(post) != boundary_frames:
            continue

        events.append(
            {
                "turn_class": turn,
                "onset_row_index": row_index,
                "onset_frame_index": int(row["frame_index"]),
                "onset_elapsed_seconds": float(row["elapsed_seconds"]),
                "pre_rows": [item[1] for item in pre],
                "post_rows": [item[1] for item in post],
            }
        )

    return events


def write_boundary_events(path, events):
    fieldnames = [
        "event_id",
        "turn_class",
        "onset_frame_index",
        "onset_elapsed_seconds",
        "pre_forward_frame_indices",
        "post_turn_frame_indices",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for event_id, event in enumerate(events, start=1):
            writer.writerow(
                {
                    "event_id": event_id,
                    "turn_class": event["turn_class"],
                    "onset_frame_index": event["onset_frame_index"],
                    "onset_elapsed_seconds": f"{event['onset_elapsed_seconds']:.3f}",
                    "pre_forward_frame_indices": ";".join(
                        row["frame_index"] for row in event["pre_rows"]
                    ),
                    "post_turn_frame_indices": ";".join(
                        row["frame_index"] for row in event["post_rows"]
                    ),
                }
            )


def build_summary(session_id, role, rows, events):
    scored = [row for row in rows if row["human_command"] in CLASS_NAMES]
    counts = {
        name: sum(row["human_command"] == name for row in scored)
        for name in CLASS_NAMES
    }
    left_events = sum(event["turn_class"] == "left" for event in events)
    right_events = sum(event["turn_class"] == "right" for event in events)

    lines = [
        "STEP 5G PAIRED BOUNDARY COLLECTION SUMMARY",
        "",
        f"Session ID: {session_id}",
        f"Role: {role}",
        f"Total saved frames: {len(rows)}",
        f"Stable-command frames: {len(scored)}",
        f"Forward frames: {counts['forward']}",
        f"Left frames: {counts['left']}",
        f"Right frames: {counts['right']}",
        f"Valid left-turn boundary events: {left_events}",
        f"Valid right-turn boundary events: {right_events}",
        f"Boundary frames per side: {BOUNDARY_FRAMES}",
        "",
        "CNN inference: OFF",
        "OpenCV GUI display: OFF",
        "Human W/A/D commands controlled the motors.",
    ]
    return "\n".join(lines) + "\n"


def main(argv=None):
    args = parse_args(argv)
    output_root = args.output_root.resolve()
    session_dir = output_root / args.session_id
    frames_dir = session_dir / "frames"

    if session_dir.exists():
        raise FileExistsError(f"Session already exists: {session_dir}")
    frames_dir.mkdir(parents=True)

    metadata_path = session_dir / "metadata.csv"
    events_path = session_dir / "boundary_events.csv"
    summary_path = session_dir / "summary.txt"

    sim = None
    left_motor = right_motor = None
    csv_file = None
    rows = []
    exit_status = 0

    try:
        print("STEP 5G - Paired Turn-Boundary Collection", flush=True)
        print(f"Session: {args.session_id} | role={args.role}", flush=True)
        print("W=forward, A=left, D=right; release keys to stop.", flush=True)
        print("Human controls motors. CNN inference is OFF.", flush=True)
        print("OpenCV GUI display is OFF.", flush=True)
        print(f"Session folder: {session_dir}", flush=True)

        import cv2
        import keyboard
        import numpy as np
        from coppeliasim_zmqremoteapi_client import RemoteAPIClient

        client = RemoteAPIClient()
        sim = client.require("sim")
        robot = sim.getObject("/PioneerP3DX")
        left_motor = sim.getObject("/PioneerP3DX/leftMotor")
        right_motor = sim.getObject("/PioneerP3DX/rightMotor")
        camera = sim.getObject(CAMERA_PATH)
        stop_motors(sim, left_motor, right_motor)

        fieldnames = [
            "timestamp_utc",
            "elapsed_seconds",
            "frame_index",
            "human_command",
            "image_relative_path",
            "robot_x",
            "robot_y",
            "robot_yaw",
        ]
        csv_file = metadata_path.open("w", newline="", encoding="utf-8")
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        csv_file.flush()

        print("READY: collector initialized. Start/resume CoppeliaSim.", flush=True)
        while sim.getSimulationState() in (
            sim.simulation_stopped,
            sim.simulation_paused,
        ):
            time.sleep(0.10)

        print(
            "SIMULATION RUNNING — W/A/D control + paired-boundary capture active.",
            flush=True,
        )
        run_started = time.monotonic()
        frame_index = 0

        while True:
            loop_started = time.monotonic()
            if sim.getSimulationState() in (
                sim.simulation_stopped,
                sim.simulation_paused,
            ):
                print("Simulation stopped; ending boundary session.", flush=True)
                break

            before_label, left_velocity, right_velocity = get_human_command(keyboard)
            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)

            raw_image, resolution = sim.getVisionSensorImg(camera)
            frame_rgb = convert_raw_image_rgb(raw_image, resolution, np)
            if not np.any(frame_rgb):
                stop_motors(sim, left_motor, right_motor)
                time.sleep(LOOP_INTERVAL_SECONDS)
                continue

            after_label, left_velocity, right_velocity = get_human_command(keyboard)
            sim.setJointTargetVelocity(left_motor, left_velocity)
            sim.setJointTargetVelocity(right_motor, right_velocity)
            stable_label = (
                before_label
                if before_label is not None and after_label == before_label
                else None
            )

            timestamp = datetime.now(timezone.utc)
            elapsed = time.monotonic() - run_started
            position = sim.getObjectPosition(robot, sim.handle_world)
            yaw = sim.getObjectOrientation(robot, sim.handle_world)[2]

            frame_index += 1
            image_name = (
                f"frame_{frame_index:06d}_"
                f"{timestamp.strftime('%Y%m%dT%H%M%S%fZ')}.jpg"
            )
            image_path = frames_dir / image_name
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            if not cv2.imwrite(str(image_path), frame_bgr):
                raise RuntimeError(f"Could not save {image_path}")

            row = {
                "timestamp_utc": timestamp.isoformat(),
                "elapsed_seconds": f"{elapsed:.3f}",
                "frame_index": str(frame_index),
                "human_command": stable_label or "",
                "image_relative_path": str(image_path.relative_to(session_dir)),
                "robot_x": f"{float(position[0]):.6f}",
                "robot_y": f"{float(position[1]):.6f}",
                "robot_yaw": f"{float(yaw):.6f}",
            }
            writer.writerow(row)
            csv_file.flush()
            rows.append(row)

            if frame_index == 1 or frame_index % 100 == 0:
                print(
                    f"t={elapsed:.1f}s frames={frame_index} "
                    f"human={stable_label or 'none':<7}",
                    flush=True,
                )

            remaining = LOOP_INTERVAL_SECONDS - (time.monotonic() - loop_started)
            if remaining > 0:
                time.sleep(remaining)

    except KeyboardInterrupt:
        print("Boundary collection stopped by user.", flush=True)
    except Exception as error:
        print(f"BOUNDARY COLLECTION ERROR: {error}", file=sys.stderr, flush=True)
        exit_status = 1
    finally:
        if sim is not None and not stop_motors(sim, left_motor, right_motor):
            exit_status = 1
        if csv_file is not None:
            csv_file.close()

        events = detect_boundary_events(rows)
        write_boundary_events(events_path, events)
        summary = build_summary(args.session_id, args.role, rows, events)
        summary_path.write_text(summary, encoding="utf-8")
        print(summary, end="", flush=True)
        print(f"Metadata: {metadata_path}", flush=True)
        print(f"Events: {events_path}", flush=True)
        print(f"Summary: {summary_path}", flush=True)

    return exit_status


if __name__ == "__main__":
    raise SystemExit(main())
