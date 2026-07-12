# The Echo in the Traffic

Aggregate reproducibility package for the manuscript **“The Echo in the
Traffic: Session-Level Log Linkage for Threat-Evidence Enrichment in Enterprise
Firewalls.”**

This repository represents the corrected same-session study. It does not retain
the predecessor cross-window numeric-identifier task as current evidence. See
[CORRECTION_NOTICE.md](CORRECTION_NOTICE.md) for the distinction.

## Study boundary

The study asks whether attributes recorded for a completed firewall traffic
session rank the presence of threat-log evidence from the same temporal session.
The corrected target requires:

1. a common device and virtual-system namespace;
2. a nonzero session identifier;
3. a threat event inside the traffic-session interval with a 30-second boundary
   tolerance; and
4. aggregate validation against direct and NAT-aware flow-tuple checks.

Evaluation uses composite session-instance groups, a later chronological test
block, train-only preprocessing, and zero group overlap between train and test.
The no-outcome feature set is the primary claim-bearing configuration; full core
is an inspection-informed upper bound, and hard proxy is a stricter stress test.

## Canonical aggregate results

| Quantity | Value |
|---|---:|
| Traffic rows | 1,048,576 |
| Corrected same-session positives | 1,233 (0.1176%) |
| Direct tuple audit | 1,233 |
| NAT-aware tuple audit | 1,233 |
| Train/test composite-group overlap | 0 |
| Primary no-outcome XGBoost AP | 0.560048 |
| Primary no-outcome macro-F1 | 0.786355 |
| Primary no-outcome precision at 100 | 0.67 |
| Hard-proxy XGBoost AP | 0.507609 |
| Rolling-origin AP range | 0.560048–0.691716 |

These are retrospective, within-export association measurements. They do not
establish maliciousness, future prediction, analyst-effort reduction,
deployment utility, or cross-organization generalization.

## Repository contents

```text
code/
  corrected_label_group_disjoint_pipeline.py
  make_corrected_figures.py
  fig_style.py
  fig_methodology_workflow_tikz.tex
  fig_methodology_workflow_standalone.tex
  validate_public_package.py
data/processed/
  README.md
results/
  corrected_linkage_results.json
  corrected_linkage_metrics.csv
  corrected_linkage_topk.csv
  corrected_linkage_summary.md
  PUBLIC_MANIFEST.json
CORRECTION_NOTICE.md
TRACEABILITY.md
```

## Reproduce on authorized local data

Python 3.12 is recommended. Install the pinned environment:

```powershell
python -m pip install -r requirements.txt
```

Run the corrected pipeline only in an authorized workspace containing the
restricted traffic and threat exports:

```powershell
python code/corrected_label_group_disjoint_pipeline.py `
  --traffic C:\authorized\traffic.csv `
  --threat C:\authorized\threat.csv `
  --processed C:\authorized\traffic_has_linked_threat.csv `
  --outdir out
```

Regenerate the empirical figures from the already-published aggregate JSON:

```powershell
python code/make_corrected_figures.py `
  --results results/corrected_linkage_results.json `
  --output-dir figures
```

The source-native workflow diagram can be compiled from `code/` with:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error `
  -jobname=fig_methodology_workflow `
  fig_methodology_workflow_standalone.tex
```

Validate the curated package before release:

```powershell
python code/validate_public_package.py .
```

## Data and privacy boundary

Raw firewall telemetry is not distributed. The public package excludes raw or
processed row-level records, IP addresses, hostnames, usernames, session
identifiers, session hashes, group hashes, absolute timestamps, row-level
labels, predictions, and sensitive deployment details.

Institutional permission covers publication of anonymized, aggregate
application, category, and policy-pocket labels in the manuscript and public
repository. Such summaries must be derived from the corrected same-session
target and must not contain row-level mappings. This repository does not reuse
predecessor-target category or pocket results.

Input SHA-256 values are retained so an authorized same-data reproduction can
confirm file identity without publishing the files themselves.

## Citation and license

Citation metadata are in [CITATION.cff](CITATION.cff). No DOI or release date is
claimed until the authors create an actual archived release. Code and curated
aggregate artifacts are provided under the [MIT License](LICENSE).
