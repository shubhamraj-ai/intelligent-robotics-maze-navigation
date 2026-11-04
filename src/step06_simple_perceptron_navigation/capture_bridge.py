"""Reuse the proven Step-4 persistent capture signal for Step-6 frames.

The stable Step-4 persistent Lua script saves a JPEG only while the small
`step4_capture_label` string signal contains one of the known labels.
For Step 6 the value "forward" is used strictly as a capture-enable token.
The generated filenames are runtime observation frames and must never be
re-finalized into the Step-5 training dataset.
"""

from __future__ import annotations


CAPTURE_LABEL_SIGNAL = "step4_capture_label"
CAPTURE_ENABLE_TOKEN = "forward"


def enable_existing_step4_capture(sim) -> str:
    sim.setStringSignal(CAPTURE_LABEL_SIGNAL, CAPTURE_ENABLE_TOKEN)
    return CAPTURE_ENABLE_TOKEN


def disable_existing_step4_capture(sim) -> bool:
    try:
        sim.setStringSignal(CAPTURE_LABEL_SIGNAL, "")
        return True
    except Exception:
        return False
