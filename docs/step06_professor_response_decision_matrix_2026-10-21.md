# Step 6 professor-response decision matrix — 2026-10-21

## Purpose

This document defines the next action before the professor replies so the project can resume quickly without inventing a new direction after seeing the response.

## Response path A — direct prediction from each individual frame is required

If the professor explicitly says Step 6 should directly use one prediction per camera frame with no smoothing/state logic:

Next action:
- do not add controller smoothing;
- redesign the training target so the label boundary is visually observable rather than tied to the exact keyboard-transition instant;
- use the existing Step 5G data first;
- define and freeze an observable turn-zone/relabeling rule before retraining;
- retain the same 50x50 image input and three output classes unless the professor instructs otherwise.

Validation:
- whole-session recovery validation;
- independent boundary-specific validation;
- then one fresh live shadow;
- autonomous only after live shadow passes.

## Response path B — smoothing / temporal confirmation is allowed

If the professor says the CNN may be wrapped with a small temporal decision mechanism:

Implement the smallest professor-aligned controller first.

Preferred first experiment:
- keep the best currently justified CNN baseline;
- keep human-labelled classes unchanged;
- require a short confirmation window before switching from forward to left/right;
- release the turn only after a similarly simple confirmation condition;
- no long commitment timer and no complex route-specific heuristics.

The exact window/threshold must be fixed before the live test.

Validation:
- replay/offline sequential logs first;
- then fresh human-controlled no-display shadow;
- then one cautious autonomous run only if the shadow gate passes.

## Response path C — both visual relabeling and smoothing are allowed

Use the simplest combination:
1. make the training target visually consistent;
2. use minimal temporal confirmation to reject one-frame noise;
3. avoid route-specific hardcoding.

The goal is not maximum sophistication. The goal is a stable, explainable Step 6 that remains clearly within the assignment's CNN-navigation intent.

## Response path D — professor recommends another specific method

Follow the professor's method unless it conflicts with a technical impossibility or the written assignment.

Before coding:
- translate the professor's recommendation into a precise implementation contract;
- identify which existing data/code remains valid;
- identify which previous experiments become obsolete;
- define the validation gate;
- only then modify code.

## Response path E — no reply by the planned waiting limit

If no reply is received by the user's chosen waiting limit, proceed with the least invasive academically defensible option:
- first perform an offline design of visually observable turn-zone labels;
- do not yet run autonomous control;
- keep the current evidence and professor question documented;
- preserve the option to adapt immediately when a reply arrives.

## Non-negotiable engineering rules

Regardless of the response:
- no return to random frame-level train/test splitting;
- no claim that the old ~95% random-frame score proves independent generalisation;
- no merging PR #13 while the Step 6 direction is unresolved;
- no autonomous promotion from offline accuracy alone;
- no route-specific controller hacks merely to force a successful video.
