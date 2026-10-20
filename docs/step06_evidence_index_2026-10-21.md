# Step 6 evidence index — 2026-10-21

## Purpose

This index provides a compact map of the Step 6 evidence already captured so final academic writing can reference verified artefacts instead of reconstructing the history from memory.

## Primary evidence documents

1. `step2_crash_isolation_2026-10-18.md`
   - CoppeliaSim crash-isolation work and stable/unstable diagnostic combinations.

2. `step05c_recovery_audit_2026-10-17.md`
   - temporal-leakage diagnosis and recovery-session evidence.

3. `step05c_v4_colab_results_2026-10-17.md`
   - session-aware v4 offline result.

4. `step05c_v4_live_shadow_2026-10-17.md`
   - fresh v4 live-shadow result and failure.

5. `step05d_v5_calibration_results_2026-10-17.md`
   - class-weight calibration evidence.

6. `step05d_alpha050_nodisplay_shadow_2026-10-18.md`
   - alpha-0.50 live no-display shadow result.

7. `step05e_clean_hard_negative_result_and_v6_plan_2026-10-18.md`
   - clean hard-negative capture and targeted v6 experiment design.

8. `step05f_v6_colab_results_2026-10-18.md`
   - v6 offline result and reason for rejecting forward-only hard-negative retraining.

9. `step05g_paired_boundary_collection_plan_2026-10-18.md`
   - paired boundary collection design and low-I/O revision.

10. `step05g_boundary_train01_result_2026-10-18.md`
    - first paired-boundary training traversal.

11. `step05g_boundary_train02_result_2026-10-20.md`
    - second paired-boundary training traversal.

12. `step05g_boundary_validation01_and_step05h_v7_plan_2026-10-21.md`
    - held-out boundary-validation collection and pre-committed v7 gate.

13. `step05h_v7_colab_results_2026-10-21.md`
    - v7 offline result, gate failure, and observability audit.

14. `step06_consolidated_evidence_checkpoint_2026-10-21.md`
    - current Step 6 technical checkpoint and hold rules.

15. `step06_professor_response_decision_matrix_2026-10-21.md`
    - pre-defined next actions based on professor guidance.

## Key non-code artefacts

Local/Drive model artefacts produced during the investigation include:
- v3, v4, calibrated alpha-0.50, v6, and v7 CNN model artefacts;
- session-aware metrics JSON files;
- confusion matrices;
- training histories;
- recovery-session logs;
- live-shadow logs;
- hard-negative collection logs;
- paired-boundary training and held-out-validation image sets.

## Current academic narrative

The evidence supports the following concise narrative:

1. The initial CNN appeared strong under random frame-level validation.
2. Closed-loop autonomous navigation exposed poor generalisation around turns.
3. Audit showed temporal near-duplicate leakage from sequential image capture.
4. Whole-session evaluation corrected the validation methodology.
5. Recovery data and class-weight tuning improved performance but did not remove premature turn decisions.
6. Forward-only hard negatives reduced some false turns but degraded legitimate turn recall.
7. Paired pre/post-turn examples improved turn recognition but still failed to distinguish the exact pre-turn command boundary.
8. A pixel-level audit showed the human W->A/D transition often has no unique single-frame visual discontinuity.
9. The remaining Step 6 question is therefore one of target observability/control interpretation, now escalated to the professor for scope clarification.

This is the preferred evidence-backed storyline for later academic reporting.
