# Pause checkpoint — 2026-10-17

## Current state

Work paused after the alpha-0.50 diagnostic live-shadow retry caused CoppeliaSim Edu 4.7.0 rev4 to terminate unexpectedly shortly after manual W/A/D driving began.

The alpha-0.50 model itself had already passed local load/warm-up validation:

- file: maze_navigation_model_alpha050_shadow.h5
- SHA256: 6885FDAD3C143B3039109AE59F68A93C5941605AD2AC53CD8B5A16D76ADE5535
- input: (None, 50, 50, 3)
- output: (None, 3)
- parameters: 89,379

The first partial alpha-0.50 shadow attempt ended cleanly when the user stopped the simulation:
- 149 scored frames
- agreement 97.32%
- forward 136/136 correct
- left recall 69.23% on 13 frames
- no right-turn frames reached
This partial attempt is not a valid gate result.

## Crash evidence

Windows Error Reporting recorded an APPCRASH for:

- application: coppeliaSim.exe
- installed path: C:\Users\Admin\Applications\CoppeliaSim_Edu_V4_7_0_rev4\coppeliaSim.exe
- exception code: c0000374
- fault module: StackHash_bfee / ntdll

Exception c0000374 is consistent with Windows heap-corruption detection. A crash dump/report was queued under Windows Error Reporting.

The crash occurred at the simulator/process level. No evidence from the shadow validator indicates that the CNN model itself failed to load or violated its input/output contract.

## Resume gate

Do not run autonomous Step 6.

On resume:
1. start from a clean CoppeliaSim 4.7 scene reset;
2. investigate simulator stability before repeating shadow validation;
3. keep alpha-0.50 shadow-only;
4. repeat a complete fresh live-shadow traversal only after CoppeliaSim stability is confirmed;
5. compare forward false-turn rate, longest false-turn streak, and turn recall against v4.

PR #13 remains draft/open.
