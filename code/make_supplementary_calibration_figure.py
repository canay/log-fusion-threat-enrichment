"""Calibration-bin diagnostic in the shared Q1 style (Figure: calibration)."""
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

from fig_style import set_style, save, hgrid, INK, C1, C2, ACCENT, NEUTRAL

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "reports_evidence_uncertainty" / "calibration_bins.csv"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTDIR = PROJECT_ROOT / "COMNET" / "manuscript-r0"


def main() -> None:
    set_style()
    df = pd.read_csv(INPUT)
    full = df[df["evidence_family"] == "full_core"].sort_values("bin").copy()
    if full.empty:
        raise ValueError("No full_core rows in calibration_bins.csv")
    labels = [f"{lo:.1f}-{hi:.1f}" for lo, hi in zip(full["lower"], full["upper"])]

    fig, axes = plt.subplots(2, 1, figsize=(3.5, 4.9), gridspec_kw={"hspace": 0.85})

    axes[0].plot([0, 1], [0, 1], color=NEUTRAL, linewidth=0.9, linestyle="--", label="Ideal")
    axes[0].plot(full["mean_score"], full["observed_rate"], color=C1, marker="o",
                 markersize=4, linewidth=1.3, markeredgecolor="white", markeredgewidth=0.5,
                 label="Full-core XGBoost")
    axes[0].set_xlim(-0.02, 1.02); axes[0].set_ylim(-0.02, 1.02)
    axes[0].set_xlabel("Mean predicted score")
    axes[0].set_ylabel("Observed linked-threat rate")
    axes[0].text(0.5, -0.36, "(a) reliability", transform=axes[0].transAxes,
                 ha="center", va="top", fontsize=8.0, color=INK)
    axes[0].grid(color="#e6ebee", linewidth=0.6); axes[0].set_axisbelow(True)
    axes[0].legend(frameon=False, loc="upper left")

    # One accent reserved for the sparse, less-reliable high-score bins.
    colors = [C2 if c >= 1000 else ACCENT for c in full["count"]]
    axes[1].bar(range(len(full)), full["count"], color=colors, edgecolor=INK, linewidth=0.5, zorder=3)
    axes[1].set_yscale("log")
    axes[1].set_xticks(range(len(full)))
    axes[1].set_xticklabels(labels, rotation=38, ha="right")
    axes[1].set_ylabel("Bin support (log scale)")
    axes[1].text(0.5, -0.52, "(b) support per probability bin", transform=axes[1].transAxes,
                 ha="center", va="top", fontsize=8.0, color=INK)
    hgrid(axes[1])
    for idx, count in enumerate(full["count"]):
        axes[1].text(idx, count * 1.25, f"{int(count):,}", ha="center", va="bottom", fontsize=6.0, color=INK)

    save(fig, OUTDIR, "fig_supp_calibration_bins")


if __name__ == "__main__":
    main()
