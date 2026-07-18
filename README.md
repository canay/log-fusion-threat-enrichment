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
block with cutoff-tie assignment and a boundary purge, train-only preprocessing,
zero group overlap, and a strict latest-train-before-earliest-test invariant. The
no-outcome feature set is the primary claim-bearing configuration; full core is
an inspection-informed upper bound, hard proxy is a stricter stress test, and
exposure-only/rate-normalized models bound observation-opportunity dependence.

## Canonical aggregate results

| Quantity | Value |
|---|---:|
| Traffic rows | 1,048,576 |
| Corrected same-session positives | 1,233 (0.1176%) |
| Direct tuple audit | 1,233 |
| NAT-aware tuple audit | 1,233 |
| Train/test composite-group overlap | 0 |
| Strict temporal boundary | PASS |
| Primary no-outcome XGBoost AP | 0.559456 |
| Primary no-outcome macro-F1 | 0.778552 |
| Primary no-outcome precision at 100 | 0.70 |
| Hard-proxy XGBoost AP | 0.518131 |
| Volume-only / rate-normalized AP | 0.433048 / 0.437593 |
| Paired no-outcome minus hard-proxy AP 95% interval | -0.0318–0.1230 |
| Rolling-origin AP range | 0.559456–0.711880 |

These are retrospective, within-export association measurements. They do not
establish maliciousness, future prediction, analyst-effort reduction,
deployment utility, or cross-organization generalization.

## Repository contents

```text
code/
  strict_temporal_exposure_uncertainty_pipeline.py
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
  exposure_strata.csv
  paired_seed_configuration_ap.csv
  uncertainty_summary.json
  PUBLIC_MANIFEST.json
CORRECTION_NOTICE.md
TRACEABILITY.md
requirements-model.lock.txt
```

## Reproduce on authorized local data

Python 3.12 is recommended. Install the pinned environment:

```powershell
python -m pip install -r requirements.txt
```

Run the corrected pipeline only in an authorized workspace containing the
restricted traffic and threat exports:

```powershell
python code/strict_temporal_exposure_uncertainty_pipeline.py `
  --traffic C:\authorized\traffic.csv `
  --threat C:\authorized\threat.csv `
  --derived C:\authorized\corrected_linkage_predictors.csv `
  --outdir out `
  --bootstrap-reps 500 `
  --bootstrap-blocks 20
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

Raw firewall telemetry is not distributed. The necessary institutional
permissions were obtained for the master's thesis from which the study was
developed. The public package excludes raw or
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
