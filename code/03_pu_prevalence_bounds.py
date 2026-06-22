"""Positive-unlabeled prevalence diagnostic (Section 5.6).

Treats has_linked_threat as a PU label: y = y* . b, b ~ Bernoulli(e(x)).
Computes (i) the SCAR-style Elkan-Noto label-frequency estimate c_EN = E[s|y=1]
on the seed-42 stratified holdout and the implied pi_EN = E[s]/c_EN, and
(ii) assumption-light structural bounds from the dual-export visibility
triangulation: the 8,341 threat-terminated-but-unlinked traffic sessions are
inspection-positive by construction, giving c <= 19,311/27,652 = 0.698 and
pi >= 27,652/1,048,576 = 2.64%. The order-of-magnitude gap between pi_EN
(~24%) and the structural floor demonstrates that SCAR fails here (labeling
concentrates in the threat-terminated dns-base pocket), so bounds rather than
point corrections are the defensible output. Score ranking is invariant to any
constant label-frequency correction, so the triage queues are unaffected.
Output: results/pu_estimates.csv  (run of 2026-06-07)
"""
# Pipeline: load/encode/fit identical to followup_weighted_seed_diagnostics
# (seed-42 stratified split, released XGBoost configuration), then:
#   c_en  = scores[y_test==1].mean()
#   pi_en = scores.mean()/c_en
#   bounds: c_ub = 19311/(19311+8341); pi_lb = (19311+8341)/1048576
