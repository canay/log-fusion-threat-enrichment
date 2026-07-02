#!/usr/bin/env python3
"""
Q1-audit full-scale extensions (run on a machine with the ML stack + no time limit).

Produces the three full-corpus results that the Cowork sandbox could not run
within its execution window:
  1) XGBoost multi-seed stability (>=10 seeds), full corpus, released config.
  2) XGBoost full-corpus stratified 5-fold CV (not just the diagnostic sample).
  3) Penalized logistic-regression baseline, full corpus, seed-42 holdout.

Pipeline mirrors the released benchmark semantics:
  - Drop: has_linked_threat (target), Session ID, Receive Time, Generate Time,
    High Res Timestamp. (Rule / Action Source are already absent from the
    processed modeling table.)
  - Categorical -> most-frequent impute + ordinal encode, unseen test category -> -1.
  - Numeric -> median impute. Scaling applied only for logistic regression.
  - XGBoost: 300 hist trees, depth 6, lr 0.08, subsample/colsample 0.9,
    tree_method='hist', unweighted (scale_pos_weight=1).
  - Split: stratified 80/20. Primary seed = 42. 5-fold = StratifiedKFold(shuffle, 42).

USAGE (from the project root):
    python scripts/q1audit_fullscale.py
    # options:
    python scripts/q1audit_fullscale.py --seeds 10 --folds 5

Requires: pandas, numpy, scikit-learn, xgboost.
Outputs (read back by the audit):
    data/reports_q1audit/fullscale_results.json   (summary, read by Claude)
    data/reports_q1audit/fullscale_multiseed.csv  (per-seed rows)
    data/reports_q1audit/fullscale_cv.csv         (per-fold rows)
A compact summary is also printed to stdout; you can paste that back if needed.
"""
import argparse, json, time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import OrdinalEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, average_precision_score, balanced_accuracy_score

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "processed" / "traffic_has_linked_threat.csv"
OUTD = ROOT / "data" / "reports_q1audit"
OUTD.mkdir(parents=True, exist_ok=True)
DROP = ["has_linked_threat", "Session ID", "Receive Time", "Generate Time", "High Res Timestamp"]
XGB = dict(n_estimators=300, max_depth=6, learning_rate=0.08, subsample=0.9,
           colsample_bytree=0.9, eval_metric="logloss", tree_method="hist", n_jobs=-1)


def top_k_precision(y_true, score, k=100):
    order = np.argsort(-score, kind="mergesort")
    return float(np.asarray(y_true)[order][:k].sum()) / k


def load():
    hdr = pd.read_csv(SRC, nrows=0).columns.tolist()
    use = [c for c in hdr if c not in ("Receive Time", "Generate Time", "High Res Timestamp", "Session ID")]
    df = pd.read_csv(SRC, usecols=use)
    y = df["has_linked_threat"].astype(int).to_numpy()
    X = df.drop(columns=["has_linked_threat"])
    cat = [c for c in X.columns if X[c].dtype == object]
    num = [c for c in X.columns if c not in cat]
    return X, y, cat, num


def make_pre(cat, num, scale=False):
    cat_pipe = [("imp", SimpleImputer(strategy="most_frequent")),
                ("enc", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1))]
    num_steps = [("imp", SimpleImputer(strategy="median"))]
    if scale:
        num_steps.append(("sc", StandardScaler()))
    from sklearn.pipeline import Pipeline
    return ColumnTransformer([("c", Pipeline(cat_pipe), cat), ("n", Pipeline(num_steps), num)])


def fit_eval_xgb(Xtr, ytr, Xte, yte, cat, num, seed):
    from xgboost import XGBClassifier
    from sklearn.pipeline import Pipeline
    pre = make_pre(cat, num, scale=False)
    clf = Pipeline([("pre", pre), ("m", XGBClassifier(random_state=seed, **XGB))])
    clf.fit(Xtr, ytr)
    s = clf.predict_proba(Xte)[:, 1]; p = (s >= 0.5).astype(int)
    return dict(macro_f1=float(f1_score(yte, p, average="macro")),
                average_precision=float(average_precision_score(yte, s)),
                balanced_accuracy=float(balanced_accuracy_score(yte, p)),
                pos_recall=float(((p == 1) & (yte == 1)).sum() / max((yte == 1).sum(), 1)),
                top100=top_k_precision(yte, s, 100), top500=top_k_precision(yte, s, 500))


