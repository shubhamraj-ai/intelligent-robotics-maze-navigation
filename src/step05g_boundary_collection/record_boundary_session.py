"""Low-I/O paired turn-boundary collector for Step 5G.

Human W/A/D controls the PioneerP3DX. No CNN inference is performed.
The collector keeps only a small rolling camera buffer in memory and writes
images to disk when a complete forward->left/right boundary is observed:
five stable forward frames before onset and five stable true-turn frames after.

This avoids the continuous JPEG write load used by the first Step 5G attempt.
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path

CLASS_NAMES = ("forward", "left", "right")
FORWARD_SPEED = 2.0
TURN_SPEED = 2.0
LOOP_INTERVAL_SECONDS = 0.10
CAMERA_PATH = "/PioneerP3DX/cam1"
BOUNDARY_FRAMES = 5
RING_SIZE = 40
METADATA_FLUSH_EVERY = 25
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "boundary_sessions"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Low-I/O human-controlled paired turn-boundary collection."
    )
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--role", choices=("train", "validation"), required=True)
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


def recent_forward_samples(ring, count=BOUNDARY_FRAMES):
    """Return the most recent contiguous stable-forward samples.

    Blank samples are ignored. Encountering a stable left/right sample stops
    the backward search so a previous turn cannot leak into a new boundary.
    """
    selected = []
    for sample in reversed(ring):
        command = sample["human_command"]
        if command is None:
            continue
        if command != "forward":
            break
        selected.append(sample)
        if len(selected) == count:
            break
    if len(selected) != count:
        return []
    selected.reverse()
    return selected


def save_completed_event(
    event_id,
    pending,
    session_dir,
    samples_writer,
    cv2_module,
):
    event_dir = session_dir / "boundary_images" / f"event_{event_id:02d}_{pending['turn']}"
    event_dir.mkdir(parents=True, exist_ok=False)

    samples = []
    for offset, sample in zip(
        range(-BOUNDARY_FRAMES, 0),
        pending["pre"],
    ):
        samples.append(("pre_forward", offset, sample))
    for offset, sample in enumerate(pending["post"]):
        samples.append(("post_turn", offset, sample))

    for side, offset, sample in samples:
        image_name = (
            f"{side}_{offset:+03d}_frame_{sample['frame_index']:06d}.jpg"
        )
        image_path = event_dir / image_name
        frame_bgr = cv2_module.cvtColor(
            sample["frame_rgb"],
            cv2_module.COLOR_RGB2BGR,
        )
        if not cv2_module.imwrite(str(image_path), frame_bgr):
            raise RuntimeError(f"Could not save boundary image: {image_path}")

        samples_writer.writerow(
            {
                "event_id": event_id,
                "turn_class": pending["turn"],
                "boundary_side": side,
                "relative_offset": offset,
                "frame_index": sample["frame_index"],
                "timestamp_utc": sample["timestamp_utc"],
                "elapsed_seconds": sample["elapsed_seconds"],
                "human_command": sample["human_command"],
                "image_relative_path": str(image_path.relative_to(session_dir)),
                "robot_x": sample["robot_x"],
                "robot_y": sample["robot_y"],
                "robot_yaw": sample["robot_yaw"],
            }
        )


def build_summary(session_id, role, rows, completed_events, discarded_events):
    scored = [row for row in rows if row["human_command"] in CLASS_NAMES]
    counts = Counter(row["human_command"] for row in scored)
    left_events = sum(event["turn"] == "left" for event in completed_events)
    right_events = sum(event["turn"] == "right" for event in completed_events)

    return "\n".join(
        [
            "STEP 5G PAIRED BOUNDARY COLLECTION SUMMARY",
            "",
            f"Session ID: {session_id}",
            f"Role: {role}",
            f"Metadata samples: {len(rows)}",
            f"Stable-command samples: {len(scored)}",
            f"Forward samples: {counts['forward']}",
            f"Left samples: {counts['left']}",
            f"Right samples: {counts['right']}",
            f"Completed left-boundary events: {left_events}",
            f"Completed right-boundary events: {right_events}",
            f"Discarded incomplete boundary events: {discarded_events}",
            f"Saved images: {len(completed_events) * BOUNDARY_FRAMES * 2}",
            f"Boundary frames per side: {BOUNDARY_FRAMES}",
            "",
            "CNN inference: OFF",
            "OpenCV GUI display: OFF",
            "Continuous JPEG writing: OFF",
            "Only completed boundary-event images are written to disk.",
            "Human W/A/D commands controlled the motors.",
            "",
        ]
    )


def main(argv=None):
    args = parse_args(argv)
    output_root = args.output_root.resolve()
    session_dir = output_root / args.session_id

    if session_dir.exists():
        raise FileExistsError(f"Session already exists: {session_dir}")
    session_dir.mkdir(parents=True)

    metadata_path = session_dir / "metadata.csv"
    samples_path = session_dir / "boundary_samples.csv"
    summary_path = session_dir / "summary.txt"

    sim = None
    left_motor = right_motor = None
    metadata_file = samples_file = None
    rows = []
    ring = deque(maxlen=RING_SIZE)
    pending = None
    completed_events = []
    discarded_events = 0
    previous_stable_command = None
    exit_status = 0

    try:
        print("STEP 5G - Low-I/O Paired Turn-Boundary Collection", flush=True)
        print(f"Session: {args.session_id} | role={args.role}", flush=True)
        print("W=forward, A=left, D=right; release keys to stop.", flush=True)
        print("Human controls motors. CNN inference is OFF.", flush=True)
        print("OpenCV GUI display is OFF.", flush=True)
        print("Continuous JPEG writing is OFF.", flush=True)
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

        metadata_fields = [
            "timestamp_utc",
            "elapsed_seconds",
            "frame_index",
            "human_command",
            "robot_x",
            "robot_y",
            "robot_yaw",
        ]
        sample_fields = [
            "event_id",
            "turn_class",
            "boundary_side",
            "relative_offset",
            "frame_index",
            "timestamp_utc",
            "elapsed_seconds",
            "human_command",
            "image_relative_path",
            "robot_x",
            "robot_y",
            "robot_yaw",
        ]

        metadata_file = metadata_path.open("w", newline="", encoding="utf-8")
        samples_file = samples_path.open("w", newline="", encoding="utf-8")
        metadata_writer = csv.DictWriter(metadata_file, fieldnames=metadata_fields)
        samples_writer = csv.DictWriter(samples_file, fieldnames=sample_fields)
        metadata_writer.writeheader()
        samples_writer.writeheader()
        metadata_file.flush()
        samples_file.flush()

        print("READY: collector initialized. Start/resume CoppeliaSim.", flush=True)
        while sim.getSimulationState() in (
            sim.simulation_stopped,
            sim.simulation_paused,
        ):
            time.sleep(0.10)

        print(
            "SIMULATION RUNNING — W/A/D + low-I/O boundary capture active.",
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

            sample = {
                "timestamp_utc": timestamp.isoformat(),
                "elapsed_seconds": f"{elapsed:.3f}",
                "frame_index": frame_index,
                "human_command": stable_label,
                "robot_x": f"{float(position[0]):.6f}",
                "robot_y": f"{float(position[1]):.6f}",
                "robot_yaw": f"{float(yaw):.6f}",
                "frame_rgb": frame_rgb,
            }

            metadata_row = {
                key: (sample[key] if sample[key] is not None else "")
                for key in metadata_fields
            }
            metadata_writer.writerow(metadata_row)
            rows.append(metadata_row)
            if frame_index % METADATA_FLUSH_EVERY == 0:
                metadata_file.flush()

            # Complete or invalidate a pending turn event first.
            if pending is not None and stable_label is not None:
                if stable_label == pending["turn"]:
                    pending["post"].append(sample.copy())
                    if len(pending["post"]) == BOUNDARY_FRAMES:
                        event_id = len(completed_events) + 1
                        save_completed_event(
                            event_id,
                            pending,
                            session_dir,
                            samples_writer,
                            cv2,
                        )
                        samples_file.flush()
                        completed_events.append(
                            {
                                "event_id": event_id,
                                "turn": pending["turn"],
                                "onset_frame_index": pending["post"][0]["frame_index"],
                            }
                        )
                        print(
                            f"BOUNDARY EVENT SAVED: id={event_id} "
                            f"turn={pending['turn']} "
                            f"onset_frame={pending['post'][0]['frame_index']}",
                            flush=True,
                        )
                        pending = None
                elif stable_label != pending["turn"]:
                    discarded_events += 1
                    pending = None

            # Start a new event only on a forward -> turn stable-command edge.
            if (
                pending is None
                and stable_label in ("left", "right")
                and previous_stable_command == "forward"
            ):
                pre = recent_forward_samples(ring)
                if len(pre) == BOUNDARY_FRAMES:
                    pending = {
                        "turn": stable_label,
                        "pre": [
                            {**item, "frame_rgb": item["frame_rgb"].copy()}
                            for item in pre
                        ],
                        "post": [sample.copy()],
                    }

            ring.append(sample)

            if stable_label is not None:
                previous_stable_command = stable_label

            if frame_index == 1 or frame_index % 100 == 0:
                print(
                    f"t={elapsed:.1f}s frames={frame_index} "
                    f"human={stable_label or 'none':<7} "
                    f"events={len(completed_events)}",
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
        if pending is not None:
            discarded_events += 1
        if metadata_file is not None:
            metadata_file.flush()
            metadata_file.close()
        if samples_file is not None:
            samples_file.flush()
            samples_file.close()

        summary = build_summary(
            args.session_id,
            args.role,
            rows,
            completed_events,
            discarded_events,
        )
        summary_path.write_text(summary, encoding="utf-8")
        print(summary, end="", flush=True)
        print(f"Metadata: {metadata_path}", flush=True)
        print(f"Boundary samples: {samples_path}", flush=True)
        print(f"Summary: {summary_path}", flush=True)

    return exit_status


if __name__ == "__main__":
    raise SystemExit(main())
