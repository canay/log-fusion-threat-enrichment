# Correction notice

Earlier repository material modeled an unrestricted numeric-session-ID
membership task: a traffic row was positive when its nonzero identifier appeared
anywhere in a wider threat export. That computation produced 19,311 positives
and was internally consistent for that definition.

A raw-data validity audit later showed that unrestricted membership did not
identify the same temporal session when identifiers were recycled. Only 1,233
traffic rows had a qualifying threat event inside the corresponding traffic
session, and the same 1,233 rows were recovered by both direct and NAT-aware
tuple audits.

The current package therefore uses a different estimand and evaluation design:

- a namespace-scoped, time-aware same-session target;
- composite session-instance groups;
- a cutoff-tie-aware, purged, strictly chronological group-disjoint test block;
- train-only preprocessing;
- explicit no-outcome and hard-proxy feature boundaries; and
- exposure-only and rate-normalized diagnostics; and
- paired block bootstrap, multi-seed, rolling-origin, and fixed-budget aggregate evaluation.

The predecessor and corrected scores are not directly comparable because the
target, prevalence, partition, and evaluation unit changed. The corrected
package should not be described as a numerical improvement over the predecessor
task. The change strengthens construct validity for the manuscript's
same-session research question.

Legacy row-level, identifier-hash, and predecessor-target result artifacts are
not part of this curated public package.
