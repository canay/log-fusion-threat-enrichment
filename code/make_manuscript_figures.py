"""Regenerate the manuscript result figures in the shared Q1 style.

Single neutral sans, constrained navy-to-light-blue ramp with one orange accent,
thin horizontal grid, no top/right spines. Redesigned 2026-06-07 to remove the
amateur look of the earlier set: the two-bar imbalance panel became a single
log-scale linkage funnel, the four-bar single-series sample-CV chart was dropped
(Table 6 carries those numbers), the lollipop benchmark became a clean grouped
bar, and the gradient-coloured importance bars became one colour.
"""
from __future__ import annotations
from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np
import pandas as pd

from fig_style import set_style, save, hgrid, vgrid, INK, C1, C2, C3, NEUTRAL, ACCENT, GRID

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "github-log-fusion-threat-enrichment" / "results"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTDIR = PROJECT_ROOT / "COMNET" / "manuscript-r0"


def wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


# ----------------------------------------------------------------------------- workflow
def make_workflow() -> None:
    fig, ax = plt.subplots(figsize=(7.16, 1.95))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    y, h, w, gap = 0.34, 0.50, 0.176, 0.030
    xs = [0.005 + i * (w + gap) for i in range(5)]
    steps = [
        ("1", "Paired firewall exports", ["1,048,576 traffic rows", "186,271 threat rows", "93 shared fields"]),
        ("2", "Session linkage audit", ["86.8% session coverage", "1,233 strict tuples"]),
        ("3", "Linked-threat label", ["19,311 positives", "1.84% prevalence", "evidence, not malice"]),
        ("4", "Leakage-aware learning", ["no IDs, IPs, raw time", "27 traffic features", "ablation + PU bounds"]),
        ("5", "Operational reading", ["full-prevalence metrics", "top-k analyst budgets", "triage use"]),
    ]
    head_h = 0.115
    for x, (num, title, lines) in zip(xs, steps):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.018",
                                    facecolor="white", edgecolor=INK, linewidth=0.9, zorder=2))
        ax.add_patch(FancyBboxPatch((x, y + h - head_h), w, head_h, boxstyle="square,pad=0",
                                    facecolor=C1, edgecolor="none", zorder=3))
        ax.text(x + 0.012, y + h - head_h / 2, f"STEP {num}", ha="left", va="center",
                color="white", fontweight="bold", fontsize=7.0, zorder=4)
        ax.text(x + w / 2, y + h - head_h - 0.085, wrap(title, 17), ha="center", va="center",
                color=INK, fontweight="bold", fontsize=7.2, zorder=4)
        ax.text(x + w / 2, y + 0.135, "\n".join(lines), ha="center", va="center",
                color="#43505a", fontsize=6.2, linespacing=1.45, zorder=4)
    for i in range(4):
        ax.add_patch(FancyArrowPatch((xs[i] + w, y + h / 2), (xs[i + 1], y + h / 2),
                     arrowstyle="-|>", mutation_scale=10, linewidth=1.0, color=NEUTRAL, zorder=1))
    ax.text(0.5, 0.075, "Primary target: a nonzero traffic session linked to threat-log evidence; "
            "strict tuple overlap is a linkage-sensitivity diagnostic.",
            ha="center", va="center", color="#43505a", fontsize=7.0)
    save(fig, OUTDIR, "fig_methodology_workflow")


# ----------------------------------------------------------------------------- linkage funnel
def make_linkage_imbalance() -> None:
    meta = pd.read_json(RESULTS / "linked_threat_dataset_metadata.json", typ="series")
    audit = {}
    for line in (RESULTS / "traffic_threat_linkage_audit.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("- ") and ":" in line:
            k, v = line[2:].split(":", 1)
            try: audit[k] = float(v.strip().replace(",", ""))
            except ValueError: pass

    total = int(meta["negative_rows"]) + int(meta["positive_rows"])
    stages = [
        ("All traffic sessions", total, "100%", C3),
        ("Linked to threat evidence", int(meta["positive_rows"]), "1.84%", C1),
        ("Threat sessions seen in traffic", int(audit["Threat nonzero session identifiers observed in traffic"]), "86.8% of threat", C2),
        ("Strict session+tuple overlap", int(audit["Traffic rows with nonzero session tuple overlap"]), "6.38% of linked", ACCENT),
    ]
    fig, ax = plt.subplots(figsize=(5.0, 2.35))
    yps = np.arange(len(stages))[::-1]
    for yp, (label, val, note, color) in zip(yps, stages):
        ax.barh(yp, val, color=color, edgecolor=INK, linewidth=0.7, height=0.62, zorder=3)
        ax.text(val * 1.6, yp, f"{val:,}", va="center", ha="left", fontsize=8.0, color=INK)
        ax.text(val * 1.6, yp - 0.30, note, va="center", ha="left", fontsize=6.6, color="#5d6972")
    ax.set_yticks(yps)
    ax.set_yticklabels([s[0] for s in stages], fontsize=7.8)
    ax.set_xscale("log")
    ax.set_xlim(700, 4e6)
    ax.set_xlabel("Session count (log scale)")
    vgrid(ax)
    save(fig, OUTDIR, "fig_linkage_imbalance")


def read_metrics(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / name)


# ----------------------------------------------------------------------------- benchmark (grouped bar)
def make_full_benchmark() -> None:
    df = read_metrics("baseline_benchmark_linked_full_core_full_baseline.csv")
    df = df.set_index("model").loc[["XGBoost", "Extra Trees", "LightGBM", "CatBoost"]].reset_index()
    metrics = [("f1_macro", "Macro-F1", C1), ("balanced_accuracy", "Balanced acc.", C2),
               ("roc_auc", "ROC-AUC", C3), ("average_precision", "Avg. precision", ACCENT)]
    x = np.arange(len(df)); width = 0.20
    fig, ax = plt.subplots(figsize=(3.5, 2.7))
    for i, (col, label, color) in enumerate(metrics):
        ax.bar(x + (i - 1.5) * width, df[col], width=width, label=label,
               color=color, edgecolor=INK, linewidth=0.6, zorder=3)
    ax.set_xticks(x); ax.set_xticklabels(df["model"])
    ax.set_ylim(0, 0.75); ax.set_ylabel("Score")
    hgrid(ax)
    ax.legend(ncol=2, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0),
              columnspacing=1.1, handlelength=1.2)
    save(fig, OUTDIR, "fig_results_full_benchmark")


