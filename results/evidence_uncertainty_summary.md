# Evidence-Family and Calibration Analysis

This analysis decomposes the linked-event prediction task by operational evidence families. All rows use the same stratified 80/20 split and the same XGBoost configuration as the main manuscript.

## Evidence-Family Summary

| evidence_family            | features | macro_f1 | balanced_accuracy | average_precision | roc_auc | positive_precision | positive_recall | brier_score | ece_10bin | top_100_precision | top_500_precision | fit_predict_seconds | device_used |
| -------------------------- | -------- | -------- | ----------------- | ----------------- | ------- | ------------------ | --------------- | ----------- | --------- | ----------------- | ----------------- | ------------------- | ----------- |
| traffic_context_only       | 17       | 0.5044   | 0.5045            | 0.0355            | 0.6232  | 0.9722             | 0.0091          | 0.0179      | 0.0001    | 0.3900            | 0.0980            | 39.4533             | cpu         |
| volume_only                | 7        | 0.5281   | 0.5169            | 0.0672            | 0.6307  | 0.8344             | 0.0339          | 0.0175      | 0.0002    | 0.8700            | 0.3500            | 22.3395             | cpu         |
| policy_action_only         | 3        | 0.4954   | 0.5000            | 0.0337            | 0.6331  | 0.0000             | 0.0000          | 0.0178      | 0.0002    | 0.1200            | 0.1320            | 16.7472             | cpu         |
| context_plus_volume        | 24       | 0.5284   | 0.5171            | 0.0719            | 0.6347  | 0.7733             | 0.0344          | 0.0174      | 0.0002    | 0.8700            | 0.4020            | 40.3836             | cpu         |
| context_plus_policy_action | 20       | 0.5074   | 0.5061            | 0.0575            | 0.6316  | 0.9592             | 0.0122          | 0.0177      | 0.0001    | 0.5800            | 0.2860            | 38.0337             | cpu         |
| full_core                  | 27       | 0.5544   | 0.5314            | 0.0946            | 0.6336  | 0.9033             | 0.0629          | 0.0170      | 0.0002    | 1.0000            | 0.5260            | 37.5084             | cpu         |


## Top-k Operating Points

| evidence_family            | k    | true_positives | false_positives | precision | recall | lift_over_prevalence |
| -------------------------- | ---- | -------------- | --------------- | --------- | ------ | -------------------- |
| traffic_context_only       | 10   | 10             | 0               | 1.0000    | 0.0026 | 54.3024              |
| traffic_context_only       | 50   | 39             | 11              | 0.7800    | 0.0101 | 42.3559              |
| traffic_context_only       | 100  | 39             | 61              | 0.3900    | 0.0101 | 21.1779              |
| traffic_context_only       | 250  | 44             | 206             | 0.1760    | 0.0114 | 9.5572               |
| traffic_context_only       | 500  | 49             | 451             | 0.0980    | 0.0127 | 5.3216               |
| traffic_context_only       | 1000 | 62             | 938             | 0.0620    | 0.0161 | 3.3668               |
| volume_only                | 10   | 10             | 0               | 1.0000    | 0.0026 | 54.3024              |
| volume_only                | 50   | 46             | 4               | 0.9200    | 0.0119 | 49.9582              |
| volume_only                | 100  | 87             | 13              | 0.8700    | 0.0225 | 47.2431              |
| volume_only                | 250  | 159            | 91              | 0.6360    | 0.0412 | 34.5363              |
| volume_only                | 500  | 175            | 325             | 0.3500    | 0.0453 | 19.0059              |
| volume_only                | 1000 | 204            | 796             | 0.2040    | 0.0528 | 11.0777              |
| policy_action_only         | 10   | 0              | 10              | 0.0000    | 0.0000 | 0.0000               |
| policy_action_only         | 50   | 9              | 41              | 0.1800    | 0.0023 | 9.7744               |
| policy_action_only         | 100  | 12             | 88              | 0.1200    | 0.0031 | 6.5163               |
| policy_action_only         | 250  | 34             | 216             | 0.1360    | 0.0088 | 7.3851               |
| policy_action_only         | 500  | 66             | 434             | 0.1320    | 0.0171 | 7.1679               |
| policy_action_only         | 1000 | 140            | 860             | 0.1400    | 0.0363 | 7.6023               |
| context_plus_volume        | 10   | 10             | 0               | 1.0000    | 0.0026 | 54.3024              |
| context_plus_volume        | 50   | 46             | 4               | 0.9200    | 0.0119 | 49.9582              |
| context_plus_volume        | 100  | 87             | 13              | 0.8700    | 0.0225 | 47.2431              |
| context_plus_volume        | 250  | 168            | 82              | 0.6720    | 0.0435 | 36.4912              |
| context_plus_volume        | 500  | 201            | 299             | 0.4020    | 0.0520 | 21.8296              |
| context_plus_volume        | 1000 | 225            | 775             | 0.2250    | 0.0583 | 12.2180              |
| context_plus_policy_action | 10   | 10             | 0               | 1.0000    | 0.0026 | 54.3024              |
| context_plus_policy_action | 50   | 48             | 2               | 0.9600    | 0.0124 | 52.1303              |
| context_plus_policy_action | 100  | 58             | 42              | 0.5800    | 0.0150 | 31.4954              |
| context_plus_policy_action | 250  | 93             | 157             | 0.3720    | 0.0241 | 20.2005              |
| context_plus_policy_action | 500  | 143            | 357             | 0.2860    | 0.0370 | 15.5305              |
| context_plus_policy_action | 1000 | 230            | 770             | 0.2300    | 0.0596 | 12.4896              |
| full_core                  | 10   | 10             | 0               | 1.0000    | 0.0026 | 54.3024              |
| full_core                  | 50   | 50             | 0               | 1.0000    | 0.0129 | 54.3024              |
| full_core                  | 100  | 100            | 0               | 1.0000    | 0.0259 | 54.3024              |
| full_core                  | 250  | 234            | 16              | 0.9360    | 0.0606 | 50.8271              |
| full_core                  | 500  | 263            | 237             | 0.5260    | 0.0681 | 28.5631              |
| full_core                  | 1000 | 276            | 724             | 0.2760    | 0.0715 | 14.9875              |


## Runtime Profile

| stage                   | evidence_family            | seconds  | rows    | test_rows | device_requested | device_used |
| ----------------------- | -------------------------- | -------- | ------- | --------- | ---------------- | ----------- |
| data_load               | all                        | 13.4642  | 1048576 |           | cpu              |             |
| fit_predict_calibration | traffic_context_only       | 41.7408  | 1048576 | 209716    | cpu              | cpu         |
| fit_predict_calibration | volume_only                | 23.1593  | 1048576 | 209716    | cpu              | cpu         |
| fit_predict_calibration | policy_action_only         | 17.5900  | 1048576 | 209716    | cpu              | cpu         |
| fit_predict_calibration | context_plus_volume        | 43.1504  | 1048576 | 209716    | cpu              | cpu         |
| fit_predict_calibration | context_plus_policy_action | 40.7506  | 1048576 | 209716    | cpu              | cpu         |
| fit_predict_calibration | full_core                  | 40.4219  | 1048576 | 209716    | cpu              | cpu         |
| total_python_runtime    | all                        | 221.2417 | 1048576 | 209716    | cpu              |             |

