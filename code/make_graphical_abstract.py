"""Graphical abstract for the COMNET submission (Elsevier 13 x 5 cm, 600 dpi PNG).

Reuses the manuscript palette. Open Sans is requested; if unavailable the
renderer falls back to the matplotlib default (regenerate on Windows for the
submission copy if the fallback font is visible).
Output: COMNET/manuscript_r0/graphical_abstract.png
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

INK, MUTED = "#1b2a3a", "#5d6972"
BLUE, TEAL, ORANGE, SKY = "#27496b", "#5b8aa6", "#c8702d", "#a9c2d1"
plt.rcParams.update({"font.family": ["Nimbus Sans", "Open Sans", "Liberation Sans", "DejaVu Sans"], "text.color": INK})

CM = 1 / 2.54
fig, ax = plt.subplots(figsize=(13 * CM, 5 * CM), dpi=600)
ax.set_xlim(0, 13); ax.set_ylim(0, 5); ax.axis("off")

def box(x, y, w, h, fc, ec=INK, lw=0.8, r=0.12):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.06,rounding_size={r}",
                                facecolor=fc, edgecolor=ec, linewidth=lw))

def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=9,
                                 linewidth=1.1, color=INK))

# Panel 1: paired exports
box(0.25, 2.85, 3.1, 1.05, "#eaf1f5")
ax.text(1.8, 3.62, "Traffic log", ha="center", fontsize=6.4, fontweight="bold", color=BLUE)
ax.text(1.8, 3.18, "1,048,576 sessions", ha="center", fontsize=5.6, color=INK)
box(0.25, 1.45, 3.1, 1.05, "#fdf3e3")
ax.text(1.8, 2.22, "Threat log", ha="center", fontsize=6.4, fontweight="bold", color=ORANGE)
ax.text(1.8, 1.78, "186,271 security events", ha="center", fontsize=5.6, color=INK)
ax.text(1.8, 0.62, "Real enterprise firewall exports", ha="center", fontsize=5.4, color=MUTED)

# Panel 2: session-level linkage
arrow(3.55, 3.30, 4.32, 2.90)
arrow(3.55, 2.00, 4.32, 2.40)
box(4.45, 1.55, 3.7, 2.05, "#e7f3f0")
ax.text(6.30, 3.20, "Session-level linkage", ha="center", fontsize=6.0, fontweight="bold", color=TEAL)
ax.text(6.30, 2.66, "has_linked_threat", ha="center", fontsize=5.4, family="monospace", color=INK)
ax.text(6.30, 2.18, "19,311 linked rows = 1.84%", ha="center", fontsize=5.2, color=INK)
ax.text(6.30, 1.80, "true rate >= 2.64% (PU floor)", ha="center", fontsize=5.0, color=TEAL)
ax.text(6.30, 0.55, "Natural prevalence preserved,\nlinked evidence, not proven maliciousness", ha="center", fontsize=5.0, color=MUTED)

# Panel 3: outcome
arrow(8.30, 2.62, 9.02, 2.62)
box(9.15, 1.15, 3.6, 2.85, "#eef4f8")
ax.text(10.95, 3.62, "Leakage-aware benchmark", ha="center", fontsize=6.2, fontweight="bold", color=BLUE)
bars = [("AP", 0.094, MUTED), ("Top-100\nprecision", 0.99, TEAL)]
bx = [10.0, 11.6]
for (lab, v, c), x in zip(bars, bx):
    ax.add_patch(plt.Rectangle((x - 0.28, 2.02), 0.56, 1.15 * v, facecolor=c, edgecolor=INK, linewidth=0.5))
    ax.text(x, 2.02 + 1.15 * v + 0.10, f"{v:.2f}" if v < 0.99 else "0.99", ha="center", fontsize=5.4, color=INK)
    ax.text(x, 1.86, lab, ha="center", va="top", fontsize=4.8, color=INK)
ax.text(10.95, 0.55, "Weak global signal, strong analyst-budget\ntriage queue for SOC monitoring", ha="center", fontsize=5.0, color=MUTED)

out = Path(__file__).resolve().parents[1] / "COMNET/manuscript_r0/graphical_abstract.png"
fig.savefig(out, bbox_inches="tight", pad_inches=0.04, facecolor="white")
print("yazildi:", out)
