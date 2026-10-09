"""Display the PioneerP3DX camera in OpenCV; stop with terminal Ctrl+C."""

import sys
import time


CAMERA_PATH = "/PioneerP3DX/cam1"
LOOP_INTERVAL_SECONDS = 0.10


def main():
    print("STEP 3 - Camera Streaming with OpenCV")
    print(f"Camera path: {CAMERA_PATH}")
    print("Start the simulation in CoppeliaSim; use terminal Ctrl+C to exit.")
    cv2 = None
    exit_status = 0

    try:
        import cv2
        import numpy as np
        from coppeliasim_zmqremoteapi_client import RemoteAPIClient

        client = RemoteAPIClient()
        sim = client.require("sim")
        try:
            camera_handle = sim.getObject(CAMERA_PATH)
            if camera_handle < 0:
                raise RuntimeError("CoppeliaSim returned an invalid object handle")
        except Exception as error:
            raise RuntimeError(f"Could not resolve camera {CAMERA_PATH}: {error}") from error

        resolution_printed = False
        while True:
            loop_started = time.monotonic()
            if sim.getSimulationState() in (sim.simulation_stopped, sim.simulation_paused):
                raise RuntimeError("Simulation is stopped or paused; start it in CoppeliaSim.")

            raw_image, resolution = sim.getVisionSensorImg(camera_handle)
            if len(resolution) != 2:
                raise ValueError(f"Expected [width, height], received {resolution}")
            width, height = resolution
            if not all(isinstance(value, int) and value > 0 for value in resolution):
                raise ValueError(f"Camera resolution must contain positive integers: {resolution}")
            expected_bytes = width * height * 3
            if len(raw_image) != expected_bytes:
                raise ValueError(
                    f"Expected {expected_bytes} RGB bytes, received {len(raw_image)}"
                )

            frame = np.frombuffer(raw_image, dtype=np.uint8).reshape(height, width, 3)
            # CoppeliaSim's image starts at the bottom and uses RGB channels.
            frame = cv2.flip(frame, 0)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            if not resolution_printed:
                print(f"Live resolution: {width} x {height}")
                resolution_printed = True
            cv2.imshow("PioneerP3DX Camera Feed", frame)
            cv2.waitKey(1)

            remaining = LOOP_INTERVAL_SECONDS - (time.monotonic() - loop_started)
            if remaining > 0:
                time.sleep(remaining)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f"STEP 3 ERROR: {error}", file=sys.stderr)
        exit_status = 1
    finally:
        if cv2 is not None:
            try:
                cv2.destroyAllWindows()
            except Exception as error:
                print(f"STEP 3 ERROR: Could not close OpenCV windows: {error}", file=sys.stderr)
                exit_status = 1

    return exit_status


if __name__ == "__main__":
    sys.exit(main())
