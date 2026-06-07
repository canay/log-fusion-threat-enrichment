"""NOTE (release copy): paths in this script reference the private project layout
(data/reports_* inputs, COMNET/manuscript_r0 output). It is included for figure
transparency; the aggregate input CSVs it consumes are in results/."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "reports_evidence_uncertainty" / "calibration_bins.csv"
OUTDIR = ROOT / "COMNET" / "manuscript_r0"

INK = "#173042"
MUTED = "#5d6972"
GRID = "#d9e1e5"
BLUE = "#2f6f8f"
TEAL = "#2d9b88"
ORANGE = "#d68c2c"


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


def main() -> None:
    set_style()
    df = pd.read_csv(INPUT)
    full = df[df["evidence_family"] == "full_core"].copy()
    if full.empty:
        raise ValueError("No full_core rows found in calibration_bins.csv")

    full = full.sort_values("bin")
    labels = [f"{lo:.1f}-{hi:.1f}" for lo, hi in zip(full["lower"], full["upper"])]

    fig, axes = plt.subplots(2, 1, figsize=(3.55, 5.15), gridspec_kw={"hspace": 0.92})

    axes[0].plot([0, 1], [0, 1], color=MUTED, linewidth=0.9, linestyle="--", label="Ideal")
    axes[0].plot(
        full["mean_score"],
        full["observed_rate"],
        color=BLUE,
        marker="o",
        markersize=4,
        linewidth=1.3,
        label="Full-core XGBoost",
    )
    axes[0].set_xlim(-0.02, 1.02)
    axes[0].set_ylim(-0.02, 1.02)
    axes[0].set_xlabel("Mean predicted score")
    axes[0].set_ylabel("Observed linked-threat rate")
    axes[0].text(0.5, -0.40, "(a)", transform=axes[0].transAxes, ha="center", va="top", fontweight="bold")
    axes[0].grid(color=GRID, linewidth=0.6)
    axes[0].legend(frameon=False, loc="upper left")

    colors = [TEAL if count >= 1000 else ORANGE for count in full["count"]]
    axes[1].bar(range(len(full)), full["count"], color=colors, edgecolor=INK, linewidth=0.5)
    axes[1].set_yscale("log")
    axes[1].set_xticks(range(len(full)))
    axes[1].set_xticklabels(labels, rotation=38, ha="right")
    axes[1].set_ylabel("Bin support (log scale)")
    axes[1].text(0.5, -0.50, "(b)", transform=axes[1].transAxes, ha="center", va="top", fontweight="bold")
    axes[1].grid(axis="y", color=GRID, linewidth=0.6)
    for idx, count in enumerate(full["count"]):
        axes[1].text(idx, count * 1.18, f"{int(count):,}", ha="center", va="bottom", fontsize=6.3, color=INK)

    fig.savefig(OUTDIR / "fig_supp_calibration_bins.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
