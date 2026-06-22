from __future__ import annotations

import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

from xgboost import XGBClassifier


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "processed" / "traffic_has_linked_threat.csv"
DATA_ZIP_PATH = ROOT / "data" / "processed" / "traffic_has_linked_threat.csv.zip"
OUTDIR = ROOT / "results"
OUTDIR.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
TARGET = "has_linked_threat"
TIME_COL = "Receive Time"
TIME_OFFSET_COL = "receive_time_offset_sec"
POSITIVE_LABEL = 1

EXCLUDE_ALWAYS = {
    TARGET,
    "target",
    "raw_action",
    "raw_traffic_subtype",
    "raw_session_end_reason",
    "Receive Time",
    "Generate Time",
    "High Res Timestamp",
    "receive_time_offset_sec",
    "generate_time_offset_sec",
    "high_res_timestamp_offset_sec",
    "Type",
    "Session ID",
    "session_key",
    "Rule",
    "Action Source",
}

NO_OUTCOME = {"Action", "Threat/Content Type", "Session End Reason"}


def make_estimator() -> XGBClassifier:
    return XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.08,
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="logloss",
        tree_method="hist",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )


def build_features(df: pd.DataFrame, exclude_extra: set[str] | None = None) -> tuple[pd.DataFrame, pd.Series]:
    exclude = set(EXCLUDE_ALWAYS)
    if exclude_extra:
        exclude |= exclude_extra
    feature_cols = [col for col in df.columns if col not in exclude]
    X = df[feature_cols].copy()
    y = df[TARGET].astype(int)
    return X, y


def preprocess_for(X: pd.DataFrame) -> ColumnTransformer:
    categorical = [col for col in X.columns if not pd.api.types.is_numeric_dtype(X[col])]
    numeric = [col for col in X.columns if col not in categorical]
    return ColumnTransformer(
        transformers=[
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)),
                    ]
                ),
                categorical,
            ),
            ("num", Pipeline(steps=[("imputer", SimpleImputer(strategy="median"))]), numeric),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )


def make_pipeline(X: pd.DataFrame) -> Pipeline:
    return Pipeline(steps=[("preprocess", preprocess_for(X)), ("model", make_estimator())])


def read_dataset() -> pd.DataFrame:
    if DATA_PATH.exists():
        return pd.read_csv(DATA_PATH, low_memory=False)
    if DATA_ZIP_PATH.exists():
        return pd.read_csv(DATA_ZIP_PATH, low_memory=False, compression="zip")
    raise FileNotFoundError(f"Could not find {DATA_PATH} or {DATA_ZIP_PATH}")


def threshold_metrics(y_true: np.ndarray, score: np.ndarray) -> dict[str, float]:
    precision, recall, thresholds = precision_recall_curve(y_true, score)
    f1 = np.divide(
        2 * precision * recall,
        precision + recall,
        out=np.zeros_like(precision),
        where=(precision + recall) > 0,
    )
    valid = np.arange(len(thresholds))
    best_idx = int(valid[np.argmax(f1[:-1])])
    default_pred = (score >= 0.5).astype(int)
    return {
        "best_f1_threshold": float(thresholds[best_idx]),
        "best_f1_precision": float(precision[best_idx]),
        "best_f1_recall": float(recall[best_idx]),
        "best_f1": float(f1[best_idx]),
        "default_precision": float(precision_score(y_true, default_pred, zero_division=0)),
        "default_recall": float(recall_score(y_true, default_pred, zero_division=0)),
        "default_f1": float(f1_score(y_true, default_pred, zero_division=0)),
    }


