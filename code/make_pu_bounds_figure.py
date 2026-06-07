"""PU prevalence-lens figure (Section 5.6): labeled share, structural floor,
and the unreliable SCAR point estimate on one axis.
Output: COMNET/manuscript_r0/fig_pu_prevalence_bounds.png (600 dpi, PNG only).
Open Sans requested; DejaVu fallback in environments without it.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

INK, MUTED, GRID = "#173042", "#5d6972", "#d9e1e5"
BLUE, TEAL, ORANGE, SKY = "#2f6f8f", "#2d9b88", "#d68c2c", "#83bdd8"
plt.rcParams.update({"font.family": ["Open Sans", "DejaVu Sans"], "font.size": 9.0,
                     "text.color": INK, "axes.edgecolor": INK})

fig, ax = plt.subplots(figsize=(5.0, 2.1), dpi=600)
ax.set_xlim(0, 27); ax.set_ylim(0, 1)
ax.get_yaxis().set_visible(False)
for s in ("left", "right", "top"): ax.spines[s].set_visible(False)
ax.spines["bottom"].set_position(("data", 0.30))
ax.set_xticks([0, 5, 10, 15, 20, 25])
ax.set_xlabel("share of all traffic sessions (%)", fontsize=8.5, color=INK)
ax.tick_params(colors=INK, labelsize=8)

# tanimli bolge: taban -> saga (ust sinir tanimsiz)
ax.axvspan(2.64, 27, ymin=0.30, ymax=0.52, color=TEAL, alpha=0.12, lw=0)
ax.annotate("identified region (upper limit not identified)", xy=(14.5, 0.41),
            ha="center", va="center", fontsize=7.6, color=TEAL)

def marker(x, y, label, sub, color, mk):
    ax.plot([x], [0.30], marker=mk, ms=8, color=color, zorder=5, clip_on=False)
    ax.annotate(label, xy=(x, 0.30), xytext=(x, y), ha="center", fontsize=8.2,
                color=color, fontweight="bold",
                arrowprops=dict(arrowstyle="-", color=color, lw=0.9))
    ax.annotate(sub, xy=(x, y), xytext=(0, -11), textcoords="offset points",
                ha="center", fontsize=7.2, color=MUTED)

marker(1.84, 0.82, "labeled share 1.84%", "19,311 linked rows", BLUE, "D")
marker(2.64, 0.62, "structural floor 2.64%", "+8,341 threat-terminated, unlinked", TEAL, "^")
marker(24.3, 0.82, "SCAR estimate 24.3%", "Elkan-Noto; unreliable here", ORANGE, "x")

out = Path(__file__).resolve().parents[1] / "COMNET/manuscript_r0/fig_pu_prevalence_bounds.png"
fig.savefig(out, bbox_inches="tight", pad_inches=0.03, facecolor="white")
print("yazildi:", out)
