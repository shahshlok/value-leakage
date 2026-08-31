"""Figure 3 (H3): answers move with the donation, and the impartiality promise does not stop it.

Sources:
  analysis/hyp7_impartiality_dissociation/outputs/h7_outcomes.csv
      -> the 100 Qwen 3.5 answers, their condition, threshold and impartiality label
  analysis/hyp7_impartiality_dissociation/outputs/contrasts.csv
      -> pooled nine-model log contrast, all traces vs label-positive traces
  analysis/hyp7_impartiality_dissociation/outputs/bootstrap_summary.json
      -> paired within-replicate difference between the two
"""
from __future__ import annotations

import csv
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, NullFormatter

import style
from style import ABOVE, BELOW, INK, MUTED

OUT = style.ANALYSIS / "hyp7_impartiality_dissociation" / "outputs"
MODEL_PREFIX = "qwen3.5-122b-a10b_"


def load_qwen():
    rows = [
        row
        for row in csv.DictReader((OUT / "h7_outcomes.csv").open(newline=""))
        if row["model_dir"].startswith(MODEL_PREFIX)
    ]
    assert len(rows) == 100
    assert {row["claim"] for row in rows} == {"True"}
    thresholds = {float(row["threshold"]) for row in rows}
    assert len(thresholds) == 1
    values = {
        cond: [float(row["estimate"]) for row in rows if row["condition"] == cond]
        for cond in ("below_good", "above_good")
    }
    assert all(len(v) == 50 for v in values.values())
    return values, thresholds.pop()


def load_pooled():
    contrasts = {}
    for row in csv.DictReader((OUT / "contrasts.csv").open(newline="")):
        if (row["dataset"] == "h6_corrected" and row["tier"] == "primary_9"
                and row["metric"] == "log"):
            contrasts[row["stratum"]] = row
    paired = json.loads((OUT / "bootstrap_summary.json").read_text())[
        "paired_diff_base_minus_labelpos"
    ]["percentage_points"]
    return contrasts, paired


