# Session-level firewall log fusion

Public reproducibility artifact for the manuscript:

**Session-Level Fusion of Enterprise Firewall Traffic and Threat Logs for Triage-Driven Rare Security-Event Prediction**

Repository short name:

`log-fusion-threat-enrichment`

Public GitHub URL:

`https://github.com/canay/log-fusion-threat-enrichment`

## Related study

This repository supports a paper on session-level linkage of real enterprise Palo Alto traffic and threat logs. The study asks whether structured traffic-log attributes can predict whether a traffic session is linked to threat-log evidence. The active manuscript framing is operational network telemetry linkage, traffic/security log correlation, and rare security-event prediction for secure network monitoring.

Target:

`has_linked_threat`

Target classes:

- 0: no linked threat-session evidence
- 1: linked threat-session evidence

## Authors and contact

Author order:

1. **Özkan Canay**, corresponding author
2. **Cem Özkurt**

Özkan Canay

- Department of Information Systems and Technologies
- Faculty of Computer and Information Sciences
- Sakarya University
- Email: canay@sakarya.edu.tr
- ORCID: 0000-0001-7539-6001

Cem Özkurt

- Department of Data Science and Analytics
- Faculty of Computer and Information Sciences
- Sakarya University
- Email: cemozkurt@sakarya.edu.tr
- ORCID: 0000-0002-1251-7715

GitHub:

https://github.com/canay

License: MIT (see `LICENSE`). Target journal: Computer Networks. Update the citation block with the article DOI once assigned.

## Repository contents

- `code/`: label-construction reference implementation (`01_build_linked_threat_dataset.py`, with expected-count assertions), Python benchmark, operating-point, evidence-family, missingness and proxy-field diagnostics, and the figure-generation scripts
- `data/processed/`: placeholder only; row-level processed firewall datasets are not included by default
- `results/`: CSV/JSON benchmark outputs, linkage audit, metadata, timing files from the Oracle Cloud VPS runs, operating-point diagnostics, evidence-family/calibration diagnostics, bootstrap confidence intervals, linkage-sensitivity output, runtime profile, error-pocket summaries, and the per-column missingness summary
- `requirements.txt`: Python dependencies used in the experiments
- `CITATION.cff`: citation metadata for this artifact

Raw enterprise firewall exports are **not** redistributed in this repository. Row-level processed derivatives are also excluded from the public-facing package by default because the source telemetry belongs to an institutional firewall environment and may carry privacy, institutional, or security exposure risks even after pseudonymization.

## Data

Included processed datasets:

- None by default.

The following row-level processed artifacts were used in the paper but are held outside the public release package unless explicit institutional authorization and privacy/security review approve redistribution:

- `traffic_has_linked_threat.csv.zip`
- `traffic_has_linked_threat_sample.csv`
- `traffic_threat_linked_positive_sessions.csv`
- `threat_session_summary.csv`

These files are derived from firewall telemetry and may contain residual re-identification or operational-security risk through session-level patterns, timing-derived fields, categorical context, application/zone/interface information, or linked threat evidence. Co-authorship on the manuscript does not by itself grant public redistribution rights for institutional telemetry derivatives.

Full linked-threat dataset:

- Traffic rows: 1,048,576
- Rows with linked threat-session evidence: 19,311
- Rows without linked threat-session evidence: 1,029,265
- Positive share: 1.84%

Linkage evidence:

- Traffic rows: 1,048,576
- Threat rows: 186,271
- Common columns: 93
- Threat nonzero session identifiers observed in traffic: 19,283
- Share of threat nonzero session identifiers observed in traffic: 86.8%
- Exact nonzero session plus tuple overlap: 1,233 traffic rows

Privacy note:

The package excludes raw enterprise log exports and row-level processed derivatives by default. Aggregate counts, model metrics, calibration summaries, linkage summaries, and validation summaries are provided for transparency. Any release of row-level processed data requires written permission from the relevant institutional data controller or authorized institutional unit and a documented review confirming that the release does not expose personal data, sensitive institutional operations, or exploitable security information.

## Main evidence snapshot

Full baseline:

- Top model by macro-F1: XGBoost
- Accuracy: 0.982615
- Balanced accuracy: 0.530887
- Macro-F1: 0.553564
- Weighted-F1: 0.975102
- Average precision: 0.094028
- ROC-AUC: 0.636265

No-traffic-outcome ablation:

- Removed fields: `Action`, `Threat/Content Type`, `Session End Reason`
- XGBoost accuracy: 0.982023
- XGBoost balanced accuracy: 0.517374
- XGBoost macro-F1: 0.528878
- XGBoost average precision: 0.071054
- XGBoost ROC-AUC: 0.634311

Positive-class performance in the no-traffic-outcome setting:

- Precision: 0.7584
- Recall: 0.0350
- F1: 0.0668
- Test support: 3,862

Operating-point diagnostics:

