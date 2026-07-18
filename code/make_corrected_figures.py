"""Generate the empirical manuscript figures from the canonical corrected run.

The workflow diagram is source-native TikZ and is compiled separately.  This
script deliberately reads only the aggregate JSON produced by the corrected
1,233-positive, group-disjoint run.  It never reads the predecessor 19,311-label
model outputs or restricted row-level telemetry.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from fig_style import ACCENT, C1, C2, C3, GRID, INK, NEUTRAL, save, set_style


ROOT = Path(__file__).resolve().parents[1]
LOCAL_CANDIDATES = sorted(
    ROOT.glob(
        "experiments/2026-07-12_*_corrected-linkage-group-disjoint/"
        "out/corrected_linkage_results.json"
    )
)
LOCAL_RESULTS = LOCAL_CANDIDATES[0] if LOCAL_CANDIDATES else Path("__missing_local_results__")
PUBLIC_RESULTS = ROOT / "results" / "corrected_linkage_results.json"
DEFAULT_RESULTS = LOCAL_RESULTS if LOCAL_RESULTS.exists() else PUBLIC_RESULTS

# Aggregate construct-audit count from the preserved predecessor target record.
# This is contextual evidence, not a corrected-run model metric.
PREDECESSOR_AUDIT_COUNT = 19_311


def panel_label(ax, label: str, size: float = 9.5) -> None:
    ax.annotate(
        f"({label})",
        xy=(0.5, 0),
        xycoords="axes fraction",
        xytext=(0, -38),
        textcoords="offset points",
        ha="center",
        va="top",
        fontsize=size,
        color=INK,
    )


def linkage(data: dict, out: Path) -> None:
    audit = data["label_audit"]
    old_rc = plt.rcParams.copy()
    plt.rcParams.update({"axes.labelsize": 9.5, "xtick.labelsize": 9.0, "ytick.labelsize": 9.0})
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(8.25, 2.6),
        gridspec_kw={"width_ratios": [1.15, 1.0]},
    )

    names = [
        "Traffic rows",
        "Unrestricted ID contrast",
        "Corrected same-session target",
    ]
    values = [audit["traffic_rows"], PREDECESSOR_AUDIT_COUNT, audit["corrected_positive_rows"]]
    colors = [C1, NEUTRAL, ACCENT]
    y = np.arange(len(names))
    bars = axes[0].barh(y, values, color=colors, height=0.58, zorder=3)
    axes[0].set_xscale("log")
    axes[0].set_yticks(y, names)
    axes[0].set_ylim(3.1, -1.1)
    axes[0].set_xlabel("Rows (log scale)")
    axes[0].grid(axis="x", color=GRID, linewidth=0.7, zorder=0)
    axes[0].spines["left"].set_visible(True)
    axes[0].tick_params(axis="y", length=0)
    for bar, value in zip(bars, values):
        axes[0].text(
            value * 1.10,
            bar.get_y() + bar.get_height() / 2,
            f"{value:,}",
            va="center",
            fontsize=9,
            color=INK,
        )
    panel_label(axes[0], "a", size=10.5)

    tolerances = [0, 30, 60, 300]
    tolerance_counts = [audit["tolerance_positive_rows"][str(x)] for x in tolerances]
    axes[1].plot(
        tolerances,
        tolerance_counts,
        marker="o",
        color=C1,
        linewidth=1.8,
        markersize=4.5,
        label="Time-compatible rows",
    )
    direct_tuple_count = audit.get(
        "exact_direct_tuple_rows_fail_closed",
        audit.get("exact_direct_tuple_rows"),
    )
    if direct_tuple_count is None:
        raise KeyError("No direct-tuple audit count found in canonical results")
    axes[1].axhline(
        direct_tuple_count,
        color=ACCENT,
        linestyle="--",
        linewidth=1.25,
        label="Direct and NAT-aware\ntuple audits",
    )
    axes[1].set_xticks(tolerances)
    axes[1].set_xlabel("Boundary tolerance (s)")
    axes[1].set_ylabel("Corrected positives")
    axes[1].set_ylim(min(tolerance_counts) - 5, max(tolerance_counts) + 8)
    axes[1].grid(axis="y", color=GRID, linewidth=0.7)
    axes[1].annotate(
        f"{tolerance_counts[0]:,}",
        (tolerances[0], tolerance_counts[0]),
        xytext=(0, 7),
        textcoords="offset points",
        ha="center",
        fontsize=8.4,
    )
    axes[1].annotate(
        "1,233 at 30--300 s",
        (60, tolerance_counts[2]),
        xytext=(0, 8),
        textcoords="offset points",
        ha="center",
        fontsize=8.4,
    )
    leg = axes[1].legend(frameon=False, bbox_to_anchor=(1.05, 1.0), loc="upper left", fontsize=8.2)
    leg.set_in_layout(False)
    panel_label(axes[1], "b", size=10.5)

    fig.tight_layout(w_pad=4.4)
    fig.savefig(out / "fig_corrected_linkage_audit.pdf", bbox_inches="tight", bbox_extra_artists=[leg], pad_inches=0.03, facecolor="white")
    fig.savefig(out / "fig_corrected_linkage_audit.png", bbox_inches="tight", bbox_extra_artists=[leg], pad_inches=0.03, facecolor="white")
    fallback_dir = out / "figures"
    if fallback_dir.exists():
        fig.savefig(fallback_dir / "fig_corrected_linkage_audit.png", bbox_inches="tight", bbox_extra_artists=[leg], pad_inches=0.03, facecolor="white")
    plt.close(fig)
    plt.rcParams.update(old_rc)


def primary_rows(data: dict) -> list[dict]:
    rows = [
        row
        for row in data["results"]
        if row["evaluation"] == "primary_later_20pct" and row["seed"] == 42
    ]
    desired = [
        ("XGBoost", "full_core"),
        ("XGBoost", "no_outcome"),
        ("XGBoost", "hard_proxy"),
        ("Extra Trees", "no_outcome"),
        ("LightGBM", "no_outcome"),
        ("CatBoost", "no_outcome"),
        ("Logistic Regression", "no_outcome"),
    ]
    lookup = {(row["model"], row["feature_set"]): row for row in rows}
    return [lookup[key] for key in desired]


def model_evidence(data: dict, out: Path) -> None:
    rows = primary_rows(data)
    top100 = {
        (row["model"], row["feature_set"], row["seed"]): row["precision"]
        for row in data["topk"]
        if row["evaluation"] == "primary_later_20pct" and row["k"] == 100
    }
    labels = [
        "XGBoost / full core",
        "XGBoost / no outcome",
        "XGBoost / hard proxy",
        "Extra Trees / no outcome",
        "LightGBM / no outcome",
        "CatBoost / no outcome",
        "Linear / no outcome",
    ]
    colors = [ACCENT, C1, C2, C3, C3, C3, NEUTRAL]
    metrics = [
        ("average_precision", "Average precision", "a"),
        ("macro_f1", "Macro-F1", "b"),
        ("p100", "Precision at 100", "c"),
    ]
    values = {
        "average_precision": [row["average_precision"] for row in rows],
        "macro_f1": [row["macro_f1"] for row in rows],
        "p100": [
            top100[(row["model"], row["feature_set"], row["seed"])] for row in rows
        ],
    }

    fig, axes = plt.subplots(1, 3, figsize=(10.17, 4.1), sharey=True)
    y = np.arange(len(rows))
    for ax, (key, title, letter) in zip(axes, metrics):
        bars = ax.barh(y, values[key], color=colors, height=0.58, zorder=3)
        ax.set_xlim(0, 1.10)
        ax.set_xlabel(title)
        ax.grid(axis="x", color=GRID, linewidth=0.7, zorder=0)
        ax.invert_yaxis()
        for bar, value in zip(bars, values[key]):
            ax.text(
                value + 0.018,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.3f}",
                va="center",
                fontsize=7.1,
            )
        panel_label(ax, letter)
    axes[0].set_yticks(y, labels)
    axes[0].tick_params(axis="y", length=0)
    for ax in axes[1:]:
        ax.tick_params(axis="y", length=0)
    axes[0].axvline(
        data["random_ranking_average_precision"],
        color=INK,
        linestyle=":",
        linewidth=1.0,
    )
    axes[0].text(
        0.015,
        6.50,
        f"Random AP {data['random_ranking_average_precision']:.4f}",
        fontsize=6.9,
        color=NEUTRAL,
    )
    fig.tight_layout(w_pad=4.6)
    save(fig, out, "fig_corrected_model_ap")


def topk_budget(data: dict, out: Path) -> None:
    rows = [
        row
        for row in data["topk"]
        if row["evaluation"] == "primary_later_20pct"
        and row["model"] == "XGBoost"
        and row["seed"] == 42
        and row["feature_set"] in {"full_core", "no_outcome", "hard_proxy"}
    ]
    styles = {
        "full_core": ("Full core (upper bound)", ACCENT, "o"),
        "no_outcome": ("No outcome (primary)", C1, "s"),
        "hard_proxy": ("Hard proxy stress test", C2, "^"),
    }
    fig, axes = plt.subplots(1, 2, figsize=(8.25, 3.25), sharex=True)
    for feature_set, (label, color, marker) in styles.items():
        subset = sorted(
            [row for row in rows if row["feature_set"] == feature_set],
            key=lambda row: row["k"],
        )
        k = np.array([row["k"] for row in subset])
        precision = np.array([row["precision"] for row in subset])
        recall = np.array([row["recall"] for row in subset])
        lower = np.array([row["precision_cp95"][0] for row in subset])
        upper = np.array([row["precision_cp95"][1] for row in subset])
        axes[0].plot(k, precision, marker=marker, color=color, linewidth=1.65, label=label)
        axes[0].fill_between(k, lower, upper, color=color, alpha=0.10, linewidth=0)
        axes[1].plot(k, recall, marker=marker, color=color, linewidth=1.65, label=label)
    for ax in axes:
        ax.set_xscale("log")
        ax.set_xticks([50, 100, 250, 500, 1000], ["50", "100", "250", "500", "1,000"])
        ax.set_xlabel("Review budget $k$ (unique groups)")
        ax.set_ylim(0, 1.03)
        ax.grid(color=GRID, linewidth=0.7)
    axes[0].set_ylabel("Precision")
    axes[1].set_ylabel("Recall")
    axes[0].legend(frameon=False, loc="upper right", fontsize=7.2)
    panel_label(axes[0], "a")
    panel_label(axes[1], "b")
    fig.tight_layout(w_pad=4.4)
    save(fig, out, "fig_corrected_topk_budget")


def stability(data: dict, out: Path) -> None:
    seed_rows = sorted(
        [
            row
            for row in data["results"]
            if row["evaluation"] == "primary_later_20pct"
            and row["model"] == "XGBoost"
            and row["feature_set"] == "no_outcome"
        ],
        key=lambda row: row["seed"],
    )
    rolling = sorted(
        [row for row in data["results"] if row["evaluation"].startswith("rolling_origin_fold_")],
        key=lambda row: row["evaluation"],
    )
    seed_top100 = {
        row["seed"]: row["precision"]
        for row in data["topk"]
        if row["evaluation"] == "primary_later_20pct"
        and row["model"] == "XGBoost"
        and row["feature_set"] == "no_outcome"
        and row["k"] == 100
    }
    rolling_top100 = {
        row["evaluation"]: row["precision"]
        for row in data["topk"]
        if row["evaluation"].startswith("rolling_origin_fold_") and row["k"] == 100
    }

    fig, axes = plt.subplots(1, 2, figsize=(8.25, 3.2), sharey=True)
    axes[0].plot(
        [row["seed"] for row in seed_rows],
        [row["average_precision"] for row in seed_rows],
        "o-",
        color=C1,
        linewidth=1.7,
        label="AP",
    )
    axes[0].plot(
        [row["seed"] for row in seed_rows],
        [seed_top100[row["seed"]] for row in seed_rows],
        "s--",
        color=ACCENT,
        linewidth=1.5,
        label="P@100",
    )
    axes[0].set_xlabel("Complete-fit seed")
    axes[0].set_ylabel("Score")
    axes[0].set_title("Stochastic fit sensitivity")

    axes[1].plot(
        range(1, 4),
        [row["average_precision"] for row in rolling],
        "o-",
        color=C1,
        linewidth=1.7,
        label="AP",
    )
    axes[1].plot(
        range(1, 4),
        [rolling_top100[row["evaluation"]] for row in rolling],
        "s--",
        color=ACCENT,
        linewidth=1.5,
        label="P@100",
    )
    axes[1].set_xticks([1, 2, 3])
    axes[1].set_xlabel("Ordered test block")
    axes[1].set_title("Within-window block variation")
    for ax in axes:
        ax.set_ylim(0.45, 1.02)
        ax.grid(color=GRID, linewidth=0.7)
    axes[0].legend(frameon=False, loc="lower right")
    panel_label(axes[0], "a")
    panel_label(axes[1], "b")
    fig.tight_layout(w_pad=4.4)
    save(fig, out, "fig_corrected_stability")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(args.results.read_text(encoding="utf-8"))
    set_style()
    linkage(data, args.output_dir)
    model_evidence(data, args.output_dir)
    topk_budget(data, args.output_dir)
    stability(data, args.output_dir)


if __name__ == "__main__":
    main()
