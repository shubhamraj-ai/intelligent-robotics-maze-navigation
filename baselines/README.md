# Baseline Evidence Guide

The baseline names are project-defined engineering checkpoints used to preserve stable states during iterative testing.

## Golden
golden_navigation_run.txt is the compact evidence log from the first preserved full autonomous-navigation gate. It records four right-turn triggers/releases and a perception-driven terminal stop.

## Diamond
The Diamond folder preserves the navigation source/model immediately before later simplification, together with the Step-7 live navigation log and ultrasonic sensor geometry.

## Platinum
The Platinum baseline preserves a simplified traversal-capable controller. It demonstrated that the NN could naturally perform the paired right-turn region, but its internal state counter could remain one turn behind near the terminal region.

## Platinum V2
The V2 baseline corrected that bookkeeping issue by recognising sustained NN-right behaviour instead of forcing another turn. The representative clean acceptance run recorded:
- 486 movement pulses
- 483 NN actions applied directly
- 3 supervisory overrides
- 99.38% prediction-to-applied-action agreement
- full-maze completion and terminal stop

The report should describe these as validation checkpoints, not as separate algorithms.
