"""Label-free ranking baselines + rolling-origin temporal diagnostic (Section 5.6).

Baselines on the 80/20 chronological split (no labels used in fitting):
  - Isolation forest: sklearn IsolationForest(n_estimators=200, max_samples=256,
    random_state=42); anomaly score = -score_samples.
  - Contextual rarity: mean of -log(train frequency) over the low-cardinality
    encoded fields (the SIERRA-spirit unsupervised contextual-ranking principle).
Both collapse on the linked-evidence label (run of 2026-06-07): isolation forest
AP 0.018 / AUC 0.467 / top-100 0.00; rarity AP 0.021 / AUC 0.515 / top-100 0.00,
versus the supervised fusion model at AP 0.079 / top-100 1.00. Linked sessions
are dominated by common dns-base traffic, so corroborated evidence is not
statistical unusualness.

Rolling-origin evaluation: four consecutive 10% receive-time slices, training on
all earlier rows with per-fold re-encoding (folds 60-70 and 70-80 are fresh
fits; folds 80-90 and 90-100 are score slices of the 80%-trained chronological
model, whose training set is identical by construction).
Results: AP 0.0925 / 0.1230 / 0.1023 / 0.0558; top-100 1.00 / 1.00 / 0.97 / 0.57
-> ranking signal persists, queue purity decays at the trailing edge.
Rows chrono_isoforest / chrono_rarity / rolling_f1..f4 in results/followup_metrics.csv.
"""
