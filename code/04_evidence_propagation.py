"""Temporal evidence-propagation diagnostic (Section 5.6) - null result.

Builds four leak-safe, past-only counters over the chronologically ordered
corpus - prior linked sessions sharing (1) the source endpoint, (2) the
destination endpoint, (3) destination port|protocol, (4) the source>destination
pair - log1p-transforms them, and appends them to the 27 core features under
the 80/20 chronological protocol. Raw addresses serve only as grouping keys;
they never enter the feature set. Result (2026-06-07, seed 42): AP 0.0787 ->
0.0784, ROC-AUC 0.638 -> 0.643, top-100..500 queues unchanged: session-level
attributes already absorb the endpoint-history signal in this window.
Rows chrono_base_s42 / chrono_prop_s42 in results/followup_metrics.csv.
"""
# Counters: df sorted by Receive Time; for key k: hist = groupby(k).y.cumsum()-y