def plot() -> None:
    style.apply()
    values, threshold = load_qwen()
    contrasts, paired = load_pooled()

    fig = plt.figure(figsize=(9.2, 5.2))
    axl = fig.add_axes([0.245, 0.375, 0.365, 0.285])
    axr = fig.add_axes([0.725, 0.375, 0.245, 0.285])

    # ---------------- left: every Qwen 3.5 answer ----------------
    rng = random.Random(7)
    for cond, y, colour in (("above_good", 1, ABOVE), ("below_good", 0, BELOW)):
        vals = values[cond]
        jitter = [y + rng.uniform(-0.15, 0.15) for _ in vals]
        axl.scatter(vals, jitter, s=30, facecolor=colour, edgecolor="white",
                    linewidth=0.6, alpha=0.92, zorder=3)
        med = statistics.median(vals)
        axl.plot([med, med], [y - 0.27, y + 0.27], color=INK, lw=3.0, zorder=4,
                 solid_capstyle="butt")
        axl.text(med, y + 0.31, f"median {style.millions(med)}", ha="center", va="bottom",
                 fontsize=10.0, fontweight="bold", color=INK)
        n_above = sum(1 for v in vals if v > threshold)
        axl.text(1.015, y, f"{n_above} of 50\nabove", transform=axl.get_yaxis_transform(),
                 ha="left", va="center", fontsize=10.2, fontweight="bold", color=colour,
                 linespacing=1.3)

    axl.axvline(threshold, color="#6f6f6f", lw=1.3, ls=(0, (4, 3)), zorder=2)
    axl.text(threshold, 1.72, f"cutoff {style.millions(threshold)}", ha="center", va="bottom",
             fontsize=10.0, color="#4a4a4a")

    axl.set_xscale("log")
    axl.set_xlim(9e6, 6e8)
    axl.xaxis.set_major_locator(FixedLocator([1e7, 2e7, 5e7, 1e8, 2e8, 5e8]))
    axl.set_xticklabels(["10M", "20M", "50M", "100M", "200M", "500M"])
    axl.xaxis.set_minor_formatter(NullFormatter())
    axl.set_ylim(-0.58, 1.70)
    axl.set_yticks([1, 0])
    axl.set_yticklabels(
        ["going above the cutoff\nHELPS the good cause",
         "going above the cutoff\nHURTS the good cause"],
        fontsize=9.9, linespacing=1.4,
    )
    for label, colour in zip(axl.get_yticklabels(), [ABOVE, BELOW]):
        label.set_color(colour)
        label.set_fontweight("bold")
    axl.tick_params(axis="y", length=0, pad=8)
    axl.spines["left"].set_visible(False)
    axl.set_xlabel("Estimated total giraffe spots, log scale · one dot per answer",
                   fontsize=10.0, labelpad=6)

    fig.text(0.045, 0.735, "Qwen 3.5: same question, same number on screen, opposite recipient",
             fontsize=10.9, color=INK, ha="left", va="bottom")
    fig.text(0.045, 0.235,
             "All 100 of these traces were labelled as explicitly promising impartiality.",
             fontsize=9.8, color=INK, ha="left", va="top", fontweight="bold")

    # ---------------- right: pooled shift, all vs promised ----------------
    entries = [("all", "all traces", 1),
               ("positive", "traces promising impartiality", 0)]
    axr.axvline(0, color="#9a9a9a", lw=1.0)
    for stratum, label, y in entries:
        row = contrasts[stratum]
        est = float(row["geometric_shift_pct"])
        lo = float(row["geometric_ci95_low_pct"])
        hi = float(row["geometric_ci95_high_pct"])
        axr.plot([lo, hi], [y, y], color=ABOVE, lw=6.0, solid_capstyle="round", zorder=3)
        axr.plot([est], [y], "o", ms=10, color=ABOVE, markeredgecolor="white",
                 markeredgewidth=1.3, zorder=4)
        axr.text(-2.5, y + 0.32, label, ha="left", va="bottom", fontsize=9.9,
                 color=MUTED, linespacing=1.35)
        axr.text(est, y - 0.24, f"$\\bf{{+{est:.1f}\\%}}$   [{lo:.1f}, {hi:.1f}]",
                 ha="center", va="top", fontsize=10.4, color=INK)

    axr.set_xlim(-3, 27)
    axr.set_ylim(-0.58, 1.70)
    axr.set_yticks([])
    axr.spines["left"].set_visible(False)
    axr.set_xticks([0, 10, 20])
    axr.set_xticklabels(["0", "+10%", "+20%"])
    axr.set_xlabel("Shift when going above the cutoff\nhelps the good cause",
                   fontsize=10.0, labelpad=6, linespacing=1.35)

    fig.text(0.66, 0.735, "Nine models pooled, equal weight", fontsize=10.9, color=INK,
             ha="left", va="bottom")
    fig.text(0.66, 0.235,
             "Filtering on the promise moves the shift\n"
             f"by {paired['estimate']:.1f} pp "
             f"[{paired['ci95_low']:.1f}, {paired['ci95_high']:.1f}].".replace("-", "\u2212"),
             fontsize=9.8, color=INK, ha="left", va="top", fontweight="bold",
             linespacing=1.45)

    style.title_block(
        fig,
        "Answers move with the donation, and the promise does not stop it",
        "The cutoff is numerically identical in both conditions. Only which side helps the good cause changes.",
        y=0.975,
        gap=0.052,
    )

    fig.text(
        0.012, 0.145,
        "Nine models, 753 usable answers; DeepSeek Pro excluded before pooling for excessive data loss. Equal weight per model,\n"
        "log scale, 10,000 bootstrap replicates, and the paired difference computed inside the same replicates. 76% of traces carry\n"
        "the promise, so the filter removes little of the sample: this is a failure to detect a difference, not a demonstration that none exists.",
        fontsize=8.6, color=MUTED, va="top", ha="left", linespacing=1.5,
    )

    for path in style.save(fig, "fig3_headline_dissociation"):
        print(path)


if __name__ == "__main__":
    plot()
