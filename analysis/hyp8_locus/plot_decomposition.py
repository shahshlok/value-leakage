"""Plot the primary nine-model H8 decomposition from saved results."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "decomposition_results.json"
OUT = HERE / "decomposition_figure"


def signed(value: float) -> str:
    """Format one-decimal percentages with typographic signs."""
    return f"{value:+.1f}".replace("-", "−")


def plot() -> None:
    results = json.loads(SOURCE.read_text())
    components = results["decomposition"]["primary_9"]["components"]
    full_effect = results["full_sample_reference"]["geometric_shift_pct"]
    audit_error = results["audit_summary"]["error_rate"]

    rows = [
        ("Population  Δln N", "ln_N", "#0072B2", "o"),
        ("Spots per giraffe  Δln S", "ln_S", "#E69F00", "s"),
        ("Final-adjustment residual", "ln_residual", "#CC79A7", "^"),
        ("Gated total  Δln Y", "ln_Y", "#000000", "D"),
    ]
    assert len(results["decomposition"]["primary_9"]["models"]) == 9
    assert audit_error == 0.25
    assert full_effect == 15.5

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
        }
    )
    fig, ax = plt.subplots(figsize=(11.2, 6.0))
    positions = list(reversed(range(len(rows))))

    for y, (label, key, color, marker) in zip(positions, rows):
        row = components[key]
        point = row["geometric_shift_pct"]
        low = row["geometric_ci95_low_pct"]
        high = row["geometric_ci95_high_pct"]
        ax.errorbar(
            point,
            y,
            xerr=[[point - low], [high - point]],
            fmt=marker,
            color=color,
            markeredgecolor="#000000",
            markeredgewidth=0.5,
            markersize=7.5,
            elinewidth=2.1,
            capsize=3,
            zorder=3,
        )
        annotation = f"{signed(point)}%  [{signed(low)}, {signed(high)}]"
        ax.text(high + 0.55, y, annotation, va="center", ha="left", fontsize=9.5, color="#000000")

    ax.axvline(0, color="#000000", alpha=.55, lw=1.1, ls="--", zorder=1)
    ax.set_yticks(positions, [label for label, _, _, _ in rows])
    ax.set_ylim(-0.65, 3.65)
    ax.set_xlim(-5.2, 20.5)
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.set_xlabel("Above-good / below-good geometric mean − 1 (%)")
    ax.grid(axis="x", color="#000000", alpha=0.15)
    ax.grid(axis="y", color="#000000", alpha=0.08, lw=1)
    ax.set_title(
        "Where the shift enters: the unconstrained factor absorbs it",
        fontsize=15,
        pad=16,
    )
    fig.text(
        0.02,
        0.026,
        "Exploratory: 25% extraction-audit error rate; condition-imbalanced gate attrition; "
        "gated subset carries +10.1% of the full +15.5% effect.",
        fontsize=9.2,
        color="#D55E00",
        weight="bold",
    )
    fig.text(
        0.02,
        0.058,
        "Equal-weight primary nine models; 10,000 within-model × condition bootstraps; marginal 95% intervals.",
        fontsize=8.8,
        color="#000000",
    )
    fig.tight_layout(rect=[0, 0.11, 1, 1])
    for extension in ("png", "svg"):
        fig.savefig(OUT.with_suffix(f".{extension}"), dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    plot()
