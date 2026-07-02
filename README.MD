# Session-level firewall log fusion

Public reproducibility artifact for the manuscript:

**The Echo in the Traffic: Session-Level Log Fusion for Threat-Evidence Enrichment in Enterprise Firewalls**

Repository short name:

`log-fusion-threat-enrichment`

Public GitHub URL:

`https://github.com/canay/log-fusion-threat-enrichment`

## Related study

This repository supports a paper on session-level linkage of real enterprise Palo Alto traffic and threat logs (source platform: PA-1410 pair in active-passive HA, PAN-OS 11.1.10-h1 at collection time, offline CSV export). The study asks whether structured traffic-log attributes can predict whether a traffic session is linked to threat-log evidence. The active manuscript framing is operational network telemetry linkage, traffic/security log correlation, and rare security-event prediction for secure network monitoring.

Target:

`has_linked_threat`

Target classes:

- 0: no linked threat-session evidence
- 1: linked threat-session evidence

## Authors and contact

Author order:

1. **Özkan Canay**, corresponding author
2. **Cem Özkurt**
3. **Fatmir Garri**

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

Fatmir Garri

- Department of Information Technology
- Sakarya University of Applied Sciences
- Email: fatmirgarri@subu.edu.tr
- ORCID: 0009-0005-6762-6846

GitHub:

https://github.com/canay

License: MIT (see `LICENSE`). Target journal: Computer Networks. Update the citation block with the article DOI once assigned.

## Repository contents

- `code/`: label-construction reference implementation (`01_build_linked_threat_dataset.py`, with expected-count assertions), Python benchmark, operating-point, evidence-family, missingness and proxy-field diagnostics, and the figure-generation scripts
- `data/processed/`: placeholder only; row-level processed firewall datasets are not included by default
- `results/`: CSV/JSON benchmark outputs, linkage audit, metadata, timing files from the Oracle Cloud VPS runs, operating-point diagnostics, evidence-family/calibration diagnostics, bootstrap confidence intervals, linkage-sensitivity output, runtime profile, error-pocket summaries, the per-column missingness summary, the proxy-field value audit, and the follow-up weighted/seed/strict-label diagnostics (followup_metrics.csv)
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
- No-traffic-outcome XGBoost, top 100 ranked sessions: 88 positives, 88.0% precision, 47.8x lift over prevalence
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
- In the CUDA-enabled validation-strengthening pass, executed on a consumer workstation with an NVIDIA GeForce GTX 1050 GPU, the full stratified XGBoost fit-and-predict stage processed the 1,048,576-row corpus with a 209,716-row holdout in 28.2 seconds.
- Error-pocket profiling shows that high-confidence positives concentrate in a narrow DNS/DMZ/WAN/threat-termination pocket, while false negatives are more diffuse across ordinary-looking traffic contexts.

Interpretation:

High accuracy is misleading because the positive class is only 1.84%. Macro-F1, balanced accuracy, recall, average precision, and ROC-AUC reveal that threat-linked session prediction is a difficult rare-event problem with weak but measurable signal.

## Experimental environment

The experiments were executed in two environments:

Benchmark environment (full-corpus benchmark, sample diagnostic benchmark, ablations, and sample cross-validation results in `results/`):

- Oracle Cloud Ampere virtual private server
- 4 OCPU
- 24 GB RAM
- Python 3.12.3
- Linux aarch64

Validation-strengthening diagnostic pass (bootstrap intervals, operating-point curves, temporal re-run, and the runtime profile in `results/validation_runtime_profile.csv`):

- Consumer workstation
- NVIDIA GeForce GTX 1050 GPU (CUDA-enabled XGBoost, `device_requested=cuda`, `device_used=cuda`)

The additional operating-point and evidence-family diagnostics were produced from restricted processed artifacts and are not used as timing evidence. All reported timings are environment-specific scale checks rather than portable speed benchmarks.

## Result file provenance

The result files in `results/` come from separate fixed passes; small default-threshold count differences between passes are expected because each pass retrains the model:

- `baseline_benchmark_*` (multi-model benchmark, ablations, sample CV): source of the manuscript full-corpus benchmark and ablation tables.
- `validation_strengthening_summary.md`, `bootstrap_confidence_intervals.csv`, `validation_runtime_profile.csv`, `error_profile_*`, `linkage_sensitivity.csv`: canonical source of the manuscript operating-point table, bootstrap confidence intervals, temporal holdout narrative, and runtime profile.
- `q1_operating_points.csv`, `q1_analysis_summary.md`, `q1_threshold_summary.csv`, `q1_analysis_payload.json`: an earlier diagnostic pass retained for transparency; superseded by the validation-strengthening pass for the operating-point and temporal values reported in the manuscript. `q1_feature_importance_no_outcome_xgboost.csv` from this pass still backs the no-outcome feature-importance figure.
- `evidence_uncertainty_*`, `runtime_profile.csv`, `calibration_bins.csv`, `evidence_family_*`: evidence-family and calibration diagnostics.
- `followup_metrics.csv`, `pu_estimates.csv`, `missingness_summary.csv`, `proxy_field_audit.csv`: follow-up diagnostics (weighted variant, chronological and rolling-origin checks, anomaly baselines).
- `fullscale_results.json`, `fullscale_multiseed.csv`, `fullscale_cv.csv`, `q1audit_addons.json`: full-corpus multi-seed, cross-validation, logistic-regression baseline, and statistical-test evidence.

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

License: MIT (see `LICENSE`).
