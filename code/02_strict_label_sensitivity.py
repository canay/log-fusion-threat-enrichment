"""Strict-tuple label-sensitivity diagnostic (Section 5.6 of the manuscript).

Rebuilds the strict session-plus-tuple label from the two raw exports, verifies
the expected 1,233 positives, aligns it row-wise with the processed modeling
table, and evaluates the released XGBoost configuration on the seed-42
stratified split (stratification on the primary label, so the row split is
identical to the main benchmark).

Usage:
  python 02_strict_label_sensitivity.py --traffic <trafik.csv> --threat <threat.csv> \
         --processed data/processed/traffic_has_linked_threat.csv

Raw exports are private; this script documents how the strict_tuple_s42 row of
results/followup_metrics.csv was produced (run of 2026-06-07: macro-F1 0.960,
AP 0.974, ROC-AUC 1.000, positive recall 92.3%).
"""
import argparse, time
import numpy as np
import pandas as pd

from followup_weighted_seed_diagnostics import load, strat_split, encode, metrics, CSVO, log

TUP = ['Session ID', 'Source address', 'Destination address',
       'Source Port', 'Destination Port', 'IP Protocol']
EXPECTED_STRICT = 1_233

def build_strict_label(traffic_csv, threat_csv):
    th = pd.read_csv(threat_csv, usecols=TUP, low_memory=False)
    th = th[th['Session ID'] != 0]
    key_th = th[TUP].astype(str).agg('|'.join, axis=1)
    tset = set(key_th.values)
    flags = []
    for ch in pd.read_csv(traffic_csv, usecols=TUP, low_memory=False, chunksize=250_000):
        key = ch[TUP].astype(str).agg('|'.join, axis=1)
        flags.append((key.isin(tset) & (ch['Session ID'] != 0)).values)
    y = np.concatenate(flags).astype(np.int8)
    assert int(y.sum()) == EXPECTED_STRICT, f"beklenen {EXPECTED_STRICT}, bulunan {int(y.sum())}"
    return y

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--traffic', required=True)
    ap.add_argument('--threat', required=True)
    ap.add_argument('--processed', default='data/processed/traffic_has_linked_threat.csv')
    a = ap.parse_args()
    t0 = time.time()
    y_strict = build_strict_label(a.traffic, a.threat)
    pr = pd.read_csv(a.processed, usecols=['Session ID', 'has_linked_threat'], low_memory=False)
    raw_sid = pd.read_csv(a.traffic, usecols=['Session ID'], low_memory=False)['Session ID'].values
    assert (pr['Session ID'].values == raw_sid).all(), 'islenmis tablo / ham trafik satir sirasi uyusmuyor'
    X, y_orig, cat, num = load()
    tr, te = strat_split(y_orig, 42)
    Xtr, Xte = encode(X, cat, num, tr, te)
    from xgboost import XGBClassifier
    clf = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.08, subsample=0.9,
                        colsample_bytree=0.9, tree_method="hist", random_state=42,
                        n_jobs=2, eval_metric="logloss")
    clf.fit(Xtr, y_strict[tr])
    s = clf.predict_proba(Xte)[:, 1]
    m = metrics(y_strict[te], s)
    m.update({"run": "strict_tuple_s42", "seed": 42, "scale_pos_weight": 1.0,
              "wall_seconds": round(time.time() - t0, 1)})
    pd.DataFrame([m]).to_csv(CSVO, mode="a", header=not CSVO.exists(), index=False)
    log(f"[strict_tuple_s42] macroF1={m['macro_f1']:.4f} AP={m['average_precision']:.4f} "
        f"AUC={m['roc_auc']:.4f} posR={m['pos_recall']:.4f}")

if __name__ == '__main__':
    main()
