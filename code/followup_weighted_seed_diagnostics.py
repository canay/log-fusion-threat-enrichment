"""Follow-up diagnostics requested in the 2026-06-05 reviewer simulation.

Runs, on the processed modeling table, four XGBoost fits with the released
benchmark configuration (300 trees, depth 6, lr 0.08, subsample/colsample 0.9,
hist) under a stratified 80/20 split:
  1) unweighted, seed 42  - in-environment reference
  2) scale_pos_weight=N/P, seed 42  - class-weighted variant (reviewer request)
  3) unweighted, seed 7   - seed-stability
  4) unweighted, seed 123 - seed-stability
Both the split and the model are re-seeded per run. Preprocessing mirrors the
released pipeline semantics with train-only statistics: categorical NaN -> train
mode, train-vocabulary ordinal codes with unseen->-1; numeric NaN -> train median.
Environment: Cowork Linux sandbox, 2 CPU cores; results are an independent
diagnostic environment, not a re-statement of the VPS numbers.
Output: data/reports_presubmission/followup_runs/followup_metrics.csv (+ .log)
"""
import json, time, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC  = ROOT / "data/processed/traffic_has_linked_threat.csv"
OUTD = ROOT / "data/reports_presubmission/followup_runs"
OUTD.mkdir(parents=True, exist_ok=True)
CSVO = OUTD / "followup_metrics.csv"
LOG  = OUTD / "followup.log"

def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f: f.write(line + "\n")

DROP = ["has_linked_threat", "Session ID", "Receive Time", "Generate Time", "High Res Timestamp"]

def load():
    log("CSV yukleniyor...")
    df = pd.read_csv(SRC, low_memory=False)
    y = df["has_linked_threat"].astype(np.int8).values
    X = df.drop(columns=DROP)
    cat = [c for c in X.columns if X[c].dtype == object]
    num = [c for c in X.columns if c not in cat]
    for c in cat: X[c] = X[c].astype("category")
    for c in num: X[c] = pd.to_numeric(X[c], errors="coerce").astype(np.float32)
    log(f"yuklendi: {X.shape}, cat={len(cat)} num={len(num)}")
    return X, y, cat, num

def strat_split(y, seed, test_frac=0.2):
    rng = np.random.default_rng(seed)
    tr_idx, te_idx = [], []
    for cls in (0, 1):
        idx = np.where(y == cls)[0]; rng.shuffle(idx)
        k = int(round(len(idx) * test_frac))
        te_idx.append(idx[:k]); tr_idx.append(idx[k:])
    tr = np.concatenate(tr_idx); te = np.concatenate(te_idx)
    rng.shuffle(tr); rng.shuffle(te)
    return tr, te

def encode(X, cat, num, tr, te):
    Xtr = np.empty((len(tr), X.shape[1]), dtype=np.float32)
    Xte = np.empty((len(te), X.shape[1]), dtype=np.float32)
    for j, c in enumerate(X.columns):
        col = X[c]
        if c in cat:
            s_tr = col.iloc[tr]
            mode = s_tr.mode(dropna=True)
            fillv = mode.iloc[0] if len(mode) else "missing"
            s_tr = s_tr.cat.add_categories([fillv]) if fillv not in s_tr.cat.categories else s_tr
            s_tr = s_tr.fillna(fillv)
            vocab = pd.Index(s_tr.unique())
            m = {v: i for i, v in enumerate(vocab)}
            Xtr[:, j] = np.asarray([m[v] for v in s_tr], dtype=np.float32)
            s_te = col.iloc[te].astype(object)
            s_te = pd.Series(np.where(pd.isna(s_te), fillv, s_te))
            Xte[:, j] = np.asarray([m.get(v, -1) for v in s_te], dtype=np.float32)
        else:
            v = col.values
            med = np.nanmedian(v[tr])
            a = v[tr].copy(); a[np.isnan(a)] = med; Xtr[:, j] = a
            b = v[te].copy(); b[np.isnan(b)] = med; Xte[:, j] = b
    return Xtr, Xte

