# Phase 3 model release

The first release uses a transparent logistic-regression xPass baseline and a training-match-only 12×8 xT grid. Match IDs are split before fitting: 42 training matches, 10 validation matches, and 10 held-out test matches. Missing 360-derived features are median-imputed with missingness indicators; they never receive inferred player identities.

Probability calibration uses isotonic regression fitted only on validation-match predictions. The test set is not used to fit either the xPass estimator, xT grid, or calibrator.

## Held-out result

| Metric | Result |
| --- | ---: |
| Brier score | 0.1147 |
| Match-bootstrap 95% Brier interval | 0.1046–0.1232 |
| Log loss | 0.3638 |
| ROC-AUC | 0.8135 |
| Expected calibration error | 0.0110 |

The model scores 375,508 visible candidate endpoints. Each score records `p_success`, xT start/end/delta, expected positive threat, a model version, and a visible-360 coverage flag. These values are estimates under a selected-action training distribution; they do not establish that an unattempted alternative would have succeeded.

Outputs are local, versioned artifacts: `models/xpass_logistic.joblib`, `models/xt_grid.npz`, `data/gold/candidate_scores.parquet`, and the calibration PNG/SVG plus metrics under `reports/evaluation/`.
