"""Shared figure style for the COMNET manuscript (Q1 restrained single-theme).

One neutral sans (Nimbus Sans, a Helvetica clone; Open Sans on the author's
Windows build if installed), a constrained navy-to-light-blue ramp with a single
orange accent reserved for the most operationally important quantity, thin
horizontal grid, no top/right spines, consistent type sizes. Import set_style
and the palette names from every figure script so the whole set matches.
"""
from __future__ import annotations
from pathlib import Path
import matplotlib.pyplot as plt

# Palette: navy text/axis, three blues for series, neutral grey, one orange accent.
INK     = "#1b2a3a"   # text, axis, primary series
C1      = "#27496b"   # primary blue
C2      = "#5b8aa6"   # secondary blue
C3      = "#a9c2d1"   # tertiary light blue
NEUTRAL = "#9aa6ad"   # support grey
ACCENT  = "#c8702d"   # single orange accent (use sparingly)
GRID    = "#e6ebee"

# Back-compat aliases for older scripts.
BLUE, TEAL, ORANGE, SKY, GRAY, GREEN, MUTED = C1, C2, ACCENT, C3, NEUTRAL, C2, "#5d6972"

_FONT_STACK = ["DejaVu Sans"]


def set_style() -> None:
    plt.rcParams.update({
        "font.family": _FONT_STACK,
        "font.size": 8.5,
        "axes.titlesize": 9.0,
        "axes.labelsize": 8.5,
        "xtick.labelsize": 8.0,
        "ytick.labelsize": 8.0,
        "legend.fontsize": 7.8,
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "axes.linewidth": 0.8,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "xtick.major.size": 3.0,
        "ytick.major.size": 3.0,
        "savefig.dpi": 600,
        "figure.dpi": 600,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.axisbelow": True,
    })


def hgrid(ax) -> None:
    ax.grid(axis="y", color=GRID, linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)


def vgrid(ax) -> None:
    ax.grid(axis="x", color=GRID, linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)


def save(fig, outdir: Path, stem: str) -> None:
    fig.savefig(outdir / f"{stem}.pdf", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    fig.savefig(outdir / f"{stem}.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    fallback_dir = outdir / "figures"
    if fallback_dir.exists():
        fig.savefig(fallback_dir / f"{stem}.png", bbox_inches="tight", pad_inches=0.03, facecolor="white")
    plt.close(fig)
