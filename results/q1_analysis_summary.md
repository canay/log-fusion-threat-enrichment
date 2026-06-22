# Q1 Operating-Point and Validity Analyses

These analyses extend the closed VPS benchmark with reviewer-facing operating-point, temporal, and interpretability diagnostics. They use the same feature-exclusion policy as the manuscript: direct session identifiers, raw time fields, log type, and high-leakage policy fields are excluded from predictors.

## Scenario Summary

| scenario                      | test_rows | test_positives | test_prevalence | macro_f1 | average_precision | roc_auc | positive_precision | positive_recall | best_f1_threshold | best_f1 | best_f1_precision | best_f1_recall |
| ----------------------------- | --------- | -------------- | --------------- | -------- | ----------------- | ------- | ------------------ | --------------- | ----------------- | ------- | ----------------- | -------------- |
| xgboost_full_stratified       | 209716    | 3862           | 0.0184          | 0.5540   | 0.0939            | 0.6347  | 0.9094             | 0.0624          | 0.2529            | 0.1243  | 0.8520            | 0.0671         |
| xgboost_no_outcome_stratified | 209716    | 3862           | 0.0184          | 0.5286   | 0.0718            | 0.6352  | 0.7614             | 0.0347          | 0.0823            | 0.0939  | 0.3924            | 0.0533         |
| xgboost_full_temporal_holdout | 209716    | 3828           | 0.0183          | 0.5391   | 0.0782            | 0.6385  | 0.9162             | 0.0457          | 0.3099            | 0.0965  | 0.8376            | 0.0512         |


## Analyst-Budget View

| scenario                      | budget     | reviewed_sessions | true_positives | false_positives | precision | recall | lift_over_prevalence |
| ----------------------------- | ---------- | ----------------- | -------------- | --------------- | --------- | ------ | -------------------- |
| xgboost_full_stratified       | top_100    | 100               | 99             | 1               | 0.9900    | 0.0256 | 53.7594              |
| xgboost_full_stratified       | top_500    | 500               | 261            | 239             | 0.5220    | 0.0676 | 28.3459              |
| xgboost_full_stratified       | top_1000   | 1000              | 273            | 727             | 0.2730    | 0.0707 | 14.8246              |
| xgboost_full_stratified       | top_0.5pct | 1049              | 273            | 776             | 0.2602    | 0.0707 | 14.1321              |
| xgboost_full_stratified       | top_1pct   | 2097              | 296            | 1801            | 0.1412    | 0.0766 | 7.6650               |
| xgboost_no_outcome_stratified | top_100    | 100               | 89             | 11              | 0.8900    | 0.0230 | 48.3292              |
| xgboost_no_outcome_stratified | top_500    | 500               | 202            | 298             | 0.4040    | 0.0523 | 21.9382              |
| xgboost_no_outcome_stratified | top_1000   | 1000              | 219            | 781             | 0.2190    | 0.0567 | 11.8922              |
| xgboost_no_outcome_stratified | top_0.5pct | 1049              | 221            | 828             | 0.2107    | 0.0572 | 11.4403              |
| xgboost_no_outcome_stratified | top_1pct   | 2097              | 249            | 1848            | 0.1187    | 0.0645 | 6.4479               |
| xgboost_full_temporal_holdout | top_100    | 100               | 100            | 0               | 1.0000    | 0.0261 | 54.7847              |
| xgboost_full_temporal_holdout | top_500    | 500               | 198            | 302             | 0.3960    | 0.0517 | 21.6948              |
| xgboost_full_temporal_holdout | top_1000   | 1000              | 211            | 789             | 0.2110    | 0.0551 | 11.5596              |
| xgboost_full_temporal_holdout | top_0.5pct | 1049              | 212            | 837             | 0.2021    | 0.0554 | 11.0718              |
| xgboost_full_temporal_holdout | top_1pct   | 2097              | 234            | 1863            | 0.1116    | 0.0611 | 6.1133               |


## No-Outcome XGBoost Feature Importance

| feature            | importance |
| ------------------ | ---------- |
| Packets            | 0.2094     |
| Outbound Interface | 0.1722     |
| Risk of app        | 0.1052     |
| Destination Zone   | 0.0731     |
| Source Zone        | 0.0667     |
| Bytes Received     | 0.0600     |
| Application        | 0.0262     |
| Category of app    | 0.0249     |
| Destination Port   | 0.0226     |
| Bytes              | 0.0206     |
| SaaS of app        | 0.0205     |
| Subcategory of app | 0.0202     |

