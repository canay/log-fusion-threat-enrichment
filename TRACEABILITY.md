# Traceability

## Canonical source run

The public artifacts are exported from the internal canonical aggregate run:

```text
2026-07-17 strict-temporal corrected same-session exposure-uncertainty run
```

The source run is not copied verbatim because its manifest and JSON contain
local host and absolute-time metadata. The public exporter removes those fields
without changing linkage or completeness counts, strict split invariants, model
metrics, top-k records, exposure and uncertainty summaries, seeds, feature
boundaries, runtime, dependency versions, or input SHA-256 values.

## Claim-to-file map

| Claim family | Public evidence |
|---|---|
| Corrected target and linkage acceptance | `results/corrected_linkage_results.json` |
| Primary, seed, and rolling-origin model metrics | `results/corrected_linkage_metrics.csv` |
| Fixed-budget descriptive precision and recall point measurements | `results/corrected_linkage_topk.csv` |
| Exposure strata and exposure-only diagnostics | `results/exposure_strata.csv`, `results/corrected_linkage_metrics.csv` |
| Paired seed-configuration differences | `results/paired_seed_configuration_ap.csv` |
| Paired nonoverlapping-block-bootstrap uncertainty | `results/uncertainty_summary.json` |
| Human-readable result summary | `results/corrected_linkage_summary.md` |
| Corrected target, strict split, exposure, and uncertainty implementation | `code/strict_temporal_exposure_uncertainty_pipeline.py` |
| Exact modeling dependency lock | `requirements-model.lock.txt` |
| Empirical figure regeneration | `code/make_corrected_figures.py`, `code/fig_style.py` |
| Source-native workflow figure | `code/fig_methodology_workflow_*.tex` |
| File hashes and byte sizes | `results/PUBLIC_MANIFEST.json` |

## Release boundary

The package is aggregate-only. Session identifiers and identifier hashes are
explicitly excluded even when salted. Publication permission covers anonymized,
aggregate application, category, and policy-pocket labels; it does not authorize
row-level mappings or identifier-level derivatives.
