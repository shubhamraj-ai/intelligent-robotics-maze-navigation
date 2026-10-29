# Professor-aligned Step 2 / Step 4 simplification Ã¢â‚¬â€ 2026-10-28

## Why this revision exists

The professor identified robot turning radius, travelling speed, training-data amount/distribution/quality, NN architecture, and random initialization as important factors in autonomous behaviour.

This branch deliberately returns to those fundamentals before any new Step-5 model work.

## Step 2 change

The original W/A/D motion used point turns:

- forward: (+2.0, +2.0)
- left: (-2.0, +2.0)
- right: (+2.0, -2.0)

The revised initial calibration profile is:

- forward: (+1.0, +1.0)
- left: (+0.10, +1.0)
- right: (+1.0, +0.10)

Manual calibration on 2026-10-29 found forward speed 1.00 and inner-wheel turn speed 0.10 to feel appropriate at the first corner in CoppeliaSim 4.9. These values are now the accepted Step-2 starting profile for continued full-maze validation.

They move both wheels forward during normal turns and therefore create curved differential-drive motion rather than an in-place pivot.

The values live in:

`config/motion_profile.json`

The profile must be manually validated through the complete maze before new training data is collected.

## Step 4 change

The recorder keeps the required W/A/D Ã¢â€ â€™ forward/left/right labels and the original three class folders.

It now:

- loads exactly the same motion profile used by Step 2;
- requires a command to remain stable for 0.20 s before saving;
- saves forward frames every 0.30 s;
- saves turn frames every 0.10 s;
- embeds a session ID in every filename;
- prints the class distribution at the end of the session;
- warns when a single class exceeds 70% of that session.

The purpose is to reduce redundant forward frames, reduce command-transition ambiguity, and preserve traversal/session identity for a cleaner Step-5 split.

## What this revision intentionally does NOT do

It does not:

- introduce a new neural network;
- use CNN class-weight tuning;
- add hard-negative mining;
- add boundary mining;
- add autonomous turn commitment;
- add route-specific logic;
- change Step 1 or Step 3.

## Next gate

Do not collect the replacement dataset yet.

First manually drive the full maze using Step 2 and tune only:

- `forward_speed`
- `turn_outer_speed`
- `turn_inner_speed`

until the robot can navigate smoothly and consistently.

Only after the motion profile is accepted should Step 4 be used for fresh data collection.

## Local simulator stability note — 2026-10-29

CoppeliaSim 4.7 repeatedly crashed on the current laptop with the native Windows
`ntdll.dll / 0xc0000374` heap-corruption signature.

CoppeliaSim 4.9.0 rev6 was stable long enough to validate:
- forward speed 1.00: good;
- turn inner speed 0.10 with outer speed 1.00: good at the first corner.

CoppeliaSim 4.9 later also closed/crashed during continued local testing. The
motion profile is therefore preserved, but further simulator work should move to
a more stable runtime environment rather than continue repeated local retries.
