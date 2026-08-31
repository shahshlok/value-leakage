"""Shared styling for the four submission figures.

One palette across all four:
  BELOW  (#0072B2, blue)   = below-good / low number shown / against the donation
  ABOVE  (#E69F00, orange) = above-good / high number shown / toward the donation

Colorblind-safe (Okabe-Ito). Sized for a Google Doc column (~650 px).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BELOW = "#0072B2"
ABOVE = "#E69F00"
INK = "#1a1a1a"
MUTED = "#5c5c5c"
FAINT = "#d0d0d0"
RULE = "#8a8a8a"
PAPER = "#f4f4f4"

REPO = Path(__file__).resolve().parents[2]
ANALYSIS = REPO / "analysis"
OUTDIR = REPO / "submission_figures"

MODEL_LABEL = {
    "claude-opus-4-7": "Claude Opus 4.7",
    "deepseek-v4-flash-0731": "DeepSeek Flash",
    "deepseek-v4-pro-0813": "DeepSeek Pro",
    "glm-5p2": "GLM 5.2",
    "inkling-small": "Inkling Small",
    "inkling": "Inkling",
    "kimi-k3": "Kimi K3",
    "minimax-m3": "MiniMax M3",
    "qwen3.5-122b-a10b": "Qwen 3.5",
    "qwen3p8-2p4t-a95b": "Qwen 3.8",
    "qwen/qwen3.5-122b-a10b": "Qwen 3.5",
    "qwen/qwen3.8-2.4t-a95b": "Qwen 3.8",
}


def apply() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 11,
            "axes.labelsize": 10.5,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10.5,
            "axes.edgecolor": RULE,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "text.color": INK,
            "axes.labelcolor": INK,
            "figure.facecolor": "white",
            "savefig.facecolor": "white",
            "legend.frameon": False,
            "svg.fonttype": "none",
        }
    )


def title_block(fig, title: str, subtitle: str, *, y=0.97, gap=0.048, x=0.03) -> None:
    fig.text(x, y, title, fontsize=14.5, fontweight="bold", va="top", ha="left", color=INK)
    fig.text(x, y - gap, subtitle, fontsize=10.4, va="top", ha="left", color=MUTED)


def millions(value: float) -> str:
    m = value / 1e6
    txt = f"{m:.1f}".rstrip("0").rstrip(".")
    return f"{txt}M"


def pct(value: float, digits: int = 1) -> str:
    """Signed percentage with a unicode minus."""
    return f"{value:+.{digits}f}%".replace("-", "\u2212")


def model_name(raw: str) -> str:
    stem = raw.split("_20")[0]
    return MODEL_LABEL.get(raw, MODEL_LABEL.get(stem, stem))


def beeswarm_offsets(values, max_width: float = 0.22, nbins: int = 14) -> np.ndarray:
    """Offsets along the category axis so equal values do not sit on top of each other."""
    arr = np.asarray(list(values), dtype=float)
    n = len(arr)
    offsets = np.zeros(n)
    if n < 2:
        return offsets
    lo, hi = float(np.min(arr)), float(np.max(arr))
    if hi == lo:
        bins = np.zeros(n, dtype=int)
    else:
        edges = np.linspace(lo, hi, nbins + 1)
        bins = np.digitize(arr, edges[1:-1], right=True)
    rng = np.random.default_rng(7)
    for b in np.unique(bins):
        idx = np.where(bins == b)[0]
        k = len(idx)
        if k == 1:
            continue
        spread = np.linspace(-max_width, max_width, k)
        rng.shuffle(spread)
        offsets[idx] = spread
    return offsets


def save(fig, stem: str) -> list[Path]:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext, kwargs in (("png", {"dpi": 220}), ("svg", {})):
        path = OUTDIR / f"{stem}.{ext}"
        fig.savefig(path, **kwargs)
        paths.append(path)
    plt.close(fig)
    return paths
