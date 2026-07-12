"""Corrected same-session linkage and group-disjoint evaluation pipeline.

Restricted raw exports are read locally. Only aggregate metrics and provenance
are written; row-level labels, identifiers, addresses, and timestamps never
leave memory.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import beta
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder, StandardScaler


CORE = [
    "Action", "Threat/Content Type", "Session End Reason", "Application",
    "Source Zone", "Destination Zone", "Inbound Interface", "Outbound Interface",
    "IP Protocol", "Source Port", "Destination Port", "Source Country",
    "Destination Country", "Category", "Bytes", "Bytes Sent", "Bytes Received",
    "Packets", "Packets Sent", "Packets Received", "Elapsed Time (sec)",
    "Subcategory of app", "Category of app", "Technology of app", "Risk of app",
    "SaaS of app", "AI Traffic",
]
OUTCOME = {"Action", "Threat/Content Type", "Session End Reason"}
HARD_PROXY = OUTCOME | {
    "Application", "Subcategory of app", "Category of app", "Technology of app",
    "Risk of app", "SaaS of app", "AI Traffic", "Source Port", "Destination Port",
    "IP Protocol", "Source Zone", "Destination Zone", "Inbound Interface",
    "Outbound Interface", "Source Country", "Destination Country", "Category",
}
NS = ["Serial #", "Virtual System", "Session ID"]
DIRECT = ["Source address", "Destination address", "Source Port", "Destination Port", "IP Protocol"]
NAT = ["NAT Source IP", "NAT Destination IP", "NAT Source Port", "NAT Destination Port", "IP Protocol"]
TRAFFIC_COLS = list(dict.fromkeys(NS + ["Device Name", "Start Time", "Generate Time"] + DIRECT + NAT))
THREAT_COLS = list(dict.fromkeys(NS + ["Device Name", "Generate Time"] + DIRECT + NAT))
SEEDS = [13, 42, 73, 101, 137]


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--traffic", default="data/restricted_source_data/raw/trafik.csv")
    p.add_argument("--threat", default="data/restricted_source_data/raw/threat.csv")
    p.add_argument("--processed", default="data/processed/traffic_has_linked_threat.csv")
    p.add_argument("--outdir", required=True)
    p.add_argument("--quick", action="store_true", help="Run only XGBoost primary scenarios.")
    return p.parse_args()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tuple_equal(left: pd.DataFrame, lcols: list[str], right: pd.DataFrame, rcols: list[str]) -> np.ndarray:
    mask = np.ones(len(left), dtype=bool)
    for lc, rc in zip(lcols, rcols):
        mask &= left[lc].astype(str).to_numpy() == right[rc].astype(str).to_numpy()
    return mask


def construct_label(traffic: pd.DataFrame, threat: pd.DataFrame) -> tuple[np.ndarray, dict]:
    for frame in (traffic, threat):
        frame["Generate Time"] = pd.to_datetime(frame["Generate Time"], errors="coerce")
    traffic["Start Time"] = pd.to_datetime(traffic["Start Time"], errors="coerce")
    threat_nz = threat.loc[threat["Session ID"].ne(0)].copy()
    candidates = traffic.reset_index(names="traffic_row").merge(
        threat_nz, on=NS, how="inner", suffixes=("_traffic", "_threat")
    )
    start = candidates["Start Time"].fillna(candidates["Generate Time_traffic"])
    tolerance_sets: dict[int, set[int]] = {}
    for tol in (0, 30, 60, 300):
        valid = candidates["Generate Time_threat"].between(
            start - pd.Timedelta(seconds=tol),
            candidates["Generate Time_traffic"] + pd.Timedelta(seconds=tol),
            inclusive="both",
        )
        tolerance_sets[tol] = set(candidates.loc[valid, "traffic_row"].astype(int))
    temporal = candidates["Generate Time_threat"].between(
        start - pd.Timedelta(seconds=30),
        candidates["Generate Time_traffic"] + pd.Timedelta(seconds=30),
        inclusive="both",
    )
    timed = candidates.loc[temporal].copy()
    direct_l = [f"{c}_traffic" for c in DIRECT]
    direct_r = [f"{c}_threat" for c in DIRECT]
    nat_l = [f"{c}_traffic" for c in NAT]
    nat_r = [f"{c}_threat" for c in NAT]
    direct_match = tuple_equal(timed, direct_l, timed, direct_r)
    traffic_nat_to_threat_direct = tuple_equal(timed, nat_l, timed, direct_r)
    traffic_direct_to_threat_nat = tuple_equal(timed, direct_l, timed, nat_r)
    nat_match = direct_match | traffic_nat_to_threat_direct | traffic_direct_to_threat_nat
    positive_rows = tolerance_sets[30]
    y = np.zeros(len(traffic), dtype=np.int8)
    y[list(positive_rows)] = 1
    multiplicity = timed.groupby("traffic_row").size()
    audit = {
        "privacy": "aggregate_only_no_row_level_output",
        "traffic_rows": int(len(traffic)),
        "threat_rows": int(len(threat)),
        "corrected_positive_rows": int(y.sum()),
        "corrected_prevalence": float(y.mean()),
        "tolerance_positive_rows": {str(k): len(v) for k, v in tolerance_sets.items()},
        "exact_direct_tuple_rows": int(timed.loc[direct_match, "traffic_row"].nunique()),
        "nat_aware_tuple_rows": int(timed.loc[nat_match, "traffic_row"].nunique()),
        "temporal_rows_without_direct_tuple": int(len(positive_rows - set(timed.loc[direct_match, "traffic_row"].astype(int)))),
        "temporal_rows_without_nat_aware_tuple": int(len(positive_rows - set(timed.loc[nat_match, "traffic_row"].astype(int)))),
        "positive_rows_with_multiple_candidate_events": int((multiplicity > 1).sum()),
        "maximum_candidate_events_per_positive_row": int(multiplicity.max()) if len(multiplicity) else 0,
        "namespace_count_traffic": int(traffic[["Serial #", "Virtual System", "Device Name"]].drop_duplicates().shape[0]),
        "namespace_count_threat": int(threat[["Serial #", "Virtual System", "Device Name"]].drop_duplicates().shape[0]),
    }
    return y, audit


def groups_and_split(traffic: pd.DataFrame, y: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict, list[tuple[np.ndarray, np.ndarray]]]:
    instance = traffic[["Serial #", "Virtual System", "Session ID", "Start Time"]].copy()
    instance["Start Time"] = instance["Start Time"].fillna(traffic["Generate Time"])
    groups = pd.util.hash_pandas_object(instance, index=False).to_numpy(dtype=np.uint64)
    zero = traffic["Session ID"].eq(0).to_numpy()
    groups[zero] = np.arange(len(traffic), dtype=np.uint64)[zero] ^ np.uint64(0x9E3779B97F4A7C15)
    meta = pd.DataFrame({"group": groups, "time": traffic["Generate Time"], "y": y})
    gm = meta.groupby("group", sort=False).agg(time=("time", "min"), rows=("group", "size"), y=("y", "max"))
    gm = gm.sort_values("time", kind="mergesort")
    cut = int(0.8 * len(gm))
    train_groups = gm.index[:cut].to_numpy(dtype=np.uint64)
    test_groups = gm.index[cut:].to_numpy(dtype=np.uint64)
    train = np.flatnonzero(np.isin(groups, train_groups, assume_unique=False))
    test = np.flatnonzero(np.isin(groups, test_groups, assume_unique=False))
    split = {
        "group_definition": "hash(Serial, Virtual System, Session ID, Start Time); zero IDs row-unique",
        "train_rows": int(len(train)), "test_rows": int(len(test)),
        "train_groups": int(len(train_groups)), "test_groups": int(len(test_groups)),
        "group_overlap": int(np.intersect1d(train_groups, test_groups, assume_unique=True).size),
        "train_positives": int(y[train].sum()), "test_positives": int(y[test].sum()),
        "test_prevalence": float(y[test].mean()),
        "cutoff_time": str(gm.iloc[cut]["time"]),
    }
    rolling: list[tuple[np.ndarray, np.ndarray]] = []
    for train_frac in (0.4, 0.6, 0.8):
        a = int(train_frac * len(gm)); b = int((train_frac + 0.2) * len(gm))
        fold_train_groups = gm.index[:a].to_numpy(dtype=np.uint64)
        fold_test_groups = gm.index[a:b].to_numpy(dtype=np.uint64)
        fold_train = np.flatnonzero(np.isin(groups, fold_train_groups, assume_unique=False))
        fold_test = np.flatnonzero(np.isin(groups, fold_test_groups, assume_unique=False))
        rolling.append((fold_train, fold_test))
    return groups, train, test, split, rolling


def preprocessor(X: pd.DataFrame, scale: bool = False) -> ColumnTransformer:
    cat = [c for c in X.columns if not pd.api.types.is_numeric_dtype(X[c])]
    num = [c for c in X.columns if c not in cat]
    num_steps: list[tuple[str, object]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale:
        num_steps.append(("scale", StandardScaler()))
    return ColumnTransformer([
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                           ("encode", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1))]), cat),
        ("num", Pipeline(num_steps), num),
    ], verbose_feature_names_out=False)


def model(name: str, seed: int):
    if name == "XGBoost":
        from xgboost import XGBClassifier
        return XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.08, subsample=0.9,
                             colsample_bytree=0.9, eval_metric="logloss", tree_method="hist",
                             random_state=seed, n_jobs=-1)
    if name == "Extra Trees":
        return ExtraTreesClassifier(n_estimators=200, class_weight="balanced", random_state=seed, n_jobs=-1)
    if name == "LightGBM":
        from lightgbm import LGBMClassifier
        return LGBMClassifier(n_estimators=300, learning_rate=0.08, class_weight="balanced",
                              random_state=seed, n_jobs=-1, verbosity=-1)
    if name == "CatBoost":
        from catboost import CatBoostClassifier
        return CatBoostClassifier(iterations=300, depth=6, learning_rate=0.08,
                                  auto_class_weights="Balanced", random_seed=seed,
                                  verbose=False, allow_writing_files=False)
    if name == "Logistic Regression":
        return SGDClassifier(loss="log_loss", penalty="l2", alpha=1e-4, class_weight="balanced",
                             max_iter=2000, tol=1e-4, random_state=seed, average=True)
    raise ValueError(name)


def cp_interval(successes: int, n: int, alpha: float = 0.05) -> list[float]:
    lo = 0.0 if successes == 0 else float(beta.ppf(alpha / 2, successes, n - successes + 1))
    hi = 1.0 if successes == n else float(beta.ppf(1 - alpha / 2, successes + 1, n - successes))
    return [lo, hi]


def evaluate(name: str, feature_set: str, X: pd.DataFrame, y: np.ndarray, groups: np.ndarray,
             train: np.ndarray, test: np.ndarray, seed: int, evaluation: str) -> tuple[dict, list[dict]]:
    use = CORE if feature_set == "full_core" else [c for c in CORE if c not in (OUTCOME if feature_set == "no_outcome" else HARD_PROXY)]
    use = [c for c in use if c in X.columns]
    pipe = Pipeline([("preprocess", preprocessor(X[use], name == "Logistic Regression")), ("model", model(name, seed))])
    start = time.perf_counter(); pipe.fit(X.iloc[train][use], y[train]); fit = time.perf_counter() - start
    score = pipe.predict_proba(X.iloc[test][use])[:, 1]
    pred = (score >= 0.5).astype(np.int8)
    yt = y[test]
    tn, fp, fn, tp = confusion_matrix(yt, pred, labels=[0, 1]).ravel()
    cases = pd.DataFrame({"group": groups[test], "y": yt, "score": score}).groupby("group", sort=False).agg(y=("y", "max"), score=("score", "max"))
    cases = cases.sort_values("score", ascending=False, kind="mergesort")
    topk = []
    total_pos = int(cases["y"].sum())
    for k in (50, 100, 250, 500, 1000):
        n = min(k, len(cases)); hits = int(cases.iloc[:n]["y"].sum())
        topk.append({"evaluation": evaluation, "model": name, "feature_set": feature_set, "seed": seed, "k": n,
                     "true_positives": hits, "precision": hits / n,
                     "recall": hits / total_pos if total_pos else 0.0,
                     "precision_cp95": cp_interval(hits, n)})
    result = {
        "evaluation": evaluation, "model": name, "feature_set": feature_set, "seed": seed, "features": len(use),
        "fit_seconds": fit, "test_rows": int(len(test)), "test_positives": int(yt.sum()),
        "accuracy": float(np.mean(pred == yt)),
        "balanced_accuracy": float(balanced_accuracy_score(yt, pred)),
        "macro_f1": float(f1_score(yt, pred, average="macro", zero_division=0)),
        "average_precision": float(average_precision_score(yt, score)),
        "roc_auc": float(roc_auc_score(yt, score)),
        "positive_precision": float(precision_score(yt, pred, zero_division=0)),
        "positive_recall": float(recall_score(yt, pred, zero_division=0)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }
    return result, topk


def main() -> None:
    a = args(); out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    started = pd.Timestamp.now(tz="Europe/Istanbul").isoformat(); wall = time.perf_counter()
    traffic_path, threat_path, processed_path = map(Path, (a.traffic, a.threat, a.processed))
    print("STAGE read restricted raw inputs", flush=True)
    traffic = pd.read_csv(traffic_path, usecols=TRAFFIC_COLS, low_memory=False)
    threat = pd.read_csv(threat_path, usecols=THREAT_COLS, low_memory=False)
    print("STAGE construct corrected label", flush=True)
    y, label_audit = construct_label(traffic, threat)
    del threat
    gc.collect()
    print("STAGE construct composite groups and chronological split", flush=True)
    groups, train, test, split, rolling = groups_and_split(traffic, y)
    print("STAGE read aligned predictor table", flush=True)
    X = pd.read_csv(processed_path, usecols=["Session ID", "has_linked_threat", *CORE], low_memory=False)
    if len(X) != len(traffic) or not np.array_equal(X["Session ID"].to_numpy(), traffic["Session ID"].to_numpy()):
        raise ValueError("Processed predictors do not align with restricted traffic rows")
    del traffic
    gc.collect()
    results: list[dict] = []; topk: list[dict] = []
    scenarios = [("XGBoost", "full_core"), ("XGBoost", "no_outcome"), ("XGBoost", "hard_proxy")]
    if not a.quick:
        scenarios += [(m, "no_outcome") for m in ("Extra Trees", "LightGBM", "CatBoost", "Logistic Regression")]
    for name, fs in scenarios:
        print(f"RUN {name} / {fs}", flush=True)
        r, t = evaluate(name, fs, X, y, groups, train, test, 42, "primary_later_20pct"); results.append(r); topk.extend(t)
    for seed in SEEDS:
        if seed == 42:
            continue
        print(f"RUN XGBoost / no_outcome / seed={seed}", flush=True)
        r, t = evaluate("XGBoost", "no_outcome", X, y, groups, train, test, seed, "primary_later_20pct"); results.append(r); topk.extend(t)
    for fold, (fold_train, fold_test) in enumerate(rolling, start=1):
        print(f"RUN rolling-origin fold={fold}", flush=True)
        r, t = evaluate("XGBoost", "no_outcome", X, y, groups, fold_train, fold_test, 42,
                        f"rolling_origin_fold_{fold}")
        results.append(r); topk.extend(t)
    dns = X.iloc[test]["Application"].astype(str).eq("dns-base").to_numpy()
    dns_ap = float(average_precision_score(y[test], dns.astype(float)))
    payload = {
        "status": "COMPLETE_CORRECTED_LABEL_GROUP_DISJOINT",
        "created_at": pd.Timestamp.now(tz="Europe/Istanbul").isoformat(),
        "started_at": started,
        "runtime_seconds": time.perf_counter() - wall,
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "host": platform.node(), "logical_cpu": os.cpu_count()},
        "input_provenance": {"traffic_sha256": sha256(traffic_path), "threat_sha256": sha256(threat_path),
                             "processed_sha256": sha256(processed_path)},
        "label_audit": label_audit, "split": split,
        "random_ranking_average_precision": split["test_prevalence"],
        "dns_rule_average_precision": dns_ap,
        "results": results, "topk": topk,
        "limitations": [
            "One organization and one approximately 47-minute traffic window.",
            "The target is retrospective same-session threat-log linkage, not future maliciousness prediction.",
            "Seed reruns characterize fit/rank variability; they are not a population-level confidence interval.",
        ],
    }
    (out / "corrected_linkage_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    pd.DataFrame(results).to_csv(out / "corrected_linkage_metrics.csv", index=False)
    tk = pd.DataFrame(topk); tk["precision_cp95"] = tk["precision_cp95"].map(json.dumps)
    tk.to_csv(out / "corrected_linkage_topk.csv", index=False)
    summary = pd.DataFrame(results)[["evaluation", "model", "feature_set", "seed", "macro_f1", "average_precision", "roc_auc", "positive_precision", "positive_recall", "tp", "fp"]]
    md = ["# Corrected Same-Session Linkage Results", "",
          f"- Corrected positives: {label_audit['corrected_positive_rows']:,} / {label_audit['traffic_rows']:,} ({100*label_audit['corrected_prevalence']:.4f}%).",
          f"- Primary split: later chronological, composite-session group-disjoint; train/test positives {split['train_positives']}/{split['test_positives']}; group overlap {split['group_overlap']}.",
          f"- Exact direct tuple rows: {label_audit['exact_direct_tuple_rows']:,}; NAT-aware tuple rows: {label_audit['nat_aware_tuple_rows']:,}.",
          f"- Random-ranking AP: {payload['random_ranking_average_precision']:.6f}; DNS-rule AP: {dns_ap:.6f}.", "", "## Model results", "", summary.to_markdown(index=False, floatfmt=".6f"), "", "## Interpretation", "",
          "These results estimate retrospective same-session threat-log linkage inside the observed export. They do not establish future attack detection, analyst-effort reduction, deployment utility, or cross-organization generalization."]
    (out / "corrected_linkage_summary.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "label": label_audit, "split": split,
                      "runtime_seconds": payload["runtime_seconds"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
