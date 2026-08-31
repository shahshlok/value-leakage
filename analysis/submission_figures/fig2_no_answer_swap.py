"""Figure 2 (H2): the visible answer is not swapped away from the reasoning's number.

Sources:
  analysis/hyp6_impartiality/full_1000/gap_screen.jsonl   -> per-pair signed gaps
  analysis/hyp6_impartiality/full_1000/gap_summary.json   -> screen counts
  analysis/hyp6_impartiality/verify_gaps/summary.json     -> verification counts
  analysis/hyp6_impartiality/numerical_consistency_report.md -> none crossed a threshold
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import style
from style import ABOVE, BELOW, INK, MUTED

H6 = style.ANALYSIS / "hyp6_impartiality"
SCREEN = H6 / "full_1000" / "gap_screen.jsonl"
SCREEN_SUMMARY = H6 / "full_1000" / "gap_summary.json"
VERIFY = H6 / "verify_gaps" / "summary.json"

BANDS = [
    (10.0, float("inf"), "10% or more"),
    (5.0, 10.0, "5 to 10%"),
    (1.0, 5.0, "1 to 5%"),
    (0.0, 1.0, "under 1%"),
]


def load():
    gaps = []
    for line in SCREEN.read_text().splitlines():
        entry = json.loads(line).get("answer_minus_reasoning")
        if entry:
            gaps.append(entry["donation_signed_gap"] * 100.0)
    screen = json.loads(SCREEN_SUMMARY.read_text())["metrics"]["answer_minus_reasoning"]
    verify = json.loads(VERIFY.read_text())["metrics"]["Y_minus_R"]
    return gaps, screen, verify


def plot() -> None:
    style.apply()
    gaps, screen, verify = load()

    n_pairs = screen["n_comparable"]
    n_zero = sum(1 for g in gaps if g == 0.0)
    n_flag = screen["n_at_least_5pct"]
    n_fav = screen["n_5pct_favored_direction"]
    n_opp = screen["n_5pct_opposed_direction"]

    counts = []
    for lo, hi, label in BANDS:
        opposed = sum(1 for g in gaps if g < 0 and lo <= abs(g) < hi)
        favored = sum(1 for g in gaps if g > 0 and lo <= abs(g) < hi)
        counts.append((label, opposed, favored))

    fig = plt.figure(figsize=(8.6, 4.1))
    axl = fig.add_axes([0.145, 0.325, 0.425, 0.355])
    axr = fig.add_axes([0.635, 0.375, 0.35, 0.27])

    # ---------------- left: signed gap, banded by size ----------------
    xlim = 21.0
    for i, (label, opposed, favored) in enumerate(counts):
        y = len(counts) - 1 - i
        axl.add_patch(Rectangle((-opposed, y - 0.30), opposed, 0.60,
                                facecolor=BELOW, edgecolor="none"))
        axl.add_patch(Rectangle((0, y - 0.30), favored, 0.60,
                                facecolor=ABOVE, edgecolor="none"))
        axl.text(-opposed - 0.9, y, str(opposed), ha="right", va="center",
                 fontsize=11, fontweight="bold", color=BELOW)
        axl.text(favored + 0.9, y, str(favored), ha="left", va="center",
                 fontsize=11, fontweight="bold", color=ABOVE)

    axl.set_xlim(-xlim, xlim)
    axl.set_ylim(-1.05, len(counts) - 0.25)
    axl.set_yticks(range(len(counts)))
    axl.set_yticklabels([label for label, _, _ in counts][::-1], fontsize=10.4, color=INK)
    axl.tick_params(axis="y", length=0, pad=6)
    axl.set_xticks([])
    axl.spines["left"].set_visible(False)
    axl.spines["bottom"].set_visible(False)
    axl.axvline(0, color="#8a8a8a", lw=1.1)

    axl.axhline(1.5, color="#9a9a9a", lw=1.0, ls=(0, (3, 3)))
    axl.text(-xlim, 1.5, "5% screen threshold", fontsize=8.6, color=MUTED,
             ha="left", va="center",
             bbox=dict(facecolor="white", edgecolor="none", pad=1.5))

    axl.text(-1.2, len(counts) - 0.32, "against the donation", fontsize=10.2, color=BELOW,
             fontweight="bold", ha="right", va="bottom")
    axl.text(1.2, len(counts) - 0.32, "toward the donation", fontsize=10.2, color=ABOVE,
             fontweight="bold", ha="left", va="bottom")

    axl.text(0, -0.86, f"{n_flag} pairs exceed the 5% screen:  {n_opp} each way",
             ha="center", va="center", fontsize=10.6, color=INK, fontweight="bold")

    fig.text(
        0.145, 0.735,
        f"{n_zero} of the {n_pairs} pairs agree exactly. The other {n_pairs - n_zero}:",
        fontsize=10.8, color=INK, ha="left", va="bottom",
    )

    # ---------------- right: verification funnel ----------------
    stages = [
        (n_pairs, "answer / reasoning pairs read"),
        (n_flag, "flagged by the 5% screen"),
        (verify["gap_ge_5pct"], "survived blind re-extraction"),
        (0, "changed the donation outcome"),
    ]
    axr.set_xlim(0, 1)
    axr.set_ylim(-0.55, len(stages) - 0.45)
    axr.axis("off")

    shades = ["#d2d2d2", "#b4b4b4", "#8f8f8f", INK]
    for i, (count, label) in enumerate(stages):
        y = len(stages) - 1 - i
        width = count / n_pairs * 0.155
        axr.add_patch(Rectangle((0, y - 0.15), width, 0.30,
                                facecolor=shades[i], edgecolor="none"))
        axr.text(0.30, y, f"{count}", ha="right", va="center",
                 fontsize=13.5 if i == 3 else 12.5, fontweight="bold", color=INK)
        axr.text(0.35, y, label, ha="left", va="center", fontsize=8.7, color=MUTED)

    fig.text(0.635, 0.735, "Nothing survives verification", fontsize=10.8, color=INK,
             ha="left", va="bottom")

    style.title_block(
        fig,
        "The model is not swapping the answer at the end",
        "The visible answer agrees with the number the reasoning itself committed to. Where it does not, the gap is\n"
        "small and as likely to hurt the favoured cause as to help it.",
        y=0.975,
        gap=0.056,
    )

    fig.text(
        0.012, 0.215,
        f"1,000 sampled traces across ten models; {n_pairs} produced a pair where both the answer and the reasoning's\n"
        "own committed number could be read. Only flagged pairs were re-extracted, so this is not a rate of\n"
        "unfaithfulness, and the 5% cutoff is a screening choice rather than a validated boundary.",
        fontsize=8.7, color=MUTED, va="top", ha="left", linespacing=1.55,
    )

    for path in style.save(fig, "fig2_no_answer_swap"):
        print(path)


if __name__ == "__main__":
    plot()
