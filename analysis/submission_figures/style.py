"""Shared styling for the four submission figures.

One palette across all four figures:
  BELOW  (#0072B2, blue)   = below-good condition / low anchor / negative shift
  ABOVE  (#E69F00, orange) = above-good condition / high anchor / positive shift

Colorblind-safe (Okabe-Ito). Figures are sized for ~650 px inline display.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BELOW = "#0072B2"
ABOVE = "#E69F00"
INK = "#1a1a1a"
MUTED = "#5c5c5c"
FAINT = "#b9b9b9"

REPO = Path(__file__).resolve().parents[2]
ANALYSIS = REPO / "analysis"
OUTDIR = REPO / "submission_figures"


def apply() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11.5,
            "axes.titlesize": 11.5,
            "axes.labelsize": 11,
            "xtick.labelsize": 10.5,
            "ytick.labelsize": 11,
            "axes.edgecolor": "#8a8a8a",
            "axes.linewidth": 0.9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "text.color": INK,
            "axes.labelcolor": INK,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "legend.frameon": False,
        }
    )


def title_block(fig, title: str, subtitle: str, *, y=0.975, gap=0.052, x=0.012) -> None:
    fig.text(x, y, title, fontsize=15.5, fontweight="bold", va="top", ha="left", color=INK)
    fig.text(x, y - gap, subtitle, fontsize=10.8, va="top", ha="left", color=MUTED)


def millions(value: float) -> str:
    m = value / 1e6
    txt = f"{m:.1f}".rstrip("0").rstrip(".")
    return f"{txt}M"


def save(fig, stem: str) -> list[Path]:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext, kwargs in (("png", {"dpi": 220}), ("svg", {})):
        path = OUTDIR / f"{stem}.{ext}"
        fig.savefig(path, **kwargs)
        paths.append(path)
    plt.close(fig)
    return paths
