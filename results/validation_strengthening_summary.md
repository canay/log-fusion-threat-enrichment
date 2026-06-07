# Paper 3 Validation Strengthening Analyses

These reviewer-facing analyses add uncertainty estimates, analyst-budget curves, error profiling, and linkage sensitivity checks for the Paper 3 manuscript.

## Scenario Metrics

| scenario              | test_rows | test_positives | test_prevalence | macro_f1 | average_precision | roc_auc | positive_precision | positive_recall | fit_seconds | device_used |
| --------------------- | --------- | -------------- | --------------- | -------- | ----------------- | ------- | ------------------ | --------------- | ----------- | ----------- |
| full_stratified       | 209716    | 3862           | 0.0184          | 0.5533   | 0.0941            | 0.6347  | 0.9084             | 0.0616          | 26.1089     | cuda        |
| no_outcome_stratified | 209716    | 3862           | 0.0184          | 0.5292   | 0.0722            | 0.6349  | 0.8193             | 0.0352          | 16.7431     | cuda        |
| full_temporal         | 209716    | 3828           | 0.0183          | 0.5391   | 0.0788            | 0.6370  | 0.9067             | 0.0457          | 15.3088     | cuda        |


## Runtime Profile

| stage                | scenario              | seconds  | rows    | test_rows | bootstrap_iterations | device_requested | device_used |
| -------------------- | --------------------- | -------- | ------- | --------- | -------------------- | ---------------- | ----------- |
| data_load            | all                   | 15.6565  | 1048576 |           |                      | cuda             |             |
| fit_predict          | full_stratified       | 28.2261  | 1048576 | 209716    |                      | cuda             | cuda        |
| bootstrap_ci         | full_stratified       | 206.7464 | 1048576 | 209716    | 500                  | cuda             | cuda        |
| scenario_total       | full_stratified       | 240.1433 | 1048576 | 209716    | 500                  | cuda             | cuda        |
| fit_predict          | no_outcome_stratified | 19.1411  | 1048576 | 209716    |                      | cuda             | cuda        |
| bootstrap_ci         | no_outcome_stratified | 176.7590 | 1048576 | 209716    | 500                  | cuda             | cuda        |
| scenario_total       | no_outcome_stratified | 200.3943 | 1048576 | 209716    | 500                  | cuda             | cuda        |
| fit_predict          | full_temporal         | 18.2129  | 1048576 | 209716    |                      | cuda             | cuda        |
| bootstrap_ci         | full_temporal         | 151.3095 | 1048576 | 209716    | 500                  | cuda             | cuda        |
| scenario_total       | full_temporal         | 171.2862 | 1048576 | 209716    | 500                  | cuda             | cuda        |
| error_profile        | full_stratified       | 0.6148   | 209716  | 209716    |                      | cuda             |             |
| linkage_sensitivity  | all                   | 0.0035   | 1048576 |           |                      | cuda             |             |
| total_python_runtime | all                   | 643.2513 | 1048576 |           | 500                  | cuda             |             |


## Bootstrap 95% Confidence Intervals

| scenario              | metric             | point   | ci_lower_95 | ci_upper_95 | bootstrap_iterations_used |
| --------------------- | ------------------ | ------- | ----------- | ----------- | ------------------------- |
| full_stratified       | macro_f1           | 0.5533  | 0.5468      | 0.5599      | 500                       |
| full_stratified       | average_precision  | 0.0941  | 0.0860      | 0.1031      | 500                       |
| full_stratified       | roc_auc            | 0.6347  | 0.6275      | 0.6429      | 500                       |
| full_stratified       | positive_precision | 0.9084  | 0.8730      | 0.9424      | 500                       |
| full_stratified       | positive_recall    | 0.0616  | 0.0542      | 0.0692      | 500                       |
| full_stratified       | top_100_precision  | 0.9900  | 0.9700      | 1.0000      | 500                       |
| full_stratified       | top_100_lift       | 53.7594 | 51.7753     | 55.6898     | 500                       |
| full_stratified       | top_500_precision  | 0.5240  | 0.4600      | 0.5911      | 500                       |
| no_outcome_stratified | macro_f1           | 0.5292  | 0.5239      | 0.5347      | 500                       |
| no_outcome_stratified | average_precision  | 0.0722  | 0.0647      | 0.0799      | 500                       |
| no_outcome_stratified | roc_auc            | 0.6349  | 0.6281      | 0.6425      | 500                       |
| no_outcome_stratified | positive_precision | 0.8193  | 0.7613      | 0.8780      | 500                       |
| no_outcome_stratified | positive_recall    | 0.0352  | 0.0295      | 0.0411      | 500                       |
| no_outcome_stratified | top_100_precision  | 0.8800  | 0.8048      | 0.9400      | 500                       |
| no_outcome_stratified | top_100_lift       | 47.7861 | 43.8170     | 51.2397     | 500                       |
| no_outcome_stratified | top_500_precision  | 0.4000  | 0.3480      | 0.4490      | 500                       |
| full_temporal         | macro_f1           | 0.5391  | 0.5328      | 0.5444      | 500                       |
| full_temporal         | average_precision  | 0.0788  | 0.0707      | 0.0865      | 500                       |
| full_temporal         | roc_auc            | 0.6370  | 0.6299      | 0.6441      | 500                       |
| full_temporal         | positive_precision | 0.9067  | 0.8660      | 0.9421      | 500                       |
| full_temporal         | positive_recall    | 0.0457  | 0.0388      | 0.0515      | 500                       |
| full_temporal         | top_100_precision  | 1.0000  | 0.9900      | 1.0000      | 500                       |
| full_temporal         | top_100_lift       | 54.7847 | 52.9876     | 56.4519     | 500                       |
| full_temporal         | top_500_precision  | 0.4060  | 0.3500      | 0.4641      | 500                       |


