from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

import q1_operating_point_analysis as q1


ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "results"
OUTDIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = q1.RANDOM_STATE
POSITIVE_LABEL = q1.POSITIVE_LABEL

POLICY_ACTION_EVIDENCE = ["Action", "Threat/Content Type", "Session End Reason"]
TRAFFIC_VOLUME_EVIDENCE = [
    "Bytes",
    "Bytes Sent",
    "Bytes Received",
    "Packets",
    "Packets Sent",
    "Packets Received",
    "Elapsed Time (sec)",
]
TRAFFIC_CONTEXT_EVIDENCE = [
    "Application",
    "Source Zone",
    "Destination Zone",
    "Inbound Interface",
    "Outbound Interface",
    "IP Protocol",
    "Source Port",
    "Destination Port",
    "Source Country",
    "Destination Country",
    "Category",
    "Subcategory of app",
    "Category of app",
    "Technology of app",
    "Risk of app",
    "SaaS of app",
    "AI Traffic",
]

EVIDENCE_FAMILIES = {
    "traffic_context_only": TRAFFIC_CONTEXT_EVIDENCE,
    "volume_only": TRAFFIC_VOLUME_EVIDENCE,
    "policy_action_only": POLICY_ACTION_EVIDENCE,
    "context_plus_volume": TRAFFIC_CONTEXT_EVIDENCE + TRAFFIC_VOLUME_EVIDENCE,
    "context_plus_policy_action": TRAFFIC_CONTEXT_EVIDENCE + POLICY_ACTION_EVIDENCE,
    "full_core": TRAFFIC_CONTEXT_EVIDENCE + TRAFFIC_VOLUME_EVIDENCE + POLICY_ACTION_EVIDENCE,
}

DEFAULT_TOPK = [10, 25, 50, 100, 250, 500, 1000]


def make_estimator(device: str) -> XGBClassifier:
    params = {
        "n_estimators": 300,
        "max_depth": 6,
        "learning_rate": 0.08,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "eval_metric": "logloss",
        "tree_method": "hist",
        "random_state": RANDOM_STATE,
        "n_jobs": -1,
    }
    if device != "cpu":
        params["device"] = device
    return XGBClassifier(**params)


def make_pipeline(X: pd.DataFrame, device: str) -> Pipeline:
    return Pipeline(steps=[("preprocess", q1.preprocess_for(X)), ("model", make_estimator(device))])


def available_columns(df: pd.DataFrame, cols: list[str]) -> list[str]:
    return [col for col in cols if col in df.columns]


def build_family_features(df: pd.DataFrame, family: str) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    cols = available_columns(df, EVIDENCE_FAMILIES[family])
    if not cols:
        raise ValueError(f"No available columns for evidence family {family}")
    return df[cols].copy(), df[q1.TARGET].astype(int), cols


def expected_calibration_error(y_true: np.ndarray, score: np.ndarray, n_bins: int = 10) -> tuple[float, pd.DataFrame]:
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_ids = np.digitize(score, bins[1:-1], right=True)
    total = len(score)
    rows = []
    ece = 0.0
    for idx in range(n_bins):
        mask = bin_ids == idx
        count = int(mask.sum())
        if count == 0:
            rows.append(
                {
                    "bin": idx + 1,
                    "lower": bins[idx],
                    "upper": bins[idx + 1],
                    "count": 0,
                    "mean_score": np.nan,
                    "observed_rate": np.nan,
                    "abs_gap": np.nan,
                }
            )
            continue
        mean_score = float(np.mean(score[mask]))
        observed_rate = float(np.mean(y_true[mask] == POSITIVE_LABEL))
        gap = abs(mean_score - observed_rate)
        ece += (count / total) * gap
        rows.append(
            {
                "bin": idx + 1,
                "lower": bins[idx],
                "upper": bins[idx + 1],
                "count": count,
                "mean_score": mean_score,
                "observed_rate": observed_rate,
                "abs_gap": gap,
            }
        )
    return float(ece), pd.DataFrame(rows)