def top_budget_table(y_true: np.ndarray, score: np.ndarray, scenario: str) -> list[dict[str, float | int | str]]:
    n = len(y_true)
    positives = int(np.sum(y_true == POSITIVE_LABEL))
    prevalence = positives / n
    budget_specs: list[tuple[str, int]] = [
        ("top_100", 100),
        ("top_250", 250),
        ("top_500", 500),
        ("top_1000", 1000),
        ("top_0.1pct", max(1, round(n * 0.001))),
        ("top_0.5pct", max(1, round(n * 0.005))),
        ("top_1pct", max(1, round(n * 0.01))),
        ("top_2pct", max(1, round(n * 0.02))),
    ]
    order = np.argsort(-score, kind="mergesort")
    rows: list[dict[str, float | int | str]] = []
    for label, k in budget_specs:
        k = min(k, n)
        selected = order[:k]
        tp = int(np.sum(y_true[selected] == POSITIVE_LABEL))
        fp = int(k - tp)
        precision = tp / k if k else 0.0
        recall = tp / positives if positives else 0.0
        rows.append(
            {
                "scenario": scenario,
                "budget": label,
                "reviewed_sessions": int(k),
                "review_share": k / n,
                "true_positives": tp,
                "false_positives": fp,
                "precision": precision,
                "recall": recall,
                "lift_over_prevalence": precision / prevalence if prevalence else 0.0,
            }
        )
    return rows


def fit_score_holdout(
    df: pd.DataFrame,
    scenario: str,
    exclude_extra: set[str] | None = None,
    temporal: bool = False,
) -> tuple[dict, list[dict], pd.DataFrame | None]:
    X, y = build_features(df, exclude_extra=exclude_extra)
    if temporal:
        if TIME_OFFSET_COL in df.columns:
            time_values = pd.to_numeric(df[TIME_OFFSET_COL], errors="coerce")
            order = np.argsort(time_values.fillna(time_values.min()).to_numpy(), kind="mergesort")
        else:
            time_values = pd.to_datetime(df[TIME_COL], errors="coerce")
            order = np.argsort(time_values.fillna(time_values.min()).to_numpy(), kind="mergesort")
        split = int(len(order) * 0.8)
        train_idx = order[:split]
        test_idx = order[split:]
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=RANDOM_STATE,
            stratify=y,
        )

    pipe = make_pipeline(X)
    start = time.perf_counter()
    pipe.fit(X_train, y_train)
    fit_seconds = time.perf_counter() - start
    score = pipe.predict_proba(X_test)[:, 1]
    pred = (score >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred, labels=[0, 1]).ravel()
    summary = {
        "scenario": scenario,
        "temporal": temporal,
        "fit_seconds": fit_seconds,
        "rows": int(len(X)),
        "features": int(X.shape[1]),
        "train_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "train_positives": int(np.sum(y_train == POSITIVE_LABEL)),
        "test_positives": int(np.sum(y_test == POSITIVE_LABEL)),
        "test_prevalence": float(np.mean(y_test == POSITIVE_LABEL)),
        "accuracy": float(accuracy_score(y_test, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_test, pred)),
        "macro_f1": float(f1_score(y_test, pred, average="macro", zero_division=0)),
        "average_precision": float(average_precision_score(y_test, score)),
        "roc_auc": float(roc_auc_score(y_test, score)),
        "positive_precision": float(precision_score(y_test, pred, zero_division=0)),
        "positive_recall": float(recall_score(y_test, pred, zero_division=0)),
        "positive_f1": float(f1_score(y_test, pred, zero_division=0)),
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
        **threshold_metrics(y_test.to_numpy(), score),
    }
    budgets = top_budget_table(y_test.to_numpy(), score, scenario)

    importance = None
    if "no_outcome" in scenario and not temporal:
        feature_names = pipe.named_steps["preprocess"].get_feature_names_out()
        importances = pipe.named_steps["model"].feature_importances_
        importance = pd.DataFrame({"feature": feature_names, "importance": importances})
        importance = importance.sort_values("importance", ascending=False).reset_index(drop=True)
    return summary, budgets, importance