def summ(rows, keys):
    out = {}
    for k in keys:
        v = np.array([r[k] for r in rows], float)
        out[k + "_mean"] = round(float(v.mean()), 4)
        out[k + "_sd"] = round(float(v.std(ddof=1)) if len(v) > 1 else 0.0, 4)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--folds", type=int, default=5)
    a = ap.parse_args()
    t0 = time.time()
    X, y, cat, num = load()
    print(f"loaded {X.shape}, positives={int(y.sum())}, prevalence={y.mean():.4f}")
    res = {"data": {"rows": int(len(y)), "positives": int(y.sum()), "prevalence": round(float(y.mean()), 4),
                    "n_features": X.shape[1], "categorical": len(cat), "numeric": len(num)},
           "xgb_config": XGB}

    # 1) multi-seed (split seed == model seed, like the released followup)
    seeds = [42, 7, 123, 1, 2, 3, 5, 11, 17, 23][:max(a.seeds, 3)]
    ms = []
    for sd in seeds:
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=sd, stratify=y)
        m = fit_eval_xgb(Xtr, ytr, Xte, yte, cat, num, sd); m["seed"] = sd; ms.append(m)
        print(f"  seed {sd}: macroF1={m['macro_f1']:.4f} AP={m['average_precision']:.4f} top100={m['top100']:.2f}")
    pd.DataFrame(ms).to_csv(OUTD / "fullscale_multiseed.csv", index=False)
    res["xgb_multiseed"] = {"seeds": seeds, **summ(ms, ["macro_f1", "average_precision", "top100"]),
                            "per_seed": ms}

    # 2) full-corpus stratified 5-fold CV (seed 42)
    skf = StratifiedKFold(n_splits=a.folds, shuffle=True, random_state=42)
    cv = []
    for i, (tr, te) in enumerate(skf.split(X, y), 1):
        m = fit_eval_xgb(X.iloc[tr], y[tr], X.iloc[te], y[te], cat, num, 42); m["fold"] = i; cv.append(m)
        print(f"  fold {i}: macroF1={m['macro_f1']:.4f} AP={m['average_precision']:.4f} top100={m['top100']:.2f}")
    pd.DataFrame(cv).to_csv(OUTD / "fullscale_cv.csv", index=False)
    res["xgb_cv5"] = {"folds": a.folds, **summ(cv, ["macro_f1", "average_precision", "top100"]), "per_fold": cv}

    # 3) penalized logistic regression baseline (full corpus, seed-42 holdout)
    from sklearn.pipeline import Pipeline
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    lr = Pipeline([("pre", make_pre(cat, num, scale=True)),
                   ("m", LogisticRegression(penalty="l2", class_weight="balanced",
                                            max_iter=1000, n_jobs=-1))])
    lr.fit(Xtr, ytr); s = lr.predict_proba(Xte)[:, 1]; p = (s >= 0.5).astype(int)
    res["logistic_full"] = dict(macro_f1=round(float(f1_score(yte, p, average="macro")), 4),
                                average_precision=round(float(average_precision_score(yte, s)), 4),
                                pos_precision=round(float(((p == 1) & (yte == 1)).sum() / max((p == 1).sum(), 1)), 4),
                                pos_recall=round(float(((p == 1) & (yte == 1)).sum() / max((yte == 1).sum(), 1)), 4),
                                top100=top_k_precision(yte, s, 100), top500=round(top_k_precision(yte, s, 500), 4))
    res["runtime_secs"] = round(time.time() - t0, 1)
    (OUTD / "fullscale_results.json").write_text(json.dumps(res, indent=2))
    print("\n=== SUMMARY ===")
    print(json.dumps({k: res[k] for k in ["xgb_multiseed", "xgb_cv5", "logistic_full"]}, indent=2, default=str)[:2000])
    print("\nWrote:", OUTD / "fullscale_results.json")


if __name__ == "__main__":
    main()