def average_precision(y, s):
    o = np.argsort(-s, kind="mergesort"); y = y[o]
    tp = np.cumsum(y); fp = np.cumsum(1 - y)
    P = tp / (tp + fp); pos = y.sum()
    R = tp / pos
    dR = np.diff(np.concatenate([[0.0], R]))
    return float((P * dR).sum())

def roc_auc(y, s):
    r = pd.Series(s).rank(method="average").values
    pos = y == 1; n1 = pos.sum(); n0 = len(y) - n1
    return float((r[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))

def metrics(y, s, thr=0.5):
    p = (s >= thr).astype(np.int8)
    tp = int(((p == 1) & (y == 1)).sum()); fp = int(((p == 1) & (y == 0)).sum())
    fn = int(((p == 0) & (y == 1)).sum()); tn = int(((p == 0) & (y == 0)).sum())
    prec1 = tp / (tp + fp) if tp + fp else 0.0; rec1 = tp / (tp + fn)
    prec0 = tn / (tn + fn) if tn + fn else 0.0; rec0 = tn / (tn + fp)
    f1 = 2 * prec1 * rec1 / (prec1 + rec1) if prec1 + rec1 else 0.0
    f0 = 2 * prec0 * rec0 / (prec0 + rec0) if prec0 + rec0 else 0.0
    o = np.argsort(-s, kind="mergesort")
    res = {
        "accuracy": (tp + tn) / len(y), "balanced_accuracy": (rec1 + rec0) / 2,
        "macro_f1": (f1 + f0) / 2, "average_precision": average_precision(y, s),
        "roc_auc": roc_auc(y, s), "pos_precision": prec1, "pos_recall": rec1,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }
    for k in (100, 500):
        res[f"top{k}_precision"] = float(y[o[:k]].mean())
    return res

def run(tag, seed, weighted, X, y, cat, num):
    from xgboost import XGBClassifier
    t0 = time.time()
    tr, te = strat_split(y, seed)
    log(f"[{tag}] split tamam (train={len(tr)} test={len(te)} pos_test={int(y[te].sum())})")
    Xtr, Xte = encode(X, cat, num, tr, te)
    log(f"[{tag}] encode tamam ({time.time()-t0:.0f}s)")
    spw = float((y[tr] == 0).sum() / (y[tr] == 1).sum()) if weighted else 1.0
    clf = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.08,
                        subsample=0.9, colsample_bytree=0.9, tree_method="hist",
                        random_state=seed, n_jobs=2, scale_pos_weight=spw,
                        eval_metric="logloss")
    clf.fit(Xtr, y[tr])
    log(f"[{tag}] fit tamam ({time.time()-t0:.0f}s)")
    s = clf.predict_proba(Xte)[:, 1]
    m = metrics(y[te], s)
    m.update({"run": tag, "seed": seed, "scale_pos_weight": round(spw, 2),
              "wall_seconds": round(time.time() - t0, 1)})
    row = pd.DataFrame([m])
    header = not CSVO.exists()
    row.to_csv(CSVO, mode="a", header=header, index=False)
    log(f"[{tag}] BITTI macroF1={m['macro_f1']:.4f} AP={m['average_precision']:.4f} "
        f"AUC={m['roc_auc']:.4f} posP={m['pos_precision']:.4f} posR={m['pos_recall']:.4f} "
        f"top100={m['top100_precision']:.2f}")
    del Xtr, Xte, clf, s

if __name__ == "__main__":
    log("=== followup diagnostics basladi ===")
    X, y, cat, num = load()
    for tag, seed, w in [("unweighted_s42", 42, False), ("weighted_s42", 42, True),
                          ("unweighted_s7", 7, False), ("unweighted_s123", 123, False)]:
        try:
            run(tag, seed, w, X, y, cat, num)
        except Exception as e:
            log(f"[{tag}] HATA: {e!r}")
    log("=== tamamlandi ===")