def write_markdown(summaries: list[dict], budgets: pd.DataFrame, importance: pd.DataFrame) -> None:
    def frame_to_markdown(frame: pd.DataFrame, floatfmt: str = ".4f") -> str:
        formatted = frame.copy()
        for col in formatted.columns:
            if pd.api.types.is_float_dtype(formatted[col]):
                formatted[col] = formatted[col].map(lambda x: format(float(x), floatfmt) if pd.notna(x) else "")
            else:
                formatted[col] = formatted[col].map(lambda x: "" if pd.isna(x) else str(x))
        widths = {
            col: max(len(str(col)), *(len(str(value)) for value in formatted[col].tolist()))
            for col in formatted.columns
        }
        header = "| " + " | ".join(str(col).ljust(widths[col]) for col in formatted.columns) + " |"
        sep = "| " + " | ".join("-" * widths[col] for col in formatted.columns) + " |"
        rows = [
            "| " + " | ".join(str(row[col]).ljust(widths[col]) for col in formatted.columns) + " |"
            for _, row in formatted.iterrows()
        ]
        return "\n".join([header, sep, *rows])

    summary_df = pd.DataFrame(summaries)
    out = []
    out.append("# Q1 Operating-Point and Validity Analyses\n")
    out.append("These analyses extend the closed VPS benchmark with reviewer-facing operating-point, temporal, and interpretability diagnostics. They use the same feature-exclusion policy as the manuscript: direct session identifiers, raw time fields, log type, and high-leakage policy fields are excluded from predictors.\n")
    out.append("## Scenario Summary\n")
    keep = [
        "scenario",
        "test_rows",
        "test_positives",
        "test_prevalence",
        "macro_f1",
        "average_precision",
        "roc_auc",
        "positive_precision",
        "positive_recall",
        "best_f1_threshold",
        "best_f1",
        "best_f1_precision",
        "best_f1_recall",
    ]
    out.append(frame_to_markdown(summary_df[keep]))
    out.append("\n\n## Analyst-Budget View\n")
    budget_keep = [
        "scenario",
        "budget",
        "reviewed_sessions",
        "true_positives",
        "false_positives",
        "precision",
        "recall",
        "lift_over_prevalence",
    ]
    selected = budgets[budgets["budget"].isin(["top_100", "top_500", "top_1000", "top_0.5pct", "top_1pct"])]
    out.append(frame_to_markdown(selected[budget_keep]))
    out.append("\n\n## No-Outcome XGBoost Feature Importance\n")
    out.append(frame_to_markdown(importance.head(12)))
    out.append("\n")
    (OUTDIR / "q1_analysis_summary.md").write_text("\n".join(out), encoding="utf-8")


def main() -> None:
    start = time.perf_counter()
    df = read_dataset()
    summaries: list[dict] = []
    budget_rows: list[dict] = []
    importance_frames: list[pd.DataFrame] = []

    for scenario, exclude_extra, temporal in [
        ("xgboost_full_stratified", set(), False),
        ("xgboost_no_outcome_stratified", NO_OUTCOME, False),
        ("xgboost_full_temporal_holdout", set(), True),
    ]:
        print(f"Running {scenario}...")
        summary, budgets, importance = fit_score_holdout(df, scenario, exclude_extra=exclude_extra, temporal=temporal)
        summaries.append(summary)
        budget_rows.extend(budgets)
        if importance is not None:
            importance_frames.append(importance)

    summary_df = pd.DataFrame(summaries)
    budget_df = pd.DataFrame(budget_rows)
    importance_df = importance_frames[0] if importance_frames else pd.DataFrame()

    summary_df.to_csv(OUTDIR / "q1_threshold_summary.csv", index=False)
    budget_df.to_csv(OUTDIR / "q1_operating_points.csv", index=False)
    importance_df.to_csv(OUTDIR / "q1_feature_importance_no_outcome_xgboost.csv", index=False)
    payload = {
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "wall_seconds": time.perf_counter() - start,
        },
        "summaries": summaries,
        "budget_rows": budget_rows,
        "top_no_outcome_importance": importance_df.head(25).to_dict(orient="records"),
    }
    (OUTDIR / "q1_analysis_payload.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(summaries, budget_df, importance_df)
    print(summary_df[["scenario", "macro_f1", "average_precision", "roc_auc", "positive_precision", "positive_recall"]])
    print(f"Wrote {OUTDIR}")


if __name__ == "__main__":
    main()
