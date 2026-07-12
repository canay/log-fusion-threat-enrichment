# Traceability

## Canonical source run

The public artifacts are exported from the internal canonical aggregate run:

```text
2026-07-12 corrected same-session group-disjoint run
```

The source run is not copied verbatim because its manifest and JSON contain
local host and absolute-time metadata. The public exporter removes those fields
without changing linkage counts, model metrics, top-k records, seeds, feature
boundaries, runtime, or input SHA-256 values.

## Claim-to-file map

| Claim family | Public evidence |
|---|---|
| Corrected target and linkage acceptance | `results/corrected_linkage_results.json` |
| Primary, seed, and rolling-origin model metrics | `results/corrected_linkage_metrics.csv` |
| Fixed-budget precision, recall, and exact intervals | `results/corrected_linkage_topk.csv` |
| Human-readable result summary | `results/corrected_linkage_summary.md` |
| Corrected target and evaluation implementation | `code/corrected_label_group_disjoint_pipeline.py` |
| Empirical figure regeneration | `code/make_corrected_figures.py`, `code/fig_style.py` |
| Source-native workflow figure | `code/fig_methodology_workflow_*.tex` |
| File hashes and byte sizes | `results/PUBLIC_MANIFEST.json` |

## Release boundary

The package is aggregate-only. Session identifiers and identifier hashes are
explicitly excluded even when salted. Publication permission covers anonymized,
aggregate application, category, and policy-pocket labels; it does not authorize
row-level mappings or identifier-level derivatives.
