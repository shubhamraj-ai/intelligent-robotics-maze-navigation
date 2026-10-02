"""Validate the objects and robot pose needed for Step 1."""

import sys

from coppeliasim_zmqremoteapi_client import RemoteAPIClient


def main():
    print("Attempting to connect to the local CoppeliaSim ZMQ Remote API...")

    try:
        client = RemoteAPIClient()
        sim = client.require("sim")
        print("Connection to CoppeliaSim succeeded.")
    except Exception as error:
        print(f"STEP 1 ERROR: Could not connect to CoppeliaSim: {error}", file=sys.stderr)
        print(
            "Check that CoppeliaSim is running and the ZMQ Remote API is enabled.",
            file=sys.stderr,
        )
        return 1

    try:
        floor_handle = sim.getObject("/Floor")
        if floor_handle == -1:
            raise RuntimeError("CoppeliaSim returned an invalid object handle")
        print("Successfully retrieved the /Floor scene object.")
        print(f"Object handle: {floor_handle}")
    except Exception as error:
        print(f"STEP 1 ERROR: Could not find /Floor: {error}", file=sys.stderr)
        print(
            "Check that the open scene contains an object named /Floor.",
            file=sys.stderr,
        )
        return 1

    required_paths = [
        "/PioneerP3DX",
        "/PioneerP3DX/leftMotor",
        "/PioneerP3DX/rightMotor",
        "/PioneerP3DX/cam1",
    ]
    object_handles = {}

    for object_path in required_paths:
        try:
            object_handle = sim.getObject(object_path)
            if object_handle == -1:
                raise RuntimeError("CoppeliaSim returned an invalid object handle")
        except Exception as error:
            print(
                f"STEP 1 ERROR: Could not find {object_path}: {error}",
                file=sys.stderr,
            )
            return 1

        object_handles[object_path] = object_handle
        print(f"Resolved {object_path} -> handle {object_handle}")

    robot_handle = object_handles["/PioneerP3DX"]

    try:
        position = sim.getObjectPosition(robot_handle, sim.handle_world)
        orientation = sim.getObjectOrientation(robot_handle, sim.handle_world)
    except Exception as error:
        print(f"STEP 1 ERROR: Could not read the robot pose: {error}", file=sys.stderr)
        return 1

    print(f"Robot world position [x, y, z]: {position}")
    print(f"Robot world orientation [alpha, beta, gamma]: {orientation}")
    print("STEP 1 PASS")

    return 0


if __name__ == "__main__":
    sys.exit(main())
