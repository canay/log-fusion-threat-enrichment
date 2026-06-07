"""NOTE (release copy): paths in this script reference the private project layout
(data/reports_* inputs, COMNET/manuscript_r0 output). It is included for figure
transparency; the aggregate input CSVs it consumes are in results/."""
from __future__ import annotations

from pathlib import Path
import textwrap

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "github-log-fusion-threat-enrichment" / "results"
OUTDIR = ROOT / "COMNET" / "manuscript_r0"

INK = "#173042"
MUTED = "#5d6972"
GRID = "#d9e1e5"
BLUE = "#2f6f8f"
TEAL = "#2d9b88"
ORANGE = "#d68c2c"
SKY = "#83bdd8"
GRAY = "#6f7d86"
GREEN = "#6f8550"


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "Open Sans",
            "font.size": 9.0,
            "axes.titlesize": 10.0,
            "axes.labelsize": 9.0,
            "xtick.labelsize": 8.0,
            "ytick.labelsize": 8.0,
            "legend.fontsize": 8.0,
            "axes.edgecolor": INK,
            "axes.linewidth": 1.0,
            "savefig.dpi": 600,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def save(fig: plt.Figure, stem: str) -> None:
    for ext in ("png",):
        fig.savefig(OUTDIR / f"{stem}.{ext}", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def add_step(
    ax: plt.Axes,
    x: float,
    y: float,
    w: float,
    h: float,
    step: str,
    title: str,
    lines: list[str],
    face: str,
    accent: str,
) -> None:
    # Shadow
    ax.add_patch(FancyBboxPatch((x + 0.008, y - 0.015), w, h, boxstyle="round,pad=0.0,rounding_size=0.04", facecolor="black", alpha=0.08, edgecolor="none", zorder=1))
    
    # Main box
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.0,rounding_size=0.04", facecolor="#ffffff", edgecolor=INK, linewidth=1.0, zorder=2))
    
    # Top accent header
    header_h = 0.14
    ax.add_patch(FancyBboxPatch((x, y + h - header_h), w, header_h, boxstyle="round,pad=0.0,rounding_size=0.04", facecolor=accent, edgecolor=INK, linewidth=1.0, zorder=3))
    # Overlay a sharp rectangle at the bottom of the header so it's only rounded on top
    ax.add_patch(Rectangle((x, y + h - header_h), w, header_h - 0.02, facecolor=accent, edgecolor="none", zorder=4))
    
    # Step Number
    ax.text(x + 0.02, y + h - (header_h / 2), f"Step {step}", ha="left", va="center", color="white", fontweight="bold", fontsize=7.5, zorder=5)

    # Title
    ax.text(x + w / 2, y + h - header_h - 0.10, wrap(title, 18), ha="center", va="center", color=INK, fontweight="bold", fontsize=7.5, zorder=5)
    
    # Body
    ax.text(x + w / 2, y + 0.15, "\n".join(lines), ha="center", va="center", color=MUTED, fontsize=6.3, linespacing=1.3, zorder=5)


def arrow(ax: plt.Axes, x1: float, y1: float, x2: float, y2: float) -> None:
    # Classic sharp filled arrow
    ax.annotate(
        "", 
        xy=(x2, y2), 
        xytext=(x1, y1),
        arrowprops=dict(arrowstyle="-|>", mutation_scale=12, linewidth=1.2, color=INK, facecolor=INK), zorder=1
    )


def make_workflow() -> None:
    fig, ax = plt.subplots(figsize=(7.16, 2.3))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    y, h, w = 0.30, 0.54, 0.18
    xs = [0.015, 0.215, 0.415, 0.615, 0.815]
    steps = [
        ("1", "Paired firewall exports", ["1,048,576 traffic rows", "186,271 threat rows", "93 shared fields"], "", INK),
        ("2", "Session linkage audit", ["86.8% session coverage", "1,233 strict tuples"], "", BLUE),
        ("3", "Linked-threat label", ["19,311 positives", "1.84% prevalence", "Evidence label"], "", TEAL),
        ("4", "Leakage-aware ML", ["No IDs, IPs, raw time", "27 traffic features", "Ablation tests"], "", MUTED),
        ("5", "Operational reading", ["Full-prevalence metrics", "Top-k budgets", "Triage use"], "", GRAY),
    ]
    for x, args in zip(xs, steps):
        add_step(ax, x, y, w, h, *args)
    for i in range(4):
        arrow(ax, xs[i] + w, y + h / 2, xs[i + 1], y + h / 2)

    ax.text(
        0.50,
        0.08,
        "Primary target: nonzero traffic session linked to threat-log evidence; strict tuple overlap is a linkage-sensitivity diagnostic.",
        ha="center",
        va="center",
        color=MUTED,
        fontsize=7.5,
    )
    save(fig, "fig_methodology_workflow")


def make_linkage_imbalance() -> None:
    meta = pd.read_json(RESULTS / "linked_threat_dataset_metadata.json", typ="series")
    audit = {}
    for line in (RESULTS / "traffic_threat_linkage_audit.md").read_text(encoding="utf-8").splitlines():
        if line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            value = value.strip().replace(",", "")
            try:
                audit[key] = float(value)
            except ValueError:
                pass

    fig, axes = plt.subplots(1, 2, figsize=(3.55, 2.65), gridspec_kw={"wspace": 0.58})
    labels = ["No linked\nrow", "Linked\nrow"]
    values = [int(meta["negative_rows"]), int(meta["positive_rows"])]
    bars = axes[0].bar(labels, values, color=[SKY, TEAL], edgecolor=INK, linewidth=0.8, alpha=0.9, zorder=3)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("Traffic rows\n(log scale)")
    axes[0].text(0.5, -0.22, "(a)", transform=axes[0].transAxes, ha="center", va="top", fontweight="bold")
    axes[0].grid(axis="y", color=GRID, linewidth=0.7, linestyle="--", alpha=0.8, zorder=0)
    for idx, (bar, val) in enumerate(zip(bars, values)):
        pct = 100 * val / sum(values)
        ypos = 3.5e5 if idx == 0 else val * 1.35
        color = "white" if idx == 0 else INK
        axes[0].text(bar.get_x() + bar.get_width() / 2, ypos, f"{val:,}\n{pct:.2f}%", ha="center", va="center", fontsize=7.5, color=color)
    axes[0].set_ylim(1e4, 1.6e6)

    link_labels = ["Threat\nsessions", "Seen in\ntraffic", "Traffic rows\nlinked", "Strict tuple"]
    link_values = [
        int(audit["Threat unique nonzero session identifiers"]),
        int(audit["Threat nonzero session identifiers observed in traffic"]),
        int(audit["Traffic rows with nonzero session overlap"]),
        int(audit["Traffic rows with nonzero session tuple overlap"]),
    ]
    colors = [SKY, TEAL, BLUE, ORANGE]
    bars = axes[1].barh(np.arange(len(link_values)), link_values, color=colors, edgecolor=INK, linewidth=0.8, alpha=0.9, zorder=3)
    axes[1].set_yticks(np.arange(len(link_values)))
    axes[1].set_yticklabels(link_labels)
    axes[1].invert_yaxis()
    axes[1].set_xlabel("Count")
    axes[1].text(0.5, -0.22, "(b)", transform=axes[1].transAxes, ha="center", va="top", fontweight="bold")
    axes[1].grid(axis="x", color=GRID, linewidth=0.7, linestyle="--", alpha=0.8, zorder=0)
    for bar, val in zip(bars, link_values):
        axes[1].text(val + max(link_values) * 0.025, bar.get_y() + bar.get_height() / 2, f"{val:,}", ha="left", va="center", fontsize=7.5)
    save(fig, "fig_linkage_imbalance")


def read_metrics(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / name)


def make_full_benchmark() -> None:
    df = read_metrics("baseline_benchmark_linked_full_core_full_baseline.csv")
    df = df.set_index("model").loc[["XGBoost", "Extra Trees", "LightGBM", "CatBoost"]].reset_index()
    metrics = [
        ("f1_macro", "Macro-F1", INK),
        ("balanced_accuracy", "Balanced accuracy", TEAL),
        ("average_precision", "Average precision", ORANGE),
        ("roc_auc", "ROC-AUC", SKY),
    ]
    x = np.arange(len(df))
    width = 0.18
    fig, ax = plt.subplots(figsize=(3.55, 2.85))
    for i, (col, label, color) in enumerate(metrics):
        offset = (i - 1.5) * width
        ax.vlines(x + offset, 0, df[col], color=color, linewidth=1.5)
        ax.plot(x + offset, df[col], "o", color=color, markersize=5.5, label=label, markeredgecolor=INK, markeredgewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(df["model"])
    ax.set_ylim(0, 0.72)
    ax.set_ylabel("Score")
    ax.grid(axis="y", color=GRID, linewidth=0.7, linestyle="--", alpha=0.8, zorder=0)
    ax.legend(ncol=2, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.02), columnspacing=1.0)
    save(fig, "fig_results_full_benchmark")


def make_ablation_cv() -> None:
    full = read_metrics("baseline_benchmark_linked_full_core_full_baseline.csv").query("model == 'XGBoost'").iloc[0]
    no_outcome = read_metrics("baseline_benchmark_linked_full_core_full_no_traffic_outcome.csv").query("model == 'XGBoost'").iloc[0]
    no_volume = read_metrics("baseline_benchmark_linked_full_core_full_no_volume.csv").query("model == 'XGBoost'").iloc[0]
    scenarios = pd.DataFrame(
        [
            {"scenario": "Full", "Macro-F1": full["f1_macro"], "Average precision": full["average_precision"], "ROC-AUC": full["roc_auc"]},
            {"scenario": "No outcome\nfields", "Macro-F1": no_outcome["f1_macro"], "Average precision": no_outcome["average_precision"], "ROC-AUC": no_outcome["roc_auc"]},
            {"scenario": "No volume\nfields", "Macro-F1": no_volume["f1_macro"], "Average precision": no_volume["average_precision"], "ROC-AUC": no_volume["roc_auc"]},
        ]
    )
    cv = pd.read_csv(RESULTS / "baseline_benchmark_linked_sample_core_sample_top_cv_cv_summary.csv")
    cv = cv.set_index("model").loc[["Extra Trees", "XGBoost", "LightGBM", "CatBoost"]].reset_index()

    fig_abl, ax_abl = plt.subplots(figsize=(3.55, 2.9))
    x = np.arange(len(scenarios))
    width = 0.24
    for i, (col, color) in enumerate([("Macro-F1", INK), ("Average precision", ORANGE), ("ROC-AUC", TEAL)]):
        ax_abl.bar(x + (i - 1) * width, scenarios[col], width=width, label=col, color=color, edgecolor=INK, linewidth=0.8, alpha=0.9, zorder=3)
    ax_abl.set_xticks(x)
    ax_abl.set_xticklabels(["Full", "No outcome\nfields", "No volume\nfields"])
    ax_abl.set_ylim(0, 0.72)
    ax_abl.set_ylabel("XGBoost score")
    ax_abl.grid(axis="y", color=GRID, linewidth=0.7, linestyle="--", alpha=0.8, zorder=0)
    ax_abl.legend(frameon=False, loc="upper right", fontsize=7.5)
    save(fig_abl, "fig_results_ablation")

    fig_cv, ax_cv = plt.subplots(figsize=(3.55, 2.9))
    x2 = np.arange(len(cv))
    err = cv["test_f1_macro.std"]
    ax_cv.bar(x2, cv["test_f1_macro.mean"], yerr=err, capsize=2.5, color=[TEAL, INK, SKY, GRAY], edgecolor=INK, linewidth=0.8, alpha=0.9, zorder=3)
    ax_cv.set_xticks(x2)
    ax_cv.set_xticklabels(cv["model"], rotation=20, ha="right")
    ax_cv.set_ylim(0, 0.72)
    ax_cv.set_ylabel("Sample CV macro-F1")
    ax_cv.grid(axis="y", color=GRID, linewidth=0.7, linestyle="--", alpha=0.8, zorder=0)
    save(fig_cv, "fig_results_sample_cv")


def make_operating_points() -> None:
    df = pd.read_csv(RESULTS / "q1_operating_points.csv")
    keep = ["top_100", "top_250", "top_500", "top_1000", "top_1pct", "top_2pct"]
    labels = ["Top 100", "Top 250", "Top 500", "Top 1,000", "Top 1%", "Top 2%"]
    scenarios = [
        ("xgboost_full_stratified", "Full stratified", INK),
        ("xgboost_no_outcome_stratified", "No outcome", TEAL),
        ("xgboost_full_temporal_holdout", "Temporal holdout", ORANGE),
    ]
    fig, axes = plt.subplots(2, 1, figsize=(3.55, 4.8), sharex=True, gridspec_kw={"hspace": 0.2})
    x = np.arange(len(keep))
    for scenario, label, color in scenarios:
        sub = df[df["scenario"] == scenario].set_index("budget").loc[keep]
        axes[0].plot(x, sub["precision"], marker="o", linewidth=1.5, label=label, color=color)
        axes[1].plot(x, sub["lift_over_prevalence"], marker="o", linewidth=1.5, label=label, color=color)
    for ax in axes:
        ax.grid(axis="y", color=GRID, linewidth=0.7, linestyle="--", alpha=0.8, zorder=0)
    axes[0].set_ylabel("Precision")
    axes[0].set_ylim(0, 1.05)
    axes[0].text(0.5, -0.15, "(a) Precision", transform=axes[0].transAxes, ha="center", va="top", fontweight="bold")
    
    axes[1].set_ylabel("Lift over test prevalence")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=25, ha="right")
    axes[1].text(0.5, -0.28, "(b) Lift", transform=axes[1].transAxes, ha="center", va="top", fontweight="bold")
    axes[1].legend(frameon=False, loc="upper right", fontsize=7.5)
    save(fig, "fig_operating_point_enrichment")


def make_feature_importance() -> None:
    df = pd.read_csv(RESULTS / "q1_feature_importance_no_outcome_xgboost.csv").head(10)
    df = df.iloc[::-1]
    
    import matplotlib.colors as mcolors
    cmap = mcolors.LinearSegmentedColormap.from_list("custom_cmap", [SKY, TEAL, BLUE])
    bar_colors = [cmap(i) for i in np.linspace(0.1, 0.9, len(df))]
    
    fig, ax = plt.subplots(figsize=(3.55, 3.4))
    ax.barh(df["feature"], df["importance"], color=bar_colors, edgecolor=INK, linewidth=0.8, alpha=0.9, zorder=3)
    ax.set_xlabel("Feature importance")
    ax.grid(axis="x", color=GRID, linewidth=0.7, linestyle="--", alpha=0.8, zorder=0)
    save(fig, "fig_no_outcome_feature_importance")


def main() -> None:
    set_style()
    make_workflow()
    make_linkage_imbalance()
    make_full_benchmark()
    make_ablation_cv()
    make_operating_points()
    make_feature_importance()


if __name__ == "__main__":
    main()
