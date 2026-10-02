"""Check that Python can connect to CoppeliaSim and find the scene floor."""

import sys

from coppeliasim_zmqremoteapi_client import RemoteAPIClient


def main():
    print("Attempting to connect to the local CoppeliaSim ZMQ Remote API...")

    try:
        client = RemoteAPIClient()
        sim = client.require("sim")
        print("Connection to CoppeliaSim succeeded.")

        floor_handle = sim.getObject("/Floor")
        print("Successfully retrieved the /Floor scene object.")
        print(f"Object handle: {floor_handle}")
        print("STEP 1B PASS")
    except Exception as error:
        print(f"STEP 1B ERROR: {error}", file=sys.stderr)
        print(
            "Check that CoppeliaSim is running, the ZMQ Remote API is enabled, "
            "and the scene contains an object named /Floor.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
