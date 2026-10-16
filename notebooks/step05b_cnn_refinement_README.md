# Step 5B CNN refinement

This is an internal quality gate between the accepted Step 5 training work and the professor's Step 6 autonomous-control work.

## Why this refinement exists

The clean Step-6A live shadow run of `maze_navigation_model_v2.h5` achieved 90.54% overall human/model agreement, but 72 of 833 human-forward frames were predicted as left (8.64%). Several false-left errors occurred in consecutive streaks. The model is therefore not yet connected to the robot motors.

## Controlled experiment

Run `notebooks/step05b_cnn_refinement.ipynb` in Google Colab.

The notebook deliberately keeps these items unchanged from v2:

- audited source dataset: `dataset_v2_clean_2383.zip`;
- expected class counts: forward 2137, left 121, right 125;
- random seed: 42;
- 70% / 15% / 15% stratified split;
- 50 x 50 RGB input;
- CNN architecture;
- Adam optimizer and sparse categorical cross-entropy;
- early stopping policy.

The only experimental variable is class-weight strength. Candidate alphas are 1.00, 0.75, 0.50, 0.25 and 0.00. Alpha 1.00 reproduces full balanced weighting; alpha 0.00 is an unweighted control. Intermediate weights are derived systematically from the balanced weights and normalized to mean sample weight 1.0.

## Leakage guardrail

All candidates are trained and ranked using validation data only. The untouched test set is evaluated once, after selection. If no moderated candidate reduces validation forward-to-left errors without unacceptable turn-performance loss, the notebook intentionally stops before test evaluation.

## Successful-run outputs

A successful run writes these files to `MyDrive/Intelligent_Robotics_Design_Project`:

- `maze_navigation_model_v3.h5`
- `step05b_candidate_validation_metrics.csv`
- `step05b_selected_config.json`
- `step05b_v3_test_metrics.json`

Preserve the executed Colab notebook as well. Do not overwrite or delete `maze_navigation_model_v2.h5`.

## Next gate

A successful offline v3 result is not enough to enable autonomy. v3 must next pass the same Step-6A live shadow-validation procedure against human W/A/D driving. Only after that gate is accepted should a Step-6 autonomous-navigation branch be created.
