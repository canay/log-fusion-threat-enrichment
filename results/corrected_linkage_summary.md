# Corrected Same-Session Linkage Results

- Corrected positives: 1,233 / 1,048,576 (0.1176%).
- Primary split: later chronological, composite-session group-disjoint; train/test positives 1033/200; group overlap 0.
- Exact direct tuple rows: 1,233; NAT-aware tuple rows: 1,233.
- Random-ranking AP: 0.000953; DNS-rule AP: 0.003946.

## Model results

| evaluation            | model               | feature_set   |   seed |   macro_f1 |   average_precision |   roc_auc |   positive_precision |   positive_recall |   tp |     fp |
|:----------------------|:--------------------|:--------------|-------:|-----------:|--------------------:|----------:|---------------------:|------------------:|-----:|-------:|
| primary_later_20pct   | XGBoost             | full_core     |     42 |   0.927768 |            0.957801 |  0.998729 |             0.882979 |          0.830000 |  166 |     22 |
| primary_later_20pct   | XGBoost             | no_outcome    |     42 |   0.786355 |            0.560048 |  0.986827 |             0.671141 |          0.500000 |  100 |     49 |
| primary_later_20pct   | XGBoost             | hard_proxy    |     42 |   0.752055 |            0.507609 |  0.978093 |             0.631579 |          0.420000 |   84 |     49 |
| primary_later_20pct   | Extra Trees         | no_outcome    |     42 |   0.786336 |            0.500581 |  0.933916 |             0.653846 |          0.510000 |  102 |     54 |
| primary_later_20pct   | LightGBM            | no_outcome    |     42 |   0.710074 |            0.543099 |  0.982864 |             0.286486 |          0.795000 |  159 |    396 |
| primary_later_20pct   | CatBoost            | no_outcome    |     42 |   0.583339 |            0.463676 |  0.991980 |             0.094789 |          0.855000 |  171 |   1633 |
| primary_later_20pct   | Logistic Regression | no_outcome    |     42 |   0.329215 |            0.001749 |  0.725489 |             0.001764 |          0.950000 |  190 | 107537 |
| primary_later_20pct   | XGBoost             | no_outcome    |     13 |   0.771763 |            0.565012 |  0.993019 |             0.627451 |          0.480000 |   96 |     57 |
| primary_later_20pct   | XGBoost             | no_outcome    |     73 |   0.770993 |            0.542622 |  0.989689 |             0.623377 |          0.480000 |   96 |     58 |
| primary_later_20pct   | XGBoost             | no_outcome    |    101 |   0.779017 |            0.562347 |  0.992769 |             0.649007 |          0.490000 |   98 |     53 |
| primary_later_20pct   | XGBoost             | no_outcome    |    137 |   0.784720 |            0.589133 |  0.992182 |             0.662252 |          0.500000 |  100 |     51 |
| rolling_origin_fold_1 | XGBoost             | no_outcome    |     42 |   0.852933 |            0.691716 |  0.988303 |             0.818681 |          0.620833 |  149 |     33 |
| rolling_origin_fold_2 | XGBoost             | no_outcome    |     42 |   0.856335 |            0.643054 |  0.982053 |             0.769231 |          0.664557 |  210 |     63 |
| rolling_origin_fold_3 | XGBoost             | no_outcome    |     42 |   0.786355 |            0.560048 |  0.986827 |             0.671141 |          0.500000 |  100 |     49 |

## Interpretation

These results estimate retrospective same-session threat-log linkage inside the observed export. They do not establish future attack detection, analyst-effort reduction, deployment utility, or cross-organization generalization.