# Step 6 bounded turn-continuation qualification plan — 2026-11-05

## Starting evidence

The first live turn qualification passed at pulse 72:
- prediction changed from forward to left;
- command = (0.10, 1.00);
- bounded turn pulse = 0.25 s;
- yaw changed from approximately -0.0011 rad to +0.0613 rad;
- motors stopped immediately;
- human visual observation confirmed a brief correct-looking left turn.

## Next gate

The next gate is not unrestricted autonomous navigation.

It is a bounded turn-continuation qualification with:
- unchanged persistent Step-4 Lua camera-save path;
- unchanged final simple perceptron;
- unchanged locked wheel speeds 1.00 / 0.10 / 1.00;
- forward pulse = 0.50 s;
- left/right pulse = 0.50 s;
- maximum total decisions = 80;
- after the first left/right decision, continue for at most 6 additional fresh-frame decisions;
- motors stop after every pulse;
- pose remains diagnostic only;
- visual supervision remains mandatory.

The hard pulse safety ceiling remains 0.50 s.

## Why not 0.75 s forward yet?

0.75 s would require deliberately raising the existing hard qualification ceiling. The first live turn has only just been established. The current 0.50 s forward pulse already approximately halves the fresh-frame count needed to reach the first corner compared with the earlier 0.25 s gate.

Keeping the ceiling at 0.50 s changes only the turn duration for the next gate and avoids introducing two new motion-duration variables at once.

## Why not 128 decisions yet?

The next question is whether repeated fresh camera decisions can continue the corner traversal after the first live turn.

A large 128-decision batch would mix that question with later-corridor behavior and would allow unnecessary travel if the turn does not continue correctly.

The 6-post-turn-decision cap isolates the immediate corner-continuation behavior first.

## Success evidence

The gate should demonstrate:
1. first turn is detected again;
2. one or more subsequent fresh frames continue to produce appropriate left/forward/right decisions;
3. the robot makes visible continued progress around the corner;
4. motors stop after every pulse;
5. the bounded post-turn limit ends the gate safely.

Only after this passes should a larger multi-turn or longer bounded batch be considered.
