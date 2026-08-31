"""Plot the Qwen 3.5 answer distributions from the saved H6 table."""
from __future__ import annotations

import csv
import random
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "hyp6_impartiality" / "existing_data" / "outcomes_and_claims.csv"
OUT = HERE / "outputs"
MODEL_PREFIX = "qwen3.5-122b-a10b_"
THRESHOLD = 41_000_000.0
COLORS = {"below_good": "#0072B2", "above_good": "#E69F00"}
MARKERS = {"below_good": "o", "above_good": "^"}
LINESTYLES = {"below_good": "-", "above_good": "--"}


def load_data() -> dict[str, list[float]]:
    with SOURCE.open(newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["model_dir"].startswith(MODEL_PREFIX)
            and row["condition"] in COLORS
        ]

    assert len(rows) == 100, f"Expected 100 Qwen rows, found {len(rows)}"
    assert all(row["estimate"].strip() for row in rows), "Unexpected missing Qwen estimate"
    assert all(float(row["threshold"]) == THRESHOLD for row in rows)
    assert all(row["impartiality_commitment"] == "True" for row in rows)

    values = {
        condition: [float(row["estimate"]) for row in rows if row["condition"] == condition]
        for condition in COLORS
    }
    assert all(len(group) == 50 for group in values.values())
    return values


def plot() -> None:
    values = load_data()
    below, above = values["below_good"], values["above_good"]
    medians = {key: statistics.median(group) for key, group in values.items()}
    crossings = {key: sum(value > THRESHOLD for value in group) for key, group in values.items()}
    assert medians == {"below_good": 38_000_000.0, "above_good": 44_000_000.0}
    assert crossings == {"below_good": 7, "above_good": 33}

    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
        }
    )
    fig, ax = plt.subplots(figsize=(11.2, 6.4))
    rng = random.Random(46062032)
    bands = {"below_good": 0.0, "above_good": 1.0}

    for condition, group in values.items():
        center = bands[condition]
        jitter = [center + rng.uniform(-0.16, 0.16) for _ in group]
        ax.scatter(
            group,
            jitter,
            s=34,
            color=COLORS[condition],
            marker=MARKERS[condition],
            alpha=0.78,
            edgecolor="#000000",
            linewidth=0.35,
            zorder=3,
        )
        median = medians[condition]
        ax.plot(
            [median, median],
            [center - 0.27, center + 0.27],
            color=COLORS[condition],
            lw=3.2,
            linestyle=LINESTYLES[condition],
            solid_capstyle="round",
            zorder=4,
        )

    ax.axvline(THRESHOLD, color="#000000", lw=1.2, ls="--", zorder=2)
    ax.annotate(
        "threshold (41M): above benefits good cause in one condition,\n"
        "below in the mirrored one",
        xy=(THRESHOLD, 1.32),
        xytext=(7, 0),
        textcoords="offset points",
        ha="left",
        va="center",
        fontsize=9.2,
        color="#000000",
        bbox={"boxstyle": "round,pad=.25", "facecolor": "white", "edgecolor": "none", "alpha": 0.93},
    )

    ax.set_xscale("log")
    ticks = [10e6, 20e6, 40e6, 80e6, 160e6, 320e6]
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1e6:g}M"))
    ax.set_xlim(9.5e6, 520e6)
    ax.set_ylim(-0.48, 1.52)
    ax.set_yticks(
        [bands["below_good"], bands["above_good"]],
        [
            "Below-good condition\nmedian 38M  ·  7/50 above threshold",
            "Above-good condition\nmedian 44M  ·  33/50 above threshold",
        ],
    )
    ax.set_xlabel("Answer estimate (millions; log scale)")
    ax.grid(axis="x", which="major", color="#000000", alpha=0.15)
    ax.grid(axis="y", color="#000000", alpha=0.08, lw=1)
    ax.set_title(
        "Qwen 3.5: answers straddle the threshold by incentive direction",
        fontsize=15,
        pad=16,
    )
    fig.text(
        0.02,
        0.025,
        "All 100 traces carry judge-labeled impartiality commitments.",
        fontsize=9,
        color="#000000",
    )
    fig.tight_layout(rect=[0, 0.07, 1, 1])
    OUT.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "svg"):
        fig.savefig(OUT / f"qwen35_distribution.{extension}", dpi=180)
    plt.close(fig)


if __name__ == "__main__":
    plot()
