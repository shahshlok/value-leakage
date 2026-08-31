"""Figure 1 (H1): a morally inert cutoff still moves the estimate.

Source: analysis/hyp1_threshold_anchoring/results.json
  - cell_summaries, universe "all_400_exploratory" -> per-cell median answers
  - confirmatory_primary / prespecified_secondary -> locked holdout shifts + CIs
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt

import style
from style import ABOVE, BELOW, FAINT, INK, MUTED, millions

RESULTS = style.ANALYSIS / "hyp1_threshold_anchoring" / "results.json"

FRAMING_LABEL = {
    "neutral_boundary": "Bookkeeping boundary",
    "irrelevant_number": "Irrelevant number",
}
MODEL_LABEL = {
    "qwen/qwen3.5-122b-a10b": "Qwen 3.5",
    "qwen/qwen3.8-2.4t-a95b": "Qwen 3.8",
}
ORDER = [
    ("neutral_boundary", "qwen/qwen3.5-122b-a10b"),
    ("neutral_boundary", "qwen/qwen3.8-2.4t-a95b"),
    ("irrelevant_number", "qwen/qwen3.5-122b-a10b"),
    ("irrelevant_number", "qwen/qwen3.8-2.4t-a95b"),
]


def load():
    data = json.loads(RESULTS.read_text())
    cells = {}
    for row in data["cell_summaries"]:
        if row["universe"] != "all_400_exploratory":
            continue
        cells[(row["framing"], row["model"], row["anchor"])] = row
    rows = []
    for framing, model in ORDER:
        anchors = sorted(a for (f, m, a) in cells if f == framing and m == model)
        low, high = anchors
        rows.append(
            {
                "framing": framing,
                "model": model,
                "anchor_low": low,
                "anchor_high": high,
                "median_low": cells[(framing, model, low)]["median"],
                "median_high": cells[(framing, model, high)]["median"],
                "n": cells[(framing, model, low)]["n"] + cells[(framing, model, high)]["n"],
            }
        )
    holdout = {
        "neutral_boundary": data["confirmatory_primary"],
        "irrelevant_number": data["prespecified_secondary"],
    }
    return rows, holdout


def plot() -> None:
    style.apply()
    rows, holdout = load()

    fig = plt.figure(figsize=(8.6, 4.95))
    ax = fig.add_axes([0.335, 0.375, 0.505, 0.395])

    ys = [3, 2, 1, 0]
    for y, row in zip(ys, rows):
        lo, hi = row["median_low"] / 1e6, row["median_high"] / 1e6
        ax.annotate(
            "",
            xy=(hi, y),
            xytext=(lo, y),
            arrowprops=dict(arrowstyle="-|>,head_width=0.22,head_length=0.5",
                            color="#9a9a9a", lw=2.2, shrinkA=7, shrinkB=6),
        )
        ax.plot([lo], [y], "o", ms=11, color=BELOW, zorder=3)
        ax.plot([hi], [y], "o", ms=11, color=ABOVE, zorder=3)
        crowded = (hi - lo) < 4.0
        ax.text(lo, y - 0.34 if crowded else y + 0.28, millions(row["median_low"]),
                ha="center", va="top" if crowded else "bottom",
                fontsize=10.5, color=BELOW, fontweight="bold")
        ax.text(hi, y + 0.28, millions(row["median_high"]), ha="center", va="bottom",
                fontsize=10.5, color=ABOVE, fontweight="bold")
        pct = row["median_high"] / row["median_low"] - 1.0
        ax.text(1.035, y, f"+{pct * 100:.0f}%", transform=ax.get_yaxis_transform(),
                ha="left", va="center", fontsize=12, fontweight="bold", color=INK)

    labels = []
    for row in rows:
        labels.append(
            f"{FRAMING_LABEL[row['framing']]} · {MODEL_LABEL[row['model']]}\n"
            f"number shown:  {millions(row['anchor_low'])}  →  {millions(row['anchor_high'])}"
        )
    ax.set_yticks(ys)
    ax.set_yticklabels(labels, fontsize=9.9, linespacing=1.5, color=INK)
    for tick in ax.get_yticklabels():
        tick.set_horizontalalignment("left")
    ax.tick_params(axis="y", length=0, pad=198)

    ax.set_ylim(-0.72, 3.78)
    ax.set_xlim(19, 58)
    ax.set_xticks([20, 30, 40, 50])
    ax.set_xticklabels(["20M", "30M", "40M", "50M"])
    ax.set_xlabel("Median answer (spots, all 400 responses)", fontsize=10.8, labelpad=7)
    ax.spines["left"].set_visible(False)
    for x in (20, 30, 40, 50):
        ax.axvline(x, color=FAINT, lw=0.7, zorder=0)

    ax.plot([0.01], [1.075], "o", ms=9, color=BELOW, transform=ax.transAxes, clip_on=False)
    ax.text(0.05, 1.075, "at the low number", transform=ax.transAxes, fontsize=10.2,
            color=BELOW, fontweight="bold", ha="left", va="center")
    ax.plot([0.53], [1.075], "o", ms=9, color=ABOVE, transform=ax.transAxes, clip_on=False)
    ax.text(0.57, 1.075, "at the high number", transform=ax.transAxes, fontsize=10.2,
            color=ABOVE, fontweight="bold", ha="left", va="center")
    ax.text(1.035, 1.075, "change", transform=ax.transAxes, fontsize=10.2,
            color=MUTED, ha="left", va="center")

    style.title_block(
        fig,
        "A number with no consequences still moves the estimate",
        "The prompt states the cutoff is arbitrary and carries no reward, no penalty and no preferred side.\n"
        "Doubling it still raises the answer in every cell.",
        y=0.985,
        gap=0.058,
    )

    prim = holdout["neutral_boundary"]
    sec = holdout["irrelevant_number"]

    def band(entry):
        lo, hi = entry["bootstrap"]["exp_theta_minus_1_ci_95_percentile"]
        return (f"+{entry['exp_theta_minus_1'] * 100:.1f}%  "
                f"[{lo * 100:.1f}, {hi * 100:.1f}]")

    fig.text(
        0.012, 0.205,
        "Locked holdout test, both models pooled, equal weight\n"
        f"bookkeeping boundary  {band(prim)}          irrelevant number  {band(sec)}",
        fontsize=10.0, color=INK, va="top", ha="left", linespacing=1.55,
    )
    fig.text(
        0.012, 0.075,
        "The analysis plan was frozen and its hash published before the 360 holdout responses were opened.\n"
        "95% bootstrap intervals; Holm-corrected p = 0.002 and 0.005.",
        fontsize=8.8, color=MUTED, va="top", ha="left", linespacing=1.5,
    )

    for path in style.save(fig, "fig1_anchoring"):
        print(path)


if __name__ == "__main__":
    plot()