# ----------------------------------------------------------------------------- ablation (sample-CV chart dropped)
def make_ablation() -> None:
    full = read_metrics("baseline_benchmark_linked_full_core_full_baseline.csv").query("model=='XGBoost'").iloc[0]
    no_o = read_metrics("baseline_benchmark_linked_full_core_full_no_traffic_outcome.csv").query("model=='XGBoost'").iloc[0]
    no_v = read_metrics("baseline_benchmark_linked_full_core_full_no_volume.csv").query("model=='XGBoost'").iloc[0]
    rows = [("Full", full), ("No outcome\nfields", no_o), ("No volume\nfields", no_v)]
    x = np.arange(len(rows)); width = 0.26
    fig, ax = plt.subplots(figsize=(3.5, 2.7))
    for i, (col, label, color) in enumerate([("f1_macro", "Macro-F1", C1),
                                             ("roc_auc", "ROC-AUC", C3),
                                             ("average_precision", "Avg. precision", ACCENT)]):
        ax.bar(x + (i - 1) * width, [r[1][col] for r in rows], width=width, label=label,
               color=color, edgecolor=INK, linewidth=0.6, zorder=3)
    ax.set_xticks(x); ax.set_xticklabels([r[0] for r in rows])
    ax.set_ylim(0, 0.75); ax.set_ylabel("XGBoost score")
    hgrid(ax)
    ax.legend(frameon=False, loc="upper right")
    save(fig, OUTDIR, "fig_results_ablation")


# ----------------------------------------------------------------------------- operating points
def make_operating_points() -> None:
    df = pd.read_csv(RESULTS / "q1_operating_points.csv")
    keep = ["top_100", "top_250", "top_500", "top_1000", "top_1pct", "top_2pct"]
    labels = ["Top 100", "Top 250", "Top 500", "Top 1k", "Top 1%", "Top 2%"]
    scenarios = [("xgboost_full_stratified", "Full stratified", C1, "o"),
                 ("xgboost_no_outcome_stratified", "No outcome", C2, "s"),
                 ("xgboost_full_temporal_holdout", "Temporal holdout", ACCENT, "^")]
    fig, axes = plt.subplots(2, 1, figsize=(3.5, 4.4), sharex=True, gridspec_kw={"hspace": 0.30})
    x = np.arange(len(keep))
    for scen, label, color, mk in scenarios:
        sub = df[df["scenario"] == scen].set_index("budget").loc[keep]
        axes[0].plot(x, sub["precision"], marker=mk, ms=4.5, linewidth=1.4, label=label,
                     color=color, markeredgecolor="white", markeredgewidth=0.5)
        axes[1].plot(x, sub["lift_over_prevalence"], marker=mk, ms=4.5, linewidth=1.4,
                     color=color, markeredgecolor="white", markeredgewidth=0.5)
    for ax in axes: hgrid(ax)
    axes[0].set_ylabel("Precision"); axes[0].set_ylim(0, 1.05)
    axes[0].text(0.5, -0.13, "(a) precision at budget", transform=axes[0].transAxes,
                 ha="center", va="top", fontsize=8.0, color=INK)
    axes[1].set_ylabel("Lift over prevalence")
    axes[1].set_xticks(x); axes[1].set_xticklabels(labels, rotation=20, ha="right")
    axes[1].text(0.5, -0.30, "(b) prevalence lift at budget", transform=axes[1].transAxes,
                 ha="center", va="top", fontsize=8.0, color=INK)
    axes[0].legend(frameon=False, loc="upper right", handlelength=1.4)
    save(fig, OUTDIR, "fig_operating_point_enrichment")


# ----------------------------------------------------------------------------- feature importance (single colour)
def make_feature_importance() -> None:
    df = pd.read_csv(RESULTS / "q1_feature_importance_no_outcome_xgboost.csv").head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(3.5, 3.1))
    ax.barh(df["feature"], df["importance"], color=C1, edgecolor=INK, linewidth=0.6, height=0.72, zorder=3)
    ax.set_xlabel("Gain importance")
    vgrid(ax)
    save(fig, OUTDIR, "fig_no_outcome_feature_importance")


def main() -> None:
    set_style()
    make_workflow()
    make_linkage_imbalance()
    make_full_benchmark()
    make_ablation()
    make_operating_points()
    make_feature_importance()


if __name__ == "__main__":
    main()