- Full stratified XGBoost, top 100 ranked sessions: 99 positives, 99.0% precision, 53.8x lift over prevalence
- No-traffic-outcome XGBoost, top 100 ranked sessions: 89 positives, 89.0% precision, 48.3x lift over prevalence
- Chronological holdout XGBoost, top 100 ranked sessions: 100 positives, 100.0% precision, 54.8x lift over prevalence
- No-traffic-outcome feature importance is led by `Packets`, `Outbound Interface`, `Risk of app`, `Destination Zone`, `Source Zone`, and `Bytes Received`

Evidence-family and calibration diagnostics:

- Full-core XGBoost gives the strongest average precision: 0.0946
- Volume-only evidence retains average precision of 0.0672
- Context-plus-volume evidence reaches average precision of 0.0719
- Policy/action-only evidence has zero positive recall at the default threshold
- Global calibration scores are dominated by the negative class, so model scores are treated as ranking evidence rather than autonomous probabilities

Validation-strengthening diagnostics:

- Bootstrap confidence intervals use 500 resamples for the main XGBoost validation scenarios.
- Full stratified XGBoost average precision is 0.0941 with a 95% bootstrap interval of 0.0860 to 0.1031.
- Full stratified XGBoost top-100 precision is 0.9900 with a 95% bootstrap interval of 0.9700 to 1.0000.
- Strict nonzero session plus exact tuple overlap retains 1,233 positives, or 6.38% of the primary session-overlap positives.
- In the CUDA-enabled diagnostic pass, the full stratified XGBoost fit-and-predict stage processed the 1,048,576-row corpus with a 209,716-row holdout in 28.2 seconds.
- Error-pocket profiling shows that high-confidence positives concentrate in a narrow DNS/DMZ/WAN/threat-termination pocket, while false negatives are more diffuse across ordinary-looking traffic contexts.

Interpretation:

High accuracy is misleading because the positive class is only 1.84%. Macro-F1, balanced accuracy, recall, average precision, and ROC-AUC reveal that threat-linked session prediction is a difficult rare-event problem with weak but measurable signal.

## Experimental environment

Final timing-sensitive experiments were conducted on:

- Oracle Cloud Ampere virtual private server
- 4 OCPU
- 24 GB RAM
- Python 3.12.3
- Linux aarch64

The same VPS environment was used for the final full-corpus benchmark, sample diagnostic benchmark, ablation, and cross-validation results in `results/`.

The additional operating-point and evidence-family diagnostics were produced from restricted processed artifacts and are not used as timing evidence.

## Reproducing with authorized processed artifacts

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

The commands below require authorized access to the row-level processed artifacts. They will not run from the public-facing repository unless the required datasets are placed under `data/processed/` after institutional permission.

Run the full baseline:

```bash
python code/03_benchmark_baseline.py --dataset linked_full --feature-set core --models "Extra Trees,XGBoost,LightGBM,CatBoost" --tag full_baseline --output-dir results
```

Run the no-traffic-outcome ablation:

```bash
python code/03_benchmark_baseline.py --dataset linked_full --feature-set core --models "Extra Trees,XGBoost,LightGBM,CatBoost" --exclude-features "Action,Threat/Content Type,Session End Reason" --tag full_no_traffic_outcome --output-dir results
```

Run the sample top-model CV:

```bash
python code/03_benchmark_baseline.py --dataset linked_sample --feature-set core --models "Extra Trees,XGBoost,LightGBM,CatBoost" --cv --tag sample_top_cv --output-dir results
```

Run the operating-point, chronological holdout, and no-traffic-outcome feature-importance diagnostics:

```bash
python code/q1_operating_point_analysis.py
```

Run the evidence-family and calibration diagnostics:

```bash
python code/evidence_uncertainty_analysis.py --device cpu
```

The manuscript also reports validation-strengthening outputs from `results/q1_analysis_payload.json`, `results/q1_operating_points.csv`, `results/q1_threshold_summary.csv`, `results/q1_feature_importance_no_outcome_xgboost.csv`, `results/bootstrap_confidence_intervals.csv`, `results/linkage_sensitivity.csv`, `results/validation_runtime_profile.csv`, `results/error_profile_categorical.csv`, `results/error_profile_numeric.csv`, and `results/validation_strengthening_summary.md`.

## Submission and public release checklist

Before linking this repository in a manuscript submission:

- Replace the planned GitHub URL with the final public URL.
- Update the paper title, author affiliations, ORCID/contact information, target journal, submission status, DOI if available, and citation text.
- Keep `data/processed/` free of row-level firewall telemetry derivatives unless explicit institutional authorization permits public redistribution.
- Confirm that no raw enterprise logs, manuscript drafts, private review notes, or local credentials are included.
- Confirm with the relevant institutional data controller or authorized IT/institutional unit whether any processed row-level artifact may be shared publicly.
- Check whether the target journal requires a data availability statement, code availability statement, or repository DOI.
- Consider archiving the final GitHub release on Zenodo only after the data-sharing scope is finalized; do not archive restricted row-level data by accident.

## License

No license has been assigned yet. Choose appropriate code and data licenses before public release.