## Top-k Analyst-Budget Curve

| scenario              | k    | true_positives | false_positives | precision | recall | lift_over_prevalence |
| --------------------- | ---- | -------------- | --------------- | --------- | ------ | -------------------- |
| full_stratified       | 10   | 10             | 0               | 1.0000    | 0.0026 | 54.3024              |
| full_stratified       | 25   | 24             | 1               | 0.9600    | 0.0062 | 52.1303              |
| full_stratified       | 50   | 49             | 1               | 0.9800    | 0.0127 | 53.2164              |
| full_stratified       | 100  | 99             | 1               | 0.9900    | 0.0256 | 53.7594              |
| full_stratified       | 250  | 233            | 17              | 0.9320    | 0.0603 | 50.6099              |
| full_stratified       | 500  | 262            | 238             | 0.5240    | 0.0678 | 28.4545              |
| full_stratified       | 1000 | 273            | 727             | 0.2730    | 0.0707 | 14.8246              |
| no_outcome_stratified | 10   | 10             | 0               | 1.0000    | 0.0026 | 54.3024              |
| no_outcome_stratified | 25   | 24             | 1               | 0.9600    | 0.0062 | 52.1303              |
| no_outcome_stratified | 50   | 45             | 5               | 0.9000    | 0.0117 | 48.8722              |
| no_outcome_stratified | 100  | 88             | 12              | 0.8800    | 0.0228 | 47.7861              |
| no_outcome_stratified | 250  | 167            | 83              | 0.6680    | 0.0432 | 36.2740              |
| no_outcome_stratified | 500  | 200            | 300             | 0.4000    | 0.0518 | 21.7210              |
| no_outcome_stratified | 1000 | 220            | 780             | 0.2200    | 0.0570 | 11.9465              |
| full_temporal         | 10   | 10             | 0               | 1.0000    | 0.0026 | 54.7847              |
| full_temporal         | 25   | 25             | 0               | 1.0000    | 0.0065 | 54.7847              |
| full_temporal         | 50   | 50             | 0               | 1.0000    | 0.0131 | 54.7847              |
| full_temporal         | 100  | 100            | 0               | 1.0000    | 0.0261 | 54.7847              |
| full_temporal         | 250  | 196            | 54              | 0.7840    | 0.0512 | 42.9512              |
| full_temporal         | 500  | 203            | 297             | 0.4060    | 0.0530 | 22.2426              |
| full_temporal         | 1000 | 218            | 782             | 0.2180    | 0.0569 | 11.9431              |


## Error Profile Snapshot

