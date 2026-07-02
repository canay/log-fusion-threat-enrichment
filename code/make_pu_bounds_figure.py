"""PU prevalence-lens figure in the shared Q1 style (Figure: PU bounds).

Labeled share, structural floor, and the unreliable SCAR point estimate on one
axis, showing that selected-at-random labeling fails globally on this corpus.
"""
from pathlib import Path
import matplotlib.pyplot as plt

from fig_style import set_style, save, INK, C1, C2, ACCENT, NEUTRAL

OUTDIR = Path(__file__).resolve().parents[2] / "COMNET" / "manuscript-r0"


def main() -> None:
    set_style()
    fig, ax = plt.subplots(figsize=(5.0, 1.95))
    ax.set_xlim(0, 27); ax.set_ylim(0, 1)
    ax.get_yaxis().set_visible(False)
    for s in ("left", "right", "top"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_position(("data", 0.30))
    ax.set_xticks([0, 5, 10, 15, 20, 25])
    ax.set_xlabel("share of all traffic sessions (%)")

    ax.axvspan(2.64, 27, ymin=0.30, ymax=0.50, color=C2, alpha=0.14, lw=0)
    ax.annotate("identified region (upper limit not identified)", xy=(14.7, 0.40),
                ha="center", va="center", fontsize=7.2, color=C1)

    def marker(x, y, label, sub, color, mk):
        ax.plot([x], [0.30], marker=mk, ms=8, color=color, zorder=5, clip_on=False,
                markeredgecolor="white", markeredgewidth=0.6)
        ax.annotate(label, xy=(x, 0.30), xytext=(x, y), ha="center", fontsize=8.0,
                    color=color, fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color=color, lw=0.8))
        ax.annotate(sub, xy=(x, y), xytext=(0, -10), textcoords="offset points",
                    ha="center", fontsize=6.8, color="#5d6972")

    marker(1.84, 0.82, "labeled share 1.84%", "19,311 linked rows", C1, "D")
    marker(2.64, 0.60, "structural floor 2.64%", "+8,341 threat-terminated, unlinked", C2, "^")
    marker(24.3, 0.82, "SCAR estimate 24.3%", "Elkan-Noto; unreliable here", ACCENT, "X")

    save(fig, OUTDIR, "fig_pu_prevalence_bounds")


if __name__ == "__main__":
    main()
