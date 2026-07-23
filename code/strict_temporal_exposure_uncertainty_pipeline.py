"""Strict-temporal corrected-linkage pipeline with exposure and uncertainty audits.

The two raw firewall exports are read only on the local workstation.  A
restricted aligned predictor table may be written locally, but every experiment
artifact under ``out/`` is aggregate-only: no addresses, identifiers, absolute
timestamps, row-level labels, group hashes, or predictions are serialized.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
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
VOLUME = [
    "Bytes", "Bytes Sent", "Bytes Received", "Packets", "Packets Sent",
    "Packets Received",
]
NS = ["Serial #", "Virtual System", "Session ID"]
DIRECT = ["Source address", "Destination address", "Source Port", "Destination Port", "IP Protocol"]
NAT = ["NAT Source IP", "NAT Destination IP", "NAT Source Port", "NAT Destination Port", "IP Protocol"]
TRAFFIC_COLS = list(dict.fromkeys(NS + ["Device Name", "Start Time", "Generate Time"] + DIRECT + NAT + CORE))
THREAT_COLS = list(dict.fromkeys(NS + ["Device Name", "Generate Time"] + DIRECT + NAT))
SEEDS = [13, 42, 73, 101, 137]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--traffic", default="data/restricted_source_data/raw/trafik.csv")
    parser.add_argument("--threat", default="data/restricted_source_data/raw/threat.csv")
    parser.add_argument(
        "--derived",
        default="data/restricted_source_data/derived/corrected_linkage_predictors_strict_20260717.csv",
    )
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--bootstrap-reps", type=int, default=500)
    parser.add_argument("--bootstrap-blocks", type=int, default=20)
    parser.add_argument("--skip-derived-write", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_versions() -> dict[str, str]:
    names = ["numpy", "pandas", "scipy", "scikit-learn", "xgboost", "lightgbm", "catboost"]
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "not-installed"
    return versions


def row_order_signature(frame: pd.DataFrame) -> str:
    """Return one non-reversible digest over the ordered restricted row keys."""
    digest = hashlib.sha256()
    cols = ["Serial #", "Virtual System", "Session ID", "Start Time", "Generate Time"]
    for start in range(0, len(frame), 200_000):
        part = frame.iloc[start : start + 200_000][cols]
        hashed = pd.util.hash_pandas_object(part, index=True).to_numpy(dtype=np.uint64)
        digest.update(hashed.tobytes())
    return digest.hexdigest()


def write_restricted_derived(path: Path, traffic: pd.DataFrame, target: np.ndarray) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    first = True
    for start in range(0, len(traffic), 200_000):
        stop = min(start + 200_000, len(traffic))
        part = traffic.iloc[start:stop][CORE].copy()
        part.insert(0, "corrected_same_session_label", target[start:stop])
        part.to_csv(path, index=False, mode="w" if first else "a", header=first, encoding="utf-8")
        first = False
    return {
        "path": str(path),
        "sha256": sha256(path),
        "rows": int(len(traffic)),
        "columns": int(1 + len(CORE)),
        "schema_sha256": hashlib.sha256(
            json.dumps(["corrected_same_session_label", *CORE], separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "classification": "restricted_local_row_level_do_not_publish",
    }


def complete_tuple_equal(frame: pd.DataFrame, left: list[str], right: list[str]) -> np.ndarray:
    complete = frame[left + right].notna().all(axis=1).to_numpy()
    equal = np.ones(len(frame), dtype=bool)
    for left_col, right_col in zip(left, right):
        equal &= frame[left_col].astype(str).to_numpy() == frame[right_col].astype(str).to_numpy()
    return complete & equal


def loose_tuple_equal(frame: pd.DataFrame, left: list[str], right: list[str]) -> np.ndarray:
    equal = np.ones(len(frame), dtype=bool)
    for left_col, right_col in zip(left, right):
        equal &= frame[left_col].astype(str).to_numpy() == frame[right_col].astype(str).to_numpy()
    return equal


def construct_label(traffic: pd.DataFrame, threat: pd.DataFrame) -> tuple[np.ndarray, dict]:
    raw_missing = {
        "traffic_namespace_incomplete": int(traffic[NS].isna().any(axis=1).sum()),
        "threat_namespace_incomplete": int(threat[NS].isna().any(axis=1).sum()),
        "traffic_direct_tuple_incomplete": int(traffic[DIRECT].isna().any(axis=1).sum()),
        "threat_direct_tuple_incomplete": int(threat[DIRECT].isna().any(axis=1).sum()),
        "traffic_nat_tuple_incomplete": int(traffic[NAT].isna().any(axis=1).sum()),
        "threat_nat_tuple_incomplete": int(threat[NAT].isna().any(axis=1).sum()),
    }
    for frame in (traffic, threat):
        frame["Generate Time"] = pd.to_datetime(frame["Generate Time"], errors="coerce")
    traffic["Start Time"] = pd.to_datetime(traffic["Start Time"], errors="coerce")
    parse = {
        "traffic_generate_time_failures": int(traffic["Generate Time"].isna().sum()),
        "traffic_start_time_failures": int(traffic["Start Time"].isna().sum()),
        "threat_generate_time_failures": int(threat["Generate Time"].isna().sum()),
        "traffic_missing_session_id": int(traffic["Session ID"].isna().sum()),
        "threat_missing_session_id": int(threat["Session ID"].isna().sum()),
        "traffic_zero_session_id": int(traffic["Session ID"].eq(0).sum()),
        "threat_zero_session_id": int(threat["Session ID"].eq(0).sum()),
    }
    required_failure = (
        raw_missing["traffic_namespace_incomplete"]
        + raw_missing["threat_namespace_incomplete"]
        + parse["traffic_generate_time_failures"]
        + parse["threat_generate_time_failures"]
        + parse["traffic_missing_session_id"]
        + parse["threat_missing_session_id"]
    )
    if required_failure:
        raise ValueError(f"Fail-closed required-field audit failed: {required_failure} rows")

    threat_nonzero = threat.loc[threat["Session ID"].ne(0)].copy()
    candidates = traffic.reset_index(names="traffic_row").merge(
        threat_nonzero, on=NS, how="inner", suffixes=("_traffic", "_threat")
    )
    fallback = candidates["Start Time"].isna()
    start = candidates["Start Time"].fillna(candidates["Generate Time_traffic"])
    tolerance_sets: dict[int, set[int]] = {}
    for tolerance in (0, 30, 60, 300):
        valid = candidates["Generate Time_threat"].between(
            start - pd.Timedelta(seconds=tolerance),
            candidates["Generate Time_traffic"] + pd.Timedelta(seconds=tolerance),
            inclusive="both",
        )
        tolerance_sets[tolerance] = set(candidates.loc[valid, "traffic_row"].astype(int))

    temporal = candidates["Generate Time_threat"].between(
        start - pd.Timedelta(seconds=30),
        candidates["Generate Time_traffic"] + pd.Timedelta(seconds=30),
        inclusive="both",
    )
    timed = candidates.loc[temporal].copy()
    direct_left = [f"{column}_traffic" for column in DIRECT]
    direct_right = [f"{column}_threat" for column in DIRECT]
    nat_left = [f"{column}_traffic" for column in NAT]
    nat_right = [f"{column}_threat" for column in NAT]

    direct_strict = complete_tuple_equal(timed, direct_left, direct_right)
    nat_to_direct_strict = complete_tuple_equal(timed, nat_left, direct_right)
    direct_to_nat_strict = complete_tuple_equal(timed, direct_left, nat_right)
    nat_aware_strict = direct_strict | nat_to_direct_strict | direct_to_nat_strict
    direct_loose = loose_tuple_equal(timed, direct_left, direct_right)
    nat_aware_loose = (
        direct_loose
        | loose_tuple_equal(timed, nat_left, direct_right)
        | loose_tuple_equal(timed, direct_left, nat_right)
    )

    positive_rows = tolerance_sets[30]
    target = np.zeros(len(traffic), dtype=np.int8)
    target[list(positive_rows)] = 1
    multiplicity = timed.groupby("traffic_row").size()
    fallback_positive_rows = set(timed.loc[fallback.loc[timed.index], "traffic_row"].astype(int))
    direct_strict_rows = set(timed.loc[direct_strict, "traffic_row"].astype(int))
    nat_strict_rows = set(timed.loc[nat_aware_strict, "traffic_row"].astype(int))
    direct_loose_rows = set(timed.loc[direct_loose, "traffic_row"].astype(int))
    nat_loose_rows = set(timed.loc[nat_aware_loose, "traffic_row"].astype(int))

    audit = {
        "privacy": "aggregate_only_no_row_level_output",
        "fail_closed_required_fields": "PASS",
        "traffic_rows": int(len(traffic)),
        "threat_rows": int(len(threat)),
        "parse_and_required_field_audit": {**parse, **raw_missing},
        "candidate_event_rows_before_temporal_filter": int(len(candidates)),
        "candidate_traffic_rows_before_temporal_filter": int(candidates["traffic_row"].nunique()),
        "corrected_positive_rows": int(target.sum()),
        "corrected_prevalence": float(target.mean()),
        "tolerance_positive_rows": {str(key): len(value) for key, value in tolerance_sets.items()},
        "start_time_fallback_candidate_rows": int(fallback.sum()),
        "positive_rows_relying_on_start_time_fallback": int(len(fallback_positive_rows)),
        "exact_direct_tuple_rows_fail_closed": int(len(direct_strict_rows)),
        "nat_aware_tuple_rows_fail_closed": int(len(nat_strict_rows)),
        "exact_direct_tuple_rows_loose_missing_equals_missing": int(len(direct_loose_rows)),
        "nat_aware_tuple_rows_loose_missing_equals_missing": int(len(nat_loose_rows)),
        "direct_rows_added_only_by_missing_missing_equality": int(len(direct_loose_rows - direct_strict_rows)),
        "nat_aware_rows_added_only_by_missing_missing_equality": int(len(nat_loose_rows - nat_strict_rows)),
        "temporal_rows_without_fail_closed_direct_tuple": int(len(positive_rows - direct_strict_rows)),
        "temporal_rows_without_fail_closed_nat_aware_tuple": int(len(positive_rows - nat_strict_rows)),
        "positive_rows_with_multiple_candidate_events": int((multiplicity > 1).sum()),
        "maximum_candidate_events_per_positive_row": int(multiplicity.max()) if len(multiplicity) else 0,
        "namespace_count_traffic": int(traffic[["Serial #", "Virtual System", "Device Name"]].drop_duplicates().shape[0]),
        "namespace_count_threat": int(threat[["Serial #", "Virtual System", "Device Name"]].drop_duplicates().shape[0]),
    }
    return target, audit


def select_indices(groups: np.ndarray, selected: np.ndarray) -> np.ndarray:
    return np.flatnonzero(np.isin(groups, selected, assume_unique=False))


def split_invariants(
    traffic: pd.DataFrame, target: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict, list[tuple[np.ndarray, np.ndarray, dict]]]:
    instance = traffic[["Serial #", "Virtual System", "Session ID", "Start Time"]].copy()
    instance["Start Time"] = instance["Start Time"].fillna(traffic["Generate Time"])
    groups = pd.util.hash_pandas_object(instance, index=False).to_numpy(dtype=np.uint64).copy()
    zero = traffic["Session ID"].eq(0).to_numpy()
    groups[zero] = np.arange(len(traffic), dtype=np.uint64)[zero] ^ np.uint64(0x9E3779B97F4A7C15)
    meta = pd.DataFrame({"group": groups, "time": traffic["Generate Time"], "y": target})
    grouped = meta.groupby("group", sort=False).agg(
        min_time=("time", "min"), max_time=("time", "max"), rows=("group", "size"), y=("y", "max")
    )
    grouped = grouped.sort_values("min_time", kind="mergesort")
    n_groups = len(grouped)
    target_cut = int(0.8 * n_groups)
    cutoff = grouped.iloc[target_cut]["min_time"]

    original_train_groups = grouped.index[:target_cut].to_numpy(dtype=np.uint64)
    original_test_groups = grouped.index[target_cut:].to_numpy(dtype=np.uint64)
    original_train = select_indices(groups, original_train_groups)
    original_test = select_indices(groups, original_test_groups)

    train_group_frame = grouped[(grouped["min_time"] < cutoff) & (grouped["max_time"] < cutoff)]
    purged_group_frame = grouped[(grouped["min_time"] < cutoff) & (grouped["max_time"] >= cutoff)]
    test_group_frame = grouped[grouped["min_time"] >= cutoff]
    train_groups = train_group_frame.index.to_numpy(dtype=np.uint64)
    test_groups = test_group_frame.index.to_numpy(dtype=np.uint64)
    train = select_indices(groups, train_groups)
    test = select_indices(groups, test_groups)

    max_train = traffic.iloc[train]["Generate Time"].max()
    min_test = traffic.iloc[test]["Generate Time"].min()
    strict = bool(max_train < min_test)
    overlap = int(np.intersect1d(train_groups, test_groups, assume_unique=True).size)
    if not strict or overlap:
        raise ValueError(f"Strict split invariant failed: strict={strict}, overlap={overlap}")

    split = {
        "group_definition": "hash(Serial, Virtual System, Session ID, Start Time); zero IDs row-unique",
        "tie_policy": "all groups whose earliest time equals the cutoff are assigned to test",
        "purge_policy": "pre-cutoff groups whose latest row reaches or crosses cutoff are excluded from training",
        "target_group_fraction": 0.8,
        "cutoff_time_restricted": str(cutoff),
        "original_min_time_ordered_split": {
            "train_rows": int(len(original_train)),
            "test_rows": int(len(original_test)),
            "max_train_time_restricted": str(traffic.iloc[original_train]["Generate Time"].max()),
            "min_test_time_restricted": str(traffic.iloc[original_test]["Generate Time"].min()),
            "strict_max_train_lt_min_test": bool(
                traffic.iloc[original_train]["Generate Time"].max()
                < traffic.iloc[original_test]["Generate Time"].min()
            ),
        },
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_groups": int(len(train_groups)),
        "test_groups": int(len(test_groups)),
        "group_overlap": overlap,
        "cutoff_tie_groups_assigned_to_test": int((grouped["min_time"] == cutoff).sum()),
        "purged_boundary_groups": int(len(purged_group_frame)),
        "purged_boundary_rows": int(purged_group_frame["rows"].sum()),
        "purged_boundary_positives": int(purged_group_frame["y"].sum()),
        "train_positives": int(target[train].sum()),
        "test_positives": int(target[test].sum()),
        "test_prevalence": float(target[test].mean()),
        "max_train_time_restricted": str(max_train),
        "min_test_time_restricted": str(min_test),
        "strict_max_train_lt_min_test": strict,
    }

    rolling: list[tuple[np.ndarray, np.ndarray, dict]] = []
    fractions = [(0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
    for fold_number, (train_fraction, end_fraction) in enumerate(fractions, start=1):
        start_time = grouped.iloc[int(train_fraction * n_groups)]["min_time"]
        end_time = None if end_fraction == 1.0 else grouped.iloc[int(end_fraction * n_groups)]["min_time"]
        fold_train_frame = grouped[(grouped["min_time"] < start_time) & (grouped["max_time"] < start_time)]
        fold_purged_frame = grouped[(grouped["min_time"] < start_time) & (grouped["max_time"] >= start_time)]
        fold_test_frame = grouped[grouped["min_time"] >= start_time]
        if end_time is not None:
            fold_test_frame = fold_test_frame[fold_test_frame["min_time"] < end_time]
        fold_train_groups = fold_train_frame.index.to_numpy(dtype=np.uint64)
        fold_test_groups = fold_test_frame.index.to_numpy(dtype=np.uint64)
        fold_train = select_indices(groups, fold_train_groups)
        fold_test = select_indices(groups, fold_test_groups)
        fold_max_train = traffic.iloc[fold_train]["Generate Time"].max()
        fold_min_test = traffic.iloc[fold_test]["Generate Time"].min()
        fold_overlap = int(np.intersect1d(fold_train_groups, fold_test_groups, assume_unique=True).size)
        fold_strict = bool(fold_max_train < fold_min_test)
        if not fold_strict or fold_overlap:
            raise ValueError(f"Rolling fold {fold_number} failed strict invariants")
        metadata = {
            "fold": fold_number,
            "start_time_restricted": str(start_time),
            "end_time_restricted": str(end_time) if end_time is not None else None,
            "train_rows": int(len(fold_train)),
            "test_rows": int(len(fold_test)),
            "train_positives": int(target[fold_train].sum()),
            "test_positives": int(target[fold_test].sum()),
            "group_overlap": fold_overlap,
            "purged_boundary_groups": int(len(fold_purged_frame)),
            "purged_boundary_rows": int(fold_purged_frame["rows"].sum()),
            "strict_max_train_lt_min_test": fold_strict,
        }
        rolling.append((fold_train, fold_test, metadata))
    split["rolling_invariants"] = [metadata for _, _, metadata in rolling]
    return groups, train, test, split, rolling


def feature_view(frame: pd.DataFrame, feature_set: str) -> pd.DataFrame:
    if feature_set == "full_core":
        return frame[CORE]
    if feature_set == "no_outcome":
        return frame[[column for column in CORE if column not in OUTCOME]]
    if feature_set == "hard_proxy":
        return frame[[column for column in CORE if column not in HARD_PROXY]]
    if feature_set == "duration_only":
        return frame[["Elapsed Time (sec)"]]
    if feature_set == "volume_only":
        return frame[VOLUME]
    if feature_set == "rate_normalized":
        duration = pd.to_numeric(frame["Elapsed Time (sec)"], errors="coerce").clip(lower=1.0)
        result = pd.DataFrame(index=frame.index)
        for column in VOLUME:
            values = pd.to_numeric(frame[column], errors="coerce")
            result[f"{column}_per_second"] = values / duration
        result["sent_byte_share"] = (
            pd.to_numeric(frame["Bytes Sent"], errors="coerce")
            / pd.to_numeric(frame["Bytes"], errors="coerce").replace(0, np.nan)
        )
        result["sent_packet_share"] = (
            pd.to_numeric(frame["Packets Sent"], errors="coerce")
            / pd.to_numeric(frame["Packets"], errors="coerce").replace(0, np.nan)
        )
        return result.replace([np.inf, -np.inf], np.nan)
    raise ValueError(feature_set)


def preprocessor(frame: pd.DataFrame, scale: bool = False) -> ColumnTransformer:
    categorical = [column for column in frame.columns if not pd.api.types.is_numeric_dtype(frame[column])]
    numeric = [column for column in frame.columns if column not in categorical]
    numeric_steps: list[tuple[str, object]] = [("imputer", SimpleImputer(strategy="median"))]
    if scale:
        numeric_steps.append(("scale", StandardScaler()))
    transformers = []
    if categorical:
        transformers.append(
            (
                "cat",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encode", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
                    ]
                ),
                categorical,
            )
        )
    if numeric:
        transformers.append(("num", Pipeline(numeric_steps), numeric))
    return ColumnTransformer(transformers, verbose_feature_names_out=False)


def estimator(name: str, seed: int):
    if name == "XGBoost":
        from xgboost import XGBClassifier

        return XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.08,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            tree_method="hist",
            random_state=seed,
            n_jobs=-1,
        )
    if name == "Extra Trees":
        return ExtraTreesClassifier(n_estimators=200, class_weight="balanced", random_state=seed, n_jobs=-1)
    if name == "LightGBM":
        from lightgbm import LGBMClassifier

        return LGBMClassifier(
            n_estimators=300,
            learning_rate=0.08,
            class_weight="balanced",
            random_state=seed,
            n_jobs=-1,
            verbosity=-1,
        )
    if name == "CatBoost":
        from catboost import CatBoostClassifier

        return CatBoostClassifier(
            iterations=300,
            depth=6,
            learning_rate=0.08,
            auto_class_weights="Balanced",
            random_seed=seed,
            verbose=False,
            allow_writing_files=False,
        )
    if name == "Logistic Regression":
        return SGDClassifier(
            loss="log_loss",
            penalty="l2",
            alpha=1e-4,
            class_weight="balanced",
            max_iter=2000,
            tol=1e-4,
            random_state=seed,
            average=True,
        )
    raise ValueError(name)


def cp_interval(successes: int, total: int, alpha: float = 0.05) -> list[float]:
    low = 0.0 if successes == 0 else float(beta.ppf(alpha / 2, successes, total - successes + 1))
    high = 1.0 if successes == total else float(beta.ppf(1 - alpha / 2, successes + 1, total - successes))
    return [low, high]


def evaluate(
    name: str,
    feature_set: str,
    predictors: pd.DataFrame,
    target: np.ndarray,
    groups: np.ndarray,
    train: np.ndarray,
    test: np.ndarray,
    seed: int,
    evaluation: str,
    return_scores: bool = False,
) -> tuple[dict, list[dict], np.ndarray | None]:
    features = feature_view(predictors, feature_set)
    start = time.perf_counter()
    if name == "CatBoost":
        # CatBoost 1.2.8 predates scikit-learn 1.8's estimator-tag contract.
        # Fit it directly on the identical fold-fitted preprocessing output so
        # that sklearn Pipeline's fitted-state tag check cannot block inference.
        transform = preprocessor(features, False)
        train_matrix = transform.fit_transform(features.iloc[train])
        test_matrix = transform.transform(features.iloc[test])
        fitted_model = estimator(name, seed)
        fitted_model.fit(train_matrix, target[train])
        fit_seconds = time.perf_counter() - start
        score = fitted_model.predict_proba(test_matrix)[:, 1]
    else:
        pipeline = Pipeline(
            [
                ("preprocess", preprocessor(features, name == "Logistic Regression")),
                ("model", estimator(name, seed)),
            ]
        )
        pipeline.fit(features.iloc[train], target[train])
        fit_seconds = time.perf_counter() - start
        score = pipeline.predict_proba(features.iloc[test])[:, 1]
    predicted = (score >= 0.5).astype(np.int8)
    observed = target[test]
    tn, fp, fn, tp = confusion_matrix(observed, predicted, labels=[0, 1]).ravel()
    cases = pd.DataFrame({"group": groups[test], "y": observed, "score": score}).groupby("group", sort=False).agg(
        y=("y", "max"), score=("score", "max")
    )
    cases = cases.sort_values("score", ascending=False, kind="mergesort")
    topk: list[dict] = []
    total_positive_cases = int(cases["y"].sum())
    for budget in (50, 100, 250, 500, 1000):
        count = min(budget, len(cases))
        hits = int(cases.iloc[:count]["y"].sum())
        topk.append(
            {
                "evaluation": evaluation,
                "model": name,
                "feature_set": feature_set,
                "seed": seed,
                "k": count,
                "true_positives": hits,
                "precision": hits / count,
                "recall": hits / total_positive_cases if total_positive_cases else 0.0,
                "precision_cp95": cp_interval(hits, count),
            }
        )
    result = {
        "evaluation": evaluation,
        "model": name,
        "feature_set": feature_set,
        "seed": seed,
        "features": int(features.shape[1]),
        "fit_seconds": fit_seconds,
        "test_rows": int(len(test)),
        "test_positives": int(observed.sum()),
        "accuracy": float(np.mean(predicted == observed)),
        "balanced_accuracy": float(balanced_accuracy_score(observed, predicted)),
        "macro_f1": float(f1_score(observed, predicted, average="macro", zero_division=0)),
        "average_precision": float(average_precision_score(observed, score)),
        "roc_auc": float(roc_auc_score(observed, score)),
        "positive_precision": float(precision_score(observed, predicted, zero_division=0)),
        "positive_recall": float(recall_score(observed, predicted, zero_division=0)),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }
    return result, topk, score if return_scores else None


def exposure_strata(predictors: pd.DataFrame, target: np.ndarray, train: np.ndarray, test: np.ndarray) -> list[dict]:
    records: list[dict] = []
    for field in ("Elapsed Time (sec)", "Bytes", "Packets"):
        train_values = np.log1p(pd.to_numeric(predictors.iloc[train][field], errors="coerce").fillna(0).clip(lower=0))
        test_values = np.log1p(pd.to_numeric(predictors.iloc[test][field], errors="coerce").fillna(0).clip(lower=0))
        edges = np.unique(np.quantile(train_values, np.linspace(0, 1, 11)))
        if len(edges) < 3:
            continue
        edges[0] = -np.inf
        edges[-1] = np.inf
        bins = np.digitize(test_values, edges[1:-1], right=False)
        for bin_number in range(len(edges) - 1):
            mask = bins == bin_number
            rows = int(mask.sum())
            positives = int(target[test][mask].sum())
            records.append(
                {
                    "field": field,
                    "train_defined_stratum": bin_number + 1,
                    "test_rows": rows,
                    "test_positives": positives,
                    "test_prevalence": positives / rows if rows else None,
                }
            )
    return records


def block_bootstrap_ap(
    target: np.ndarray,
    test: np.ndarray,
    groups: np.ndarray,
    times: pd.Series,
    no_outcome_score: np.ndarray,
    hard_proxy_score: np.ndarray,
    repetitions: int,
    block_count: int,
) -> dict:
    test_frame = pd.DataFrame(
        {
            "local_row": np.arange(len(test)),
            "group": groups[test],
            "time": times.iloc[test].to_numpy(),
        }
    )
    group_order = test_frame.groupby("group", sort=False)["time"].min().sort_values(kind="mergesort").index.to_numpy()
    group_blocks = [block for block in np.array_split(group_order, block_count) if len(block)]
    group_to_rows = test_frame.groupby("group", sort=False)["local_row"].apply(lambda values: values.to_numpy()).to_dict()
    row_blocks = [np.concatenate([group_to_rows[group] for group in block]) for block in group_blocks]
    rng = np.random.default_rng(20260717)
    no_values: list[float] = []
    hard_values: list[float] = []
    difference_values: list[float] = []
    observed = target[test]
    for _ in range(repetitions):
        sampled = rng.integers(0, len(row_blocks), size=len(row_blocks))
        rows = np.concatenate([row_blocks[index] for index in sampled])
        if np.unique(observed[rows]).size < 2:
            continue
        no_ap = float(average_precision_score(observed[rows], no_outcome_score[rows]))
        hard_ap = float(average_precision_score(observed[rows], hard_proxy_score[rows]))
        no_values.append(no_ap)
        hard_values.append(hard_ap)
        difference_values.append(no_ap - hard_ap)

    def summary(values: list[float]) -> dict:
        array = np.asarray(values, dtype=float)
        return {
            "replicates": int(len(array)),
            "median": float(np.median(array)),
            "percentile_95": [float(np.quantile(array, 0.025)), float(np.quantile(array, 0.975))],
        }

    return {
        "method": "paired nonoverlapping-block bootstrap over 20 contiguous session-group blocks on fixed seed-42 test scores",
        "scope": "evaluation-sampling uncertainty; not full training-population uncertainty",
        "requested_repetitions": repetitions,
        "temporal_blocks": int(len(row_blocks)),
        "no_outcome_ap": summary(no_values),
        "hard_proxy_ap": summary(hard_values),
        "paired_ap_difference_no_outcome_minus_hard_proxy": summary(difference_values),
    }


def main() -> None:
    args = arguments()
    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)
    traffic_path = Path(args.traffic)
    threat_path = Path(args.threat)
    derived_path = Path(args.derived)
    started_at = pd.Timestamp.now(tz="Europe/Istanbul").isoformat()
    wall = time.perf_counter()

    print("STAGE read restricted raw inputs", flush=True)
    traffic = pd.read_csv(traffic_path, usecols=TRAFFIC_COLS, low_memory=False)
    threat = pd.read_csv(threat_path, usecols=THREAT_COLS, low_memory=False)
    input_hashes = {"traffic_sha256": sha256(traffic_path), "threat_sha256": sha256(threat_path)}

    print("STAGE fail-closed corrected label", flush=True)
    target, label_audit = construct_label(traffic, threat)
    del threat
    gc.collect()

    print("STAGE provenance and restricted aligned predictor table", flush=True)
    provenance = {
        "input_provenance": input_hashes,
        "row_order_signature_sha256": row_order_signature(traffic),
        "row_order_signature_algorithm": "sha256(concatenated pandas-hash-pandas-object uint64 blocks over ordered restricted row keys, index included)",
        "derivation": "raw traffic predictors selected directly from trafik.csv; corrected target reconstructed from raw threat.csv; no legacy processed target used",
    }
    if not args.skip_derived_write:
        provenance["restricted_derived_table"] = write_restricted_derived(derived_path, traffic, target)
    else:
        provenance["restricted_derived_table"] = {"status": "skipped_by_cli"}

    print("STAGE strict tie-aware purged temporal splits", flush=True)
    groups, train, test, split, rolling = split_invariants(traffic, target)
    predictors = traffic[CORE].copy()
    times = traffic["Generate Time"].copy()
    del traffic
    gc.collect()

    results: list[dict] = []
    topk: list[dict] = []
    primary_scores: dict[str, np.ndarray] = {}
    primary = [
        ("XGBoost", "full_core"),
        ("XGBoost", "no_outcome"),
        ("XGBoost", "hard_proxy"),
        ("Extra Trees", "no_outcome"),
        ("LightGBM", "no_outcome"),
        ("CatBoost", "no_outcome"),
        ("Logistic Regression", "no_outcome"),
        ("XGBoost", "duration_only"),
        ("XGBoost", "volume_only"),
        ("XGBoost", "rate_normalized"),
    ]
    for name, feature_set in primary:
        print(f"RUN primary {name} / {feature_set}", flush=True)
        keep_scores = name == "XGBoost" and feature_set in {"no_outcome", "hard_proxy"}
        result, budget, scores = evaluate(
            name, feature_set, predictors, target, groups, train, test, 42, "primary_later_20pct", keep_scores
        )
        results.append(result)
        topk.extend(budget)
        if scores is not None:
            primary_scores[feature_set] = scores

    for seed in SEEDS:
        if seed == 42:
            continue
        for feature_set in ("no_outcome", "hard_proxy"):
            print(f"RUN seed {seed} / {feature_set}", flush=True)
            result, budget, _ = evaluate(
                "XGBoost", feature_set, predictors, target, groups, train, test, seed, "primary_later_20pct"
            )
            results.append(result)
            topk.extend(budget)

    for fold_train, fold_test, metadata in rolling:
        fold_number = metadata["fold"]
        print(f"RUN strict rolling-origin fold {fold_number}", flush=True)
        result, budget, _ = evaluate(
            "XGBoost",
            "no_outcome",
            predictors,
            target,
            groups,
            fold_train,
            fold_test,
            42,
            f"rolling_origin_fold_{fold_number}",
        )
        results.append(result)
        topk.extend(budget)

    print("STAGE exposure strata and paired block bootstrap", flush=True)
    strata = exposure_strata(predictors, target, train, test)
    uncertainty = block_bootstrap_ap(
        target,
        test,
        groups,
        times,
        primary_scores["no_outcome"],
        primary_scores["hard_proxy"],
        args.bootstrap_reps,
        args.bootstrap_blocks,
    )
    dns = predictors.iloc[test]["Application"].astype(str).eq("dns-base").to_numpy()
    dns_ap = float(average_precision_score(target[test], dns.astype(float)))

    result_frame = pd.DataFrame(results)
    seed_pairs = result_frame[
        (result_frame["evaluation"] == "primary_later_20pct")
        & (result_frame["model"] == "XGBoost")
        & (result_frame["feature_set"].isin(["no_outcome", "hard_proxy"]))
    ].pivot(index="seed", columns="feature_set", values="average_precision")
    seed_pairs["difference_no_outcome_minus_hard_proxy"] = seed_pairs["no_outcome"] - seed_pairs["hard_proxy"]

    payload = {
        "status": "COMPLETE_STRICT_TEMPORAL_EXPOSURE_UNCERTAINTY",
        "created_at": pd.Timestamp.now(tz="Europe/Istanbul").isoformat(),
        "started_at": started_at,
        "runtime_seconds": time.perf_counter() - wall,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "host": platform.node(),
            "logical_cpu": os.cpu_count(),
            "packages": package_versions(),
        },
        "provenance": provenance,
        "label_audit": label_audit,
        "split": split,
        "random_ranking_average_precision": split["test_prevalence"],
        "dns_rule_average_precision": dns_ap,
        "results": results,
        "topk": topk,
        "exposure_strata": strata,
        "uncertainty": uncertainty,
        "seed_paired_configuration_ap": seed_pairs.reset_index().to_dict(orient="records"),
        "limitations": [
            "One organization, one firewall, and one approximately 47-minute traffic window.",
            "The target is retrospective same-session threat-log linkage, not future maliciousness prediction.",
            "The nonoverlapping-block bootstrap conditions on fixed seed-42 scores and does not represent full population or refit uncertainty.",
            "Exposure-only and rate-normalized models diagnose observation-opportunity dependence; they do not identify a causal mechanism.",
        ],
    }
    (out / "corrected_linkage_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    result_frame.to_csv(out / "corrected_linkage_metrics.csv", index=False)
    topk_frame = pd.DataFrame(topk)
    topk_frame["precision_cp95"] = topk_frame["precision_cp95"].map(json.dumps)
    topk_frame.to_csv(out / "corrected_linkage_topk.csv", index=False)
    pd.DataFrame(strata).to_csv(out / "exposure_strata.csv", index=False)
    seed_pairs.reset_index().to_csv(out / "paired_seed_configuration_ap.csv", index=False)
    (out / "uncertainty_summary.json").write_text(json.dumps(uncertainty, indent=2), encoding="utf-8")

    primary_rows = result_frame[
        (result_frame["evaluation"] == "primary_later_20pct") & (result_frame["seed"] == 42)
    ][
        ["model", "feature_set", "macro_f1", "average_precision", "roc_auc", "positive_precision", "positive_recall", "tp", "fp"]
    ]
    lines = [
        "# Strict-Temporal Corrected-Linkage Results",
        "",
        f"- Corrected positives: {label_audit['corrected_positive_rows']:,} / {label_audit['traffic_rows']:,} ({100 * label_audit['corrected_prevalence']:.4f}%).",
        f"- Fail-closed direct/NAT-aware tuple support: {label_audit['exact_direct_tuple_rows_fail_closed']:,} / {label_audit['nat_aware_tuple_rows_fail_closed']:,}.",
        f"- Original min-time-only primary split strict temporal invariant: {split['original_min_time_ordered_split']['strict_max_train_lt_min_test']}.",
        f"- Revised split: {split['train_rows']:,} train rows, {split['test_rows']:,} test rows, {split['purged_boundary_groups']} purged boundary groups, strict max(train)<min(test)={split['strict_max_train_lt_min_test']}.",
        f"- Random-ranking AP: {payload['random_ranking_average_precision']:.6f}; DNS-rule AP: {dns_ap:.6f}.",
        "",
        "## Seed-42 primary results",
        "",
        primary_rows.to_markdown(index=False, floatfmt=".6f"),
        "",
        "## Paired block-bootstrap evaluation uncertainty",
        "",
        f"- No-outcome AP 95% interval: {uncertainty['no_outcome_ap']['percentile_95'][0]:.4f} to {uncertainty['no_outcome_ap']['percentile_95'][1]:.4f}.",
        f"- Hard-proxy AP 95% interval: {uncertainty['hard_proxy_ap']['percentile_95'][0]:.4f} to {uncertainty['hard_proxy_ap']['percentile_95'][1]:.4f}.",
        f"- Paired AP difference 95% interval: {uncertainty['paired_ap_difference_no_outcome_minus_hard_proxy']['percentile_95'][0]:.4f} to {uncertainty['paired_ap_difference_no_outcome_minus_hard_proxy']['percentile_95'][1]:.4f}.",
        "",
        "## Interpretation boundary",
        "",
        "The strict purge repairs the chronological boundary but does not create external validation. Exposure-only, rate-normalized, seed-paired, and block-bootstrap results diagnose dependence and uncertainty inside this single observed export; they do not support causal, deployment, or cross-organization claims.",
    ]
    (out / "corrected_linkage_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "runtime_seconds": payload["runtime_seconds"],
                "label": label_audit,
                "split": split,
                "uncertainty": uncertainty,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