| error_group    | column             | value               | count | share_within_group |
| -------------- | ------------------ | ------------------- | ----- | ------------------ |
| true_positive  | Action             | allow               | 238   | 1.0000             |
| true_positive  | Session End Reason | threat              | 229   | 0.9622             |
| true_positive  | Session End Reason | tcp-fin             | 9     | 0.0378             |
| true_positive  | Application        | dns-base            | 206   | 0.8655             |
| true_positive  | Application        | web-browsing        | 23    | 0.0966             |
| true_positive  | Application        | telegram-base       | 6     | 0.0252             |
| true_positive  | Application        | unknown-tcp         | 3     | 0.0126             |
| true_positive  | Destination Zone   | DMZ                 | 150   | 0.6303             |
| true_positive  | Destination Zone   | WAN                 | 69    | 0.2899             |
| true_positive  | Destination Zone   | WAF                 | 19    | 0.0798             |
| true_positive  | Risk of app        | 3                   | 206   | 0.8655             |
| true_positive  | Risk of app        | 4                   | 23    | 0.0966             |
| true_positive  | Risk of app        | 2                   | 6     | 0.0252             |
| true_positive  | Risk of app        | 1                   | 3     | 0.0126             |
| false_positive | Action             | allow               | 24    | 1.0000             |
| false_positive | Session End Reason | threat              | 24    | 1.0000             |
| false_positive | Application        | dns-base            | 23    | 0.9583             |
| false_positive | Application        | web-browsing        | 1     | 0.0417             |
| false_positive | Destination Zone   | DMZ                 | 12    | 0.5000             |
| false_positive | Destination Zone   | WAN                 | 11    | 0.4583             |
| false_positive | Destination Zone   | LAN                 | 1     | 0.0417             |
| false_positive | Risk of app        | 3                   | 23    | 0.9583             |
| false_positive | Risk of app        | 4                   | 1     | 0.0417             |
| false_negative | Action             | allow               | 3573  | 0.9859             |
| false_negative | Action             | drop                | 51    | 0.0141             |
| false_negative | Session End Reason | aged-out            | 2371  | 0.6542             |
| false_negative | Session End Reason | tcp-fin             | 662   | 0.1827             |
| false_negative | Session End Reason | tcp-rst-from-client | 339   | 0.0935             |
| false_negative | Session End Reason | tcp-rst-from-server | 131   | 0.0361             |
| false_negative | Session End Reason | threat              | 47    | 0.0130             |
| false_negative | Application        | dns-base            | 966   | 0.2666             |
| false_negative | Application        | ssl                 | 684   | 0.1887             |
| false_negative | Application        | snmpv3-get-request  | 544   | 0.1501             |
| false_negative | Application        | insufficient-data   | 367   | 0.1013             |
| false_negative | Application        | ping                | 196   | 0.0541             |
| false_negative | Destination Zone   | LAN                 | 1303  | 0.3595             |
| false_negative | Destination Zone   | WAN                 | 934   | 0.2577             |
| false_negative | Destination Zone   | DMZ                 | 920   | 0.2539             |
| false_negative | Destination Zone   | WAF                 | 467   | 0.1289             |
| false_negative | Risk of app        | 3                   | 1044  | 0.2881             |
| false_negative | Risk of app        | 2                   | 959   | 0.2646             |
| false_negative | Risk of app        | 1                   | 842   | 0.2323             |
| false_negative | Risk of app        | 4                   | 777   | 0.2144             |
| false_negative | Risk of app        | 5                   | 2     | 0.0006             |


## Numeric Error Profile Snapshot

| error_group    | column             | count  | mean        | median   | q25      | q75       | min      | max             |
| -------------- | ------------------ | ------ | ----------- | -------- | -------- | --------- | -------- | --------------- |
| true_negative  | Bytes              | 205830 | 146469.1370 | 272.0000 | 153.0000 | 1459.0000 | 60.0000  | 5544739007.0000 |
| true_negative  | Packets            | 205830 | 183.2663    | 2.0000   | 2.0000   | 10.0000   | 1.0000   | 14319574.0000   |
| true_negative  | Elapsed Time (sec) | 205830 | 15.3009     | 0.0000   | 0.0000   | 0.0000    | 0.0000   | 78214.0000      |
| false_negative | Bytes              | 3624   | 72293.9299  | 628.0000 | 207.0000 | 2368.0000 | 60.0000  | 96086813.0000   |
| false_negative | Packets            | 3624   | 71.4691     | 4.0000   | 2.0000   | 16.0000   | 1.0000   | 80573.0000      |
| false_negative | Elapsed Time (sec) | 3624   | 15.9741     | 0.0000   | 0.0000   | 0.0000    | 0.0000   | 2545.0000       |
| true_positive  | Bytes              | 238    | 27339.4286  | 427.0000 | 319.2500 | 728.0000  | 182.0000 | 2781717.0000    |
| true_positive  | Packets            | 238    | 36.8025     | 4.0000   | 2.0000   | 8.0000    | 2.0000   | 3266.0000       |
| true_positive  | Elapsed Time (sec) | 238    | 17.6345     | 10.0000  | 3.0000   | 17.7500   | 0.0000   | 354.0000        |
| false_positive | Bytes              | 24     | 708.0000    | 572.5000 | 242.7500 | 807.0000  | 198.0000 | 2121.0000       |
| false_positive | Packets            | 24     | 6.2500      | 6.0000   | 2.0000   | 8.5000    | 2.0000   | 20.0000         |
| false_positive | Elapsed Time (sec) | 24     | 19.3333     | 12.0000  | 0.0000   | 16.2500   | 0.0000   | 176.0000        |


## Linkage Sensitivity

The primary session-overlap label yields 19,311 positives (1.8416%). The stricter nonzero session plus exact flow-tuple overlap yields 1,233 positives (0.1176%), retaining 6.38% of session-overlap positives. This supports the manuscript's conservative framing: session-level linkage is measurable, whereas packet-level reconstruction should not be claimed.

| label_definition                         | positive_rows | positive_share | notes                                                          |
| ---------------------------------------- | ------------- | -------------- | -------------------------------------------------------------- |
| nonzero_session_overlap                  | 19311         | 0.0184         | Primary manuscript label.                                      |
| nonzero_session_plus_exact_tuple_overlap | 1233          | 0.0012         | Strict diagnostic evidence; too sparse for the primary target. |