def topk_metrics(y_true: np.ndarray, score: np.ndarray, budgets: list[int]) -> list[dict]:
    positives = int(np.sum(y_true == POSITIVE_LABEL))
    prevalence = positives / len(y_true)
    order = np.argsort(-score, kind="mergesort")
    rows = []
    for k in budgets:
        k = min(k, len(y_true))
        selected = order[:k]
        tp = int(np.sum(y_true[selected] == POSITIVE_LABEL))
        precision = tp / k if k else 0.0
        recall = tp / positives if positives else 0.0
        rows.append(
            {
                "k": k,
                "true_positives": tp,
                "false_positives": int(k - tp),
                "precision": precision,
                "recall": recall,
                "lift_over_prevalence": precision / prevalence if prevalence else 0.0,
            }
        )
    return rows


def evaluate_family(
    df: pd.DataFrame,
    family: str,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    device: str,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    X, y, cols = build_family_features(df, family)
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    pipe = make_pipeline(X, device)
    fit_start = time.perf_counter()
    used_device = device
    try:
        pipe.fit(X_train, y_train)
    except Exception:
        if device == "cpu":
            raise
        used_device = "cpu_fallback"
        pipe = make_pipeline(X, "cpu")
        pipe.fit(X_train, y_train)
    fit_seconds = time.perf_counter() - fit_start

    predict_start = time.perf_counter()
    score = pipe.predict_proba(X_test)[:, 1]
    pred = (score >= 0.5).astype(int)
    predict_seconds = time.perf_counter() - predict_start
    y_np = y_test.to_numpy(dtype=int)
    ece, calibration = expected_calibration_error(y_np, score)

    top_rows = pd.DataFrame(topk_metrics(y_np, score, DEFAULT_TOPK))
    top_rows.insert(0, "evidence_family", family)
    calibration.insert(0, "evidence_family", family)
    summary = {
        "evidence_family": family,
        "features": len(cols),
        "feature_columns": "; ".join(cols),
        "train_rows": int(len(train_idx)),
        "test_rows": int(len(test_idx)),
        "train_positives": int(np.sum(y.iloc[train_idx] == POSITIVE_LABEL)),
        "test_positives": int(np.sum(y_np == POSITIVE_LABEL)),
        "test_prevalence": float(np.mean(y_np == POSITIVE_LABEL)),
        "accuracy": float(accuracy_score(y_np, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_np, pred)),
        "macro_f1": float(f1_score(y_np, pred, average="macro", zero_division=0)),
        "average_precision": float(average_precision_score(y_np, score)),
        "roc_auc": float(roc_auc_score(y_np, score)),
        "positive_precision": float(precision_score(y_np, pred, zero_division=0)),
        "positive_recall": float(recall_score(y_np, pred, zero_division=0)),
        "brier_score": float(brier_score_loss(y_np, score)),
        "ece_10bin": ece,
        "top_100_precision": float(top_rows.loc[top_rows["k"] == 100, "precision"].iloc[0]),
        "top_100_recall": float(top_rows.loc[top_rows["k"] == 100, "recall"].iloc[0]),
        "top_500_precision": float(top_rows.loc[top_rows["k"] == 500, "precision"].iloc[0]),
        "fit_seconds": fit_seconds,
        "predict_seconds": predict_seconds,
        "fit_predict_seconds": fit_seconds + predict_seconds,
        "predict_ms_per_1000_rows": (predict_seconds / len(y_np)) * 1000 * 1000,
        "device_used": used_device,
    }
    return summary, top_rows, calibration


def to_markdown_table(frame: pd.DataFrame, floatfmt: str = ".4f") -> str:
    if frame.empty:
        return ""
    formatted = frame.copy()
    for col in formatted.columns:
        if pd.api.types.is_float_dtype(formatted[col]):
            formatted[col] = formatted[col].map(lambda x: "" if pd.isna(x) else format(float(x), floatfmt))
        else:
            formatted[col] = formatted[col].map(lambda x: "" if pd.isna(x) else str(x))
    widths = {col: max(len(str(col)), *(len(str(v)) for v in formatted[col].tolist())) for col in formatted.columns}
    header = "| " + " | ".join(str(col).ljust(widths[col]) for col in formatted.columns) + " |"
    sep = "| " + " | ".join("-" * widths[col] for col in formatted.columns) + " |"
    rows = [
        "| " + " | ".join(str(row[col]).ljust(widths[col]) for col in formatted.columns) + " |"
        for _, row in formatted.iterrows()
    ]
    return "\n".join([header, sep, *rows])


def write_summary(summary: pd.DataFrame, topk: pd.DataFrame, runtime: list[dict]) -> None:
    out = []
    out.append("# Evidence-Family and Calibration Analysis\n")
    out.append(
        "This analysis decomposes the linked-event prediction task by operational evidence families. "
        "All rows use the same stratified 80/20 split and the same XGBoost configuration as the main manuscript.\n"
    )
    keep = [
        "evidence_family",
        "features",
        "macro_f1",
        "balanced_accuracy",
        "average_precision",
        "roc_auc",
        "positive_precision",
        "positive_recall",
        "brier_score",
        "ece_10bin",
        "top_100_precision",
        "top_500_precision",
        "fit_predict_seconds",
        "device_used",
    ]
    out.append("## Evidence-Family Summary\n")
    out.append(to_markdown_table(summary[keep]))
    out.append("\n\n## Top-k Operating Points\n")
    out.append(to_markdown_table(topk[topk["k"].isin([10, 50, 100, 250, 500, 1000])]))
    out.append("\n\n## Runtime Profile\n")
    out.append(to_markdown_table(pd.DataFrame(runtime)))
    out.append("\n")
    (OUTDIR / "evidence_uncertainty_summary.md").write_text("\n".join(out), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--sample-rows", type=int, default=None)
    parser.add_argument("--families", nargs="+", choices=sorted(EVIDENCE_FAMILIES), default=list(EVIDENCE_FAMILIES))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_start = time.perf_counter()
    load_start = time.perf_counter()
    df = q1.read_dataset()
    if args.sample_rows and args.sample_rows < len(df):
        df = df.sample(n=args.sample_rows, random_state=RANDOM_STATE).reset_index(drop=True)
    load_seconds = time.perf_counter() - load_start

    y = df[q1.TARGET].astype(int)
    idx = np.arange(len(df))
    train_idx, test_idx = train_test_split(idx, test_size=0.2, random_state=RANDOM_STATE, stratify=y)
    train_idx = np.asarray(train_idx)
    test_idx = np.asarray(test_idx)

    summaries = []
    top_frames = []
    calibration_frames = []
    runtime_rows = [
        {
            "stage": "data_load",
            "evidence_family": "all",
            "seconds": load_seconds,
            "rows": int(len(df)),
            "test_rows": "",
            "device_requested": args.device,
            "device_used": "",
        }
    ]
    for family in args.families:
        print(f"Running {family}...")
        family_start = time.perf_counter()
        summary, top_rows, calibration = evaluate_family(df, family, train_idx, test_idx, args.device)
        summaries.append(summary)
        top_frames.append(top_rows)
        calibration_frames.append(calibration)
        runtime_rows.append(
            {
                "stage": "fit_predict_calibration",
                "evidence_family": family,
                "seconds": time.perf_counter() - family_start,
                "rows": int(len(df)),
                "test_rows": int(len(test_idx)),
                "device_requested": args.device,
                "device_used": summary["device_used"],
            }
        )

    total_seconds = time.perf_counter() - run_start
    runtime_rows.append(
        {
            "stage": "total_python_runtime",
            "evidence_family": "all",
            "seconds": total_seconds,
            "rows": int(len(df)),
            "test_rows": int(len(test_idx)),
            "device_requested": args.device,
            "device_used": "",
        }
    )

    summary_df = pd.DataFrame(summaries)
    topk_df = pd.concat(top_frames, ignore_index=True)
    calibration_df = pd.concat(calibration_frames, ignore_index=True)
    runtime_df = pd.DataFrame(runtime_rows)

    summary_df.to_csv(OUTDIR / "evidence_family_metrics.csv", index=False)
    topk_df.to_csv(OUTDIR / "evidence_family_topk.csv", index=False)
    calibration_df.to_csv(OUTDIR / "calibration_bins.csv", index=False)
    runtime_df.to_csv(OUTDIR / "runtime_profile.csv", index=False)
    payload = {
        "runtime": {
            "note": "Evidence-family and calibration diagnostic run; platform, machine, and timing details are omitted from the public artifact because these checks are not used as timing evidence.",
            "device_requested": args.device,
            "sample_rows": args.sample_rows,
        },
        "evidence_families": EVIDENCE_FAMILIES,
        "summaries": summaries,
    }
    (OUTDIR / "evidence_uncertainty_payload.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_summary(summary_df, topk_df, runtime_rows)
    print(summary_df[["evidence_family", "macro_f1", "average_precision", "top_100_precision", "brier_score", "ece_10bin"]])
    print(f"Wrote {OUTDIR}")


if __name__ == "__main__":
    main()
