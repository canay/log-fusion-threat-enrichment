# Strict-Temporal Corrected-Linkage Results

- Corrected positives: 1,233 / 1,048,576 (0.1176%).
- Fail-closed direct/NAT-aware tuple support: 1,233 / 1,233.
- Original min-time-only primary split strict temporal invariant: False.
- Revised split: 838,748 train rows, 209,826 test rows, 1 purged boundary groups, strict max(train)<min(test)=True.
- Random-ranking AP: 0.000953; DNS-rule AP: 0.003945.

## Seed-42 primary results

| model               | feature_set     |   macro_f1 |   average_precision |   roc_auc |   positive_precision |   positive_recall |   tp |     fp |
|:--------------------|:----------------|-----------:|--------------------:|----------:|---------------------:|------------------:|-----:|-------:|
| XGBoost             | full_core       |   0.942402 |            0.966320 |  0.999374 |             0.905759 |          0.865000 |  173 |     18 |
| XGBoost             | no_outcome      |   0.778552 |            0.559456 |  0.989519 |             0.655405 |          0.485000 |   97 |     51 |
| XGBoost             | hard_proxy      |   0.757201 |            0.518131 |  0.978032 |             0.630435 |          0.435000 |   87 |     51 |
| Extra Trees         | no_outcome      |   0.787957 |            0.493705 |  0.933950 |             0.662338 |          0.510000 |  102 |     52 |
| LightGBM            | no_outcome      |   0.702903 |            0.544189 |  0.983304 |             0.270627 |          0.820000 |  164 |    442 |
| CatBoost            | no_outcome      |   0.583249 |            0.476547 |  0.991243 |             0.094587 |          0.865000 |  173 |   1656 |
| Logistic Regression | no_outcome      |   0.330141 |            0.001849 |  0.740269 |             0.001844 |          0.990000 |  198 | 107168 |
| XGBoost             | duration_only   |   0.499762 |            0.014738 |  0.802053 |             0.000000 |          0.000000 |    0 |      0 |
| XGBoost             | volume_only     |   0.709974 |            0.433048 |  0.969628 |             0.578947 |          0.330000 |   66 |     48 |
| XGBoost             | rate_normalized |   0.734388 |            0.437593 |  0.970936 |             0.567376 |          0.400000 |   80 |     61 |

## Paired block-bootstrap evaluation uncertainty

- No-outcome AP 95% interval: 0.4364 to 0.7091.
- Hard-proxy AP 95% interval: 0.3548 to 0.6759.
- Paired AP difference 95% interval: -0.0318 to 0.1230.

## Interpretation boundary

The strict purge repairs the chronological boundary but does not create external validation. Exposure-only, rate-normalized, seed-paired, and block-bootstrap results diagnose dependence and uncertainty inside this single observed export; they do not support causal, deployment, or cross-organization claims.
