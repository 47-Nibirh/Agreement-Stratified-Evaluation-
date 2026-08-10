"""
Shared figure style for the Phase 2 report.

One place defines typography, palette, grid and export settings so every
figure in the document reads as part of the same system. Palette is
colour-blind safe (Okabe-Ito derived) and every figure is exported at 300 dpi
with tight bounding boxes for print reproduction.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
FIGDIR = ROOT / "figures_phase2"
FIGDIR.mkdir(exist_ok=True)

DPI = 300

# ---- Okabe-Ito derived, colour-blind safe --------------------------------
INK = "#1a1a1a"
MUTED = "#6b7280"
GRID = "#dfe3e8"
BLUE = "#0072B2"
ORANGE = "#D55E00"
GREEN = "#009E73"
PURPLE = "#8256A6"
YELLOW = "#E69F00"
CYAN = "#56B4E9"
PINK = "#CC79A7"
RED = "#B2182B"

SEED_COLORS = [BLUE, ORANGE, GREEN, PURPLE, CYAN]
SPLIT_COLORS = {"Train": BLUE, "Validation": YELLOW, "Test": ORANGE}
WALL_COLORS = {"G": BLUE, "A": ORANGE, "L": GREEN, "P": PURPLE,
               "OTHERCLASS": MUTED}


def apply() -> None:
    mpl.rcParams.update({
        "figure.dpi": 110,
        "savefig.dpi": DPI,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans"],
        "font.size": 9,
        "axes.titlesize": 10.5,
        "axes.titleweight": "bold",
        "axes.labelsize": 9.5,
        "axes.edgecolor": "#9aa3ad",
        "axes.linewidth": 0.8,
        "axes.labelcolor": INK,
        "axes.titlecolor": INK,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.7,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "legend.frameon": False,
        "legend.fontsize": 8.5,
        "text.color": INK,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


def despine(ax, left=False, bottom=False):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if left:
        ax.spines["left"].set_visible(False)
    if bottom:
        ax.spines["bottom"].set_visible(False)


def panel(ax, letter: str, dx: float = -0.085, dy: float = 1.06):
    ax.text(dx, dy, letter, transform=ax.transAxes, fontsize=12,
            fontweight="bold", va="top", ha="left", color=INK)


def caption(fig, text: str, y: float = -0.02):
    fig.text(0.5, y, text, ha="center", va="top", fontsize=8,
             color=MUTED, wrap=True)


def save(fig, name: str) -> Path:
    p = FIGDIR / name
    fig.savefig(p, dpi=DPI)
    plt.close(fig)
    print(f"  wrote {name}")
    return p
