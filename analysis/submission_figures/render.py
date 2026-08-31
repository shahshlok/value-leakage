"""Build the four submission figures as SVG, then rasterize to PNG via Chrome.

    uv run python analysis/submission_figures/render.py
"""
from __future__ import annotations

import csv
import json
import math
import statistics
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from svgdraw import ABOVE, BELOW, FAINT, INK, MUTED, RULE, Svg
import style

HERE = Path(__file__).resolve().parent
OUT = style.OUTDIR
CHROME = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SCALE = 2

MODEL_LABEL = style.MODEL_LABEL


def millions(value: float) -> str:
    return style.millions(value)


def pct(value: float, digits: int = 1) -> str:
    return style.pct(value, digits)


def model_name(raw: str) -> str:
    return style.model_name(raw)


def title_block(svg: Svg, title: str, subtitle: str, *, x=28, y=22) -> None:
    svg.text(x, y, title, size=20, weight=700, baseline="hanging")
    svg.text(x, y + 30, subtitle, size=13, fill=MUTED, baseline="hanging")


def rasterize(svg_path: Path, png_path: Path, width: int, height: int) -> None:
    """Chrome headless screenshot at SCALE, then the PNG matches the SVG layout."""
    scaled_w, scaled_h = width * SCALE, height * SCALE
    html = (
        "<!doctype html><meta charset='utf-8'>"
        "<style>html,body{margin:0;background:#fff;overflow:hidden}</style>"
        f"<img src='{svg_path.name}' width='{scaled_w}' height='{scaled_h}' "
        f"style='display:block;width:{scaled_w}px;height:{scaled_h}px'>"
    )
    html_path = svg_path.with_suffix(".raster.html")
    html_path.write_text(html)
    subprocess.run(
        [
            str(CHROME),
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            "--default-background-color=ffffffff",
            f"--screenshot={png_path}",
            f"--window-size={scaled_w},{scaled_h}",
            html_path.resolve().as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    html_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# H1
# ---------------------------------------------------------------------------

def load_h1():
    estimates = style.ANALYSIS / "hyp1_threshold_anchoring" / "final_estimates.csv"
    results = json.loads(
        (style.ANALYSIS / "hyp1_threshold_anchoring" / "results.json").read_text()
    )
    rows = [
        r for r in csv.DictReader(estimates.open())
        if r["split"] == "holdout" and r["condition"] == "neutral_boundary" and r["final_estimate"]
    ]
    cells = {}
    for model in ("qwen/qwen3.5-122b-a10b", "qwen/qwen3.8-2.4t-a95b"):
        sub = [r for r in rows if r["model"] == model]
        anchors = sorted({int(r["anchor"]) for r in sub})
        cells[model] = {
            "anchors": anchors,
            "values": {
                a: [float(r["final_estimate"]) / 1e6 for r in sub if int(r["anchor"]) == a]
                for a in anchors
            },
        }
    return cells, results["confirmatory_primary"], results["prespecified_secondary"]


def fig1() -> tuple[Path, int, int]:
    cells, primary, _secondary = load_h1()
    w, h = 860, 545
    svg = Svg(w, h)
    lo, hi = (x * 100 for x in primary["bootstrap"]["exp_theta_minus_1_ci_95_percentile"])
    svg.text(28, 18, "A number with no consequences still moves the estimate",
             size=20, weight=700, baseline="hanging")
    svg.text(
        28, 46,
        f"Pooled locked holdout, bookkeeping framing (what the panels show): "
        f"{pct(primary['exp_theta_minus_1'] * 100)}  [{lo:.1f}, {hi:.1f}].",
        size=12.5, fill=MUTED, baseline="hanging",
    )
    svg.text(
        28, 64,
        "Each cloud is 45 answers. Black bars are that column's median, not the pooled test.",
        size=12.5, fill=MUTED, baseline="hanging",
    )

    panels = [
        ("qwen/qwen3.5-122b-a10b", "Qwen 3.5", 28, 10.0, 92.0),
        ("qwen/qwen3.8-2.4t-a95b", "Qwen 3.8", 454, 8.0, 54.0),
    ]
    plot_top, plot_bot = 118, 448
    plot_h = plot_bot - plot_top
    plot_w = 378

    def y_of(val, vmin, vmax):
        return plot_bot - (val - vmin) / (vmax - vmin) * plot_h

    for model, label, x0, vmin, vmax in panels:
        cell = cells[model]
        low_a, high_a = cell["anchors"]
        cols = [
            (x0 + 118, cell["values"][low_a], low_a / 1e6, BELOW),
            (x0 + 270, cell["values"][high_a], high_a / 1e6, ABOVE),
        ]
        svg.text(x0 + plot_w / 2, 94, label, size=15, weight=700, anchor="middle")

        for tick in _nice_ticks(vmin, vmax):
            y = y_of(tick, vmin, vmax)
            svg.line(x0 + 52, y, x0 + plot_w, y, stroke=FAINT, sw=0.8)
            svg.text(x0 + 46, y, f"{tick:g}", size=11, fill=MUTED, anchor="end",
                     baseline="middle")

        clip_counts = []
        svg.clip_start(f"p{abs(hash(model)) % 10**6}", x0 + 52, plot_top, plot_w - 52, plot_h)
        for cx, vals, shown, colour in cols:
            n_hi = sum(v > vmax for v in vals)
            n_lo = sum(v < vmin for v in vals)
            clip_counts.append((n_lo, n_hi, colour))
            if vmin < shown < vmax:
                svg.line(cx - 48, y_of(shown, vmin, vmax), cx + 48,
                         y_of(shown, vmin, vmax), stroke=RULE, sw=1.2, dash="4 3")
            clipped = [min(max(v, vmin), vmax) for v in vals]
            off = style.beeswarm_offsets(clipped, max_width=14, nbins=18)
            for v, dx in zip(clipped, off):
                svg.circle(cx + float(dx), y_of(v, vmin, vmax), 3.4,
                           fill=colour, stroke="white", sw=0.5)
            med = statistics.median(vals)
            my = y_of(min(max(med, vmin), vmax), vmin, vmax)
            svg.line(cx - 22, my, cx + 22, my, stroke=INK, sw=2.6, cap="butt")
        svg.clip_end()

        for cx, vals, shown, colour in cols:
            med = statistics.median(vals)
            svg.text(cx, plot_bot + 16, f"shown {millions(shown * 1e6)}",
                     size=12, fill=MUTED, anchor="middle")
            svg.text(cx, plot_bot + 34, f"median {millions(med * 1e6)}",
                     size=12, weight=700, fill=INK, anchor="middle")

        svg.nodes.append(
            f'<text x="{x0 + 14:.2f}" y="{(plot_top + plot_bot) / 2:.2f}" fill="{MUTED}"'
            f' font-size="11" font-weight="400" font-family="Helvetica Neue, Helvetica, Arial, sans-serif"'
            f' text-anchor="middle" dominant-baseline="middle"'
            f' transform="rotate(-90 {x0 + 14:.2f} {(plot_top + plot_bot) / 2:.2f})">'
            f"Answer, millions of spots</text>"
        )
        n_off = sum(a + b for a, b, _ in clip_counts)
        if n_off:
            svg.text(x0 + plot_w, plot_top + 2,
                     f"{n_off} answers above {vmax:g}M in this panel",
                     size=10, fill=MUTED, anchor="end", baseline="hanging")

    svg.circle(28, 522, 5, fill=BELOW, stroke="white")
    svg.text(38, 522, "low number shown", size=12, fill=BELOW, weight=700, baseline="middle")
    svg.circle(188, 522, 5, fill=ABOVE, stroke="white")
    svg.text(198, 522, "high number shown", size=12, fill=ABOVE, weight=700, baseline="middle")
    svg.line(368, 522, 398, 522, stroke=RULE, sw=1.3, dash="4 3")
    svg.text(406, 522, "number on screen", size=12, fill=MUTED, baseline="middle")

    path = OUT / "fig1_anchoring.svg"
    svg.write(path)
    return path, w, h


def _nice_ticks(vmin, vmax):
    span = vmax - vmin
    step = 20 if span > 50 else 10
    start = math.ceil(vmin / step) * step
    ticks = list(range(int(start), int(vmax) + 1, step))
    return ticks or [int(vmin), int(vmax)]


# ---------------------------------------------------------------------------
# H2
# ---------------------------------------------------------------------------

def load_h2():
    h6 = style.ANALYSIS / "hyp6_impartiality"
    pairs = []
    for line in (h6 / "full_1000" / "gap_screen.jsonl").read_text().splitlines():
        entry = json.loads(line)
        amr = entry.get("answer_minus_reasoning")
        if not amr:
            continue
        pairs.append(
            {
                "id": entry["trace_id"],
                "y": float(entry["visible_answer"]),
                "r": float(entry["reasoning_conclusion"]),
                "signed": amr["donation_signed_gap"],
                "flag": bool(amr["at_least_5pct"]),
            }
        )
    screen = json.loads((h6 / "full_1000" / "gap_summary.json").read_text())[
        "metrics"
    ]["answer_minus_reasoning"]
    verify = json.loads((h6 / "verify_gaps" / "summary.json").read_text())[
        "metrics"
    ]["Y_minus_R"]
    return pairs, screen, set(verify["trace_ids_ge_5pct"])


def fig2() -> tuple[Path, int, int]:
    pairs, screen, verified = load_h2()
    w, h = 780, 650
    svg = Svg(w, h)
    svg.text(28, 22, "The answer is the number the reasoning already committed to",
             size=18, weight=700, baseline="hanging")
    svg.text(
        28, 52,
        "A last-second swap toward the donation would lift points off this diagonal.",
        size=13, fill=MUTED, baseline="hanging",
    )
    svg.text(
        28, 70,
        "The 5% screen split 17 / 17. Three pairs survived re-extraction. None of those 3 crossed a cutoff.",
        size=13, fill=MUTED, baseline="hanging",
    )

    left, right, top, bot = 90, 740, 108, 548
    vmin, vmax = 5e6, 2.2e8

    def lx(v):
        t = (math.log10(v) - math.log10(vmin)) / (math.log10(vmax) - math.log10(vmin))
        return left + t * (right - left)

    def ly(v):
        t = (math.log10(v) - math.log10(vmin)) / (math.log10(vmax) - math.log10(vmin))
        return bot - t * (bot - top)

    ticks = [1e7, 2e7, 5e7, 1e8, 2e8]
    for t in ticks:
        svg.line(lx(t), top, lx(t), bot, stroke=FAINT, sw=0.8)
        svg.line(left, ly(t), right, ly(t), stroke=FAINT, sw=0.8)
        svg.text(lx(t), bot + 16, millions(t), size=11, fill=MUTED, anchor="middle")
        svg.text(left - 8, ly(t), millions(t), size=11, fill=MUTED, anchor="end",
                 baseline="middle")

    svg.line(lx(vmin), ly(vmin), lx(vmax), ly(vmax), stroke=RULE, sw=1.2)
    svg.line(left, bot, right, bot, stroke=RULE, sw=1)
    svg.line(left, top, left, bot, stroke=RULE, sw=1)

    exact = [p for p in pairs if p["signed"] == 0]
    small = [p for p in pairs if (not p["flag"]) and p["signed"] != 0]
    flagged = [p for p in pairs if p["flag"] and p["id"] not in verified]
    survivors = [p for p in pairs if p["id"] in verified]

    def dots(group, r, fill, stroke="white", sw=0.5, opacity=1):
        for p in group:
            svg.circle(lx(p["r"]), ly(p["y"]), r, fill=fill, stroke=stroke, sw=sw,
                       opacity=opacity)

    svg.clip_start("h2", left, top, right - left, bot - top)
    dots(exact, 3.1, "#b4b4b4", opacity=0.7)
    dots(small, 3.4, "#7a7a7a")
    dots([p for p in flagged if p["signed"] < 0], 4.4, BELOW)
    dots([p for p in flagged if p["signed"] > 0], 4.4, ABOVE)
    for p in survivors:
        svg.circle(lx(p["r"]), ly(p["y"]), 7.2, fill="none", stroke=INK, sw=1.6)
    svg.clip_end()

    n_zero = screen["n_comparable"] - screen["n_nonzero"]
    svg.rect(left + 10, top + 10, 268, 28, fill="white", rx=3)
    svg.text(left + 18, top + 24, f"{n_zero} of {screen['n_comparable']} sit exactly on the line",
             size=13, weight=700, baseline="middle")

    svg.text((left + right) / 2, bot + 40, "Number the reasoning committed to",
             size=13, fill=INK, anchor="middle")
    svg.nodes.append(
        f'<text x="22" y="{(top + bot) / 2:.2f}" fill="{INK}" font-size="13" font-weight="400"'
        f' font-family="Helvetica Neue, Helvetica, Arial, sans-serif" text-anchor="middle"'
        f' dominant-baseline="middle" transform="rotate(-90 22 {(top + bot) / 2:.2f})">'
        f"Visible answer</text>"
    )

    legend = [
        (24, "#b4b4b4", "exact agreement"),
        (190, BELOW, "screened, against"),
        (370, ABOVE, "screened, toward"),
    ]
    for x, colour, label in legend:
        svg.circle(x + 6, 622, 5, fill=colour, stroke="white")
        svg.text(x + 18, 622, label, size=12, fill=MUTED, baseline="middle")
    svg.circle(545, 622, 7, fill="none", stroke=INK, sw=1.5)
    svg.text(559, 622, "still off after re-extraction (3)", size=12, fill=MUTED,
             baseline="middle")

    path = OUT / "fig4_no_answer_swap.svg"
    svg.write(path)
    return path, w, h


# ---------------------------------------------------------------------------
# H3
# ---------------------------------------------------------------------------

def load_h3():
    out = style.ANALYSIS / "hyp7_impartiality_dissociation" / "outputs"
    primary = json.loads((out / "bootstrap_summary.json").read_text())["tiers"]["primary_9"]
    rows = [
        r for r in csv.DictReader((out / "threshold_rates.csv").open())
        if r["dataset"] == "h6_corrected" and r["stratum"] == "all" and r["model_dir"] in primary
    ]
    by_model = {}
    for r in rows:
        by_model.setdefault(r["model_dir"], {})[r["condition"]] = r
    crossing = []
    for model in primary:
        below = by_model[model]["below_good"]
        above = by_model[model]["above_good"]
        crossing.append(
            {
                "label": model_name(model),
                "below": float(below["above_threshold_rate"]) * 100,
                "above": float(above["above_threshold_rate"]) * 100,
            }
        )
    crossing.sort(key=lambda r: r["above"] - r["below"], reverse=True)
    contrasts = {}
    for row in csv.DictReader((out / "contrasts.csv").open()):
        if row["dataset"] == "h6_corrected" and row["tier"] == "primary_9" and row["metric"] == "log":
            contrasts[row["stratum"]] = row
    paired = json.loads((out / "bootstrap_summary.json").read_text())[
        "paired_diff_base_minus_labelpos"
    ]["percentage_points"]
    primary_set = set(primary)
    n_usable = n_promised = 0
    for row in csv.DictReader((out / "h7_outcomes.csv").open()):
        if row["model_dir"] not in primary_set or row["value_status"] != "positive":
            continue
        n_usable += 1
        if row["claim"] == "True":
            n_promised += 1
    assert n_usable == 753
    return crossing, contrasts, paired, n_promised / n_usable


def fig3() -> tuple[Path, int, int]:
    crossing, contrasts, paired, promise_share = load_h3()
    w, h = 840, 670
    svg = Svg(w, h)
    svg.text(28, 20, "Answers move with the donation. The promise does not stop them.",
             size=19, weight=700, baseline="hanging")
    svg.text(28, 48, "The cutoff is the same number in both conditions. Only which side helps the good cause changes.",
             size=13, fill=MUTED, baseline="hanging")

    svg.circle(28, 82, 5.5, fill=BELOW, stroke="white")
    svg.text(40, 82, "going above hurts the good cause", size=13, fill=BELOW, weight=700,
             baseline="middle")
    svg.circle(310, 82, 5.5, fill=ABOVE, stroke="white")
    svg.text(322, 82, "going above helps the good cause", size=13, fill=ABOVE, weight=700,
             baseline="middle")

    left, right, top, bot = 178, 800, 102, 430
    n = len(crossing)
    row_h = (bot - top) / n

    def x_of(p):
        return left + p / 100 * (right - left)

    for tick in (0, 25, 50, 75, 100):
        svg.line(x_of(tick), top, x_of(tick), bot, stroke=FAINT, sw=0.8)
        svg.text(x_of(tick), bot + 16, f"{tick}%" if tick else "0", size=11, fill=MUTED,
                 anchor="middle")

    for i, row in enumerate(crossing):
        y = top + (i + 0.5) * row_h
        svg.line(x_of(row["below"]), y, x_of(row["above"]), y, stroke="#c8c8c8", sw=2.4)
        svg.circle(x_of(row["below"]), y, 5.5, fill=BELOW, stroke="white", sw=0.7)
        svg.circle(x_of(row["above"]), y, 5.5, fill=ABOVE, stroke="white", sw=0.7)
        svg.text(left - 12, y, row["label"], size=13, fill=INK, anchor="end", baseline="middle")
        svg.text(x_of(row["below"]) - 8, y, f"{row['below']:.0f}%", size=11, fill=BELOW,
                 weight=700, anchor="end", baseline="middle")
        svg.text(x_of(row["above"]) + 8, y, f"{row['above']:.0f}%", size=11, fill=ABOVE,
                 weight=700, anchor="start", baseline="middle")

    svg.text((left + right) / 2, bot + 36, "Share of answers above the cutoff",
             size=13, fill=INK, anchor="middle")

    svg.line(28, 462, 812, 462, stroke=FAINT, sw=1)

    # bottom panel: all vs promised
    btop, bbot = 508, 598
    bleft, bright = 178, 760
    svg.text(28, 476, "Shift in answer size, nine models equal-weighted",
             size=14, weight=700, baseline="hanging")

    def bx(p):
        # -4 to 36
        return bleft + (p + 4) / 40 * (bright - bleft)

    for tick, label in ((0, "0"), (10, "+10%"), (20, "+20%"), (30, "+30%")):
        svg.line(bx(tick), btop, bx(tick), bbot, stroke=FAINT, sw=0.8)
        svg.text(bx(tick), bbot + 16, label, size=11, fill=MUTED, anchor="middle")
    svg.line(bx(0), btop, bx(0), bbot, stroke=RULE, sw=1)

    entries = [("all", "All traces"), ("positive", "Promised impartiality")]
    for i, (stratum, label) in enumerate(entries):
        y = btop + (i + 0.5) * ((bbot - btop) / 2)
        row = contrasts[stratum]
        est = float(row["geometric_shift_pct"])
        lo = float(row["geometric_ci95_low_pct"])
        hi = float(row["geometric_ci95_high_pct"])
        svg.line(bx(lo), y, bx(hi), y, stroke=ABOVE, sw=10, cap="round")
        svg.circle(bx(est), y, 5.5, fill=INK, stroke="white", sw=1.2)
        svg.text(bleft - 12, y, label, size=13, fill=INK, anchor="end", baseline="middle")
        svg.text(bx(hi) + 10, y, f"{pct(est)}   [{lo:.1f}, {hi:.1f}]".replace("-", "\u2212"),
                 size=13, weight=700, fill=INK, baseline="middle")

    svg.text((bleft + bright) / 2, bbot + 34, "Change in answer size, when going above helps the good cause",
             size=12.5, fill=INK, anchor="middle")
    delta = (
        f"{paired['estimate']:+.1f} pp  [{paired['ci95_low']:.1f}, {paired['ci95_high']:.1f}]"
        .replace("-", "\u2212")
    )
    svg.text(
        28, 648,
        f"Filtering on the promise changes that shift by {delta}.  "
        f"{promise_share:.0%} of answers in this nine-model sample already carry the promise.",
        size=12, fill=MUTED, baseline="middle",
    )

    path = OUT / "fig2_headline_dissociation.svg"
    svg.write(path)
    return path, w, h


# ---------------------------------------------------------------------------
# Qwen 3.5, the clearest case
# ---------------------------------------------------------------------------

def load_qwen():
    out = style.ANALYSIS / "hyp7_impartiality_dissociation" / "outputs"
    rows = [
        r for r in csv.DictReader((out / "h7_outcomes.csv").open())
        if r["model_dir"].startswith("qwen3.5-122b-a10b_")
    ]
    assert len(rows) == 100
    assert {r["claim"] for r in rows} == {"True"}
    values = {
        cond: [float(r["estimate"]) for r in rows if r["condition"] == cond]
        for cond in ("below_good", "above_good")
    }
    assert all(len(v) == 50 for v in values.values())
    threshold = float(rows[0]["threshold"])
    assert threshold == 41_000_000.0
    assert statistics.median(values["below_good"]) == 38_000_000.0
    assert statistics.median(values["above_good"]) == 44_000_000.0
    assert sum(v > threshold for v in values["below_good"]) == 7
    assert sum(v > threshold for v in values["above_good"]) == 33
    return values, threshold


def fig_qwen() -> tuple[Path, int, int]:
    values, threshold = load_qwen()
    w, h = 840, 430
    svg = Svg(w, h)
    svg.text(28, 18, "Same question, same cutoff, opposite recipient",
             size=20, weight=700, baseline="hanging")
    svg.text(28, 46, "Qwen 3.5. All 100 of these traces were labelled as promising impartiality.",
             size=13, fill=MUTED, baseline="hanging")

    left, right, top, bot = 270, 655, 88, 355
    xmin, xmax = 12.0, 80.0
    threshold_m = threshold / 1e6

    def x_of(val_m):
        return left + (val_m - xmin) / (xmax - xmin) * (right - left)

    svg.rect(x_of(threshold_m), top, right - x_of(threshold_m), bot - top,
             fill=ABOVE, rx=0)
    # overlay white then shade: rect fill needs opacity. svg.rect has no opacity.
    svg.nodes[-1] = (
        f'<rect x="{x_of(threshold_m):.2f}" y="{top:.2f}" '
        f'width="{right - x_of(threshold_m):.2f}" height="{bot - top:.2f}" '
        f'fill="{ABOVE}" opacity="0.10"/>'
    )

    for tick in (20, 40, 60, 80):
        svg.line(x_of(tick), top, x_of(tick), bot, stroke=FAINT, sw=0.8)
        svg.text(x_of(tick), bot + 16, f"{tick}M", size=11, fill=MUTED, anchor="middle")

    svg.line(x_of(threshold_m), top, x_of(threshold_m), bot, stroke=RULE, sw=1.4, dash="4 3")
    svg.text(x_of(threshold_m), top - 8, "cutoff 41M", size=12, fill=INK, weight=700,
             anchor="middle")

    rows = [
        ("above_good", 145, ABOVE, "helps the good cause"),
        ("below_good", 278, BELOW, "hurts the good cause"),
    ]
    svg.clip_start("qwen", left, top, right - left, bot - top)
    for cond, y, colour, _label in rows:
        vals_m = [v / 1e6 for v in values[cond]]
        clipped = [min(max(v, xmin), xmax) for v in vals_m]
        off = style.beeswarm_offsets(clipped, max_width=22, nbins=20)
        for v, dy in zip(clipped, off):
            svg.circle(x_of(v), y + float(dy), 4.0, fill=colour, stroke="white", sw=0.55)
        med = statistics.median(vals_m)
        svg.line(x_of(med), y - 28, x_of(med), y + 28, stroke=INK, sw=2.8, cap="butt")
    svg.clip_end()

    for cond, y, colour, label in rows:
        vals = values[cond]
        n_above = sum(v > threshold for v in vals)
        svg.text(left - 16, y - 11, label, size=12.5, fill=colour, weight=700,
                 anchor="end", baseline="middle")
        svg.text(left - 16, y + 9, f"median {millions(statistics.median(vals))}",
                 size=12, fill=INK, weight=700, anchor="end", baseline="middle")
        svg.text(right + 16, y - 9, f"{n_above} of 50", size=16, fill=colour, weight=700,
                 baseline="middle")
        svg.text(right + 16, y + 11, "above the cutoff", size=11, fill=MUTED,
                 baseline="middle")

    n_off_above = sum(v / 1e6 > xmax for v in values["above_good"])
    n_off_below = sum(v / 1e6 > xmax for v in values["below_good"])
    svg.text((left + right) / 2, bot + 38, "Estimated total giraffe spots",
             size=13, fill=INK, anchor="middle")
    if n_off_above or n_off_below:
        svg.text(
            28, 412,
            f"{n_off_above} answers in the top row and {n_off_below} in the bottom sit above 80M.",
            size=11, fill=MUTED, baseline="hanging",
        )

    path = OUT / "fig3_qwen35_distribution.svg"
    svg.write(path)
    return path, w, h


# ---------------------------------------------------------------------------
# H4
# ---------------------------------------------------------------------------

def load_h4():
    h8 = style.ANALYSIS / "hyp8_locus"
    data = json.loads((h8 / "decomposition_results.json").read_text())
    primary = data["metadata"]["primary_models"]
    components = data["decomposition"]["primary_9"]["components"]
    rows = list(csv.DictReader((h8 / "extractions.csv").open()))
    gated = [
        r for r in rows
        if r["gate_pass"].lower() == "true"
        and r["model"] in primary
        and r["N"] and r["S"]
        and r["condition"] == "baseline"
    ]
    spreads = []
    for factor, key, fmt in (
        ("Giraffe population", "N", lambda lo, hi: f"{lo / 1000:.0f}k–{hi / 1000:.0f}k"),
        ("Spots per giraffe", "S", lambda lo, hi: f"{lo:.0f}–{hi:.0f} spots"),
    ):
        medians = []
        for model in primary:
            vals = [float(r[key]) for r in gated if r["model"] == model]
            if vals:
                medians.append(statistics.median(vals))
        spreads.append(
            {
                "label": factor,
                "lo": min(medians),
                "hi": max(medians),
                "ratio": max(medians) / min(medians),
                "range": fmt(min(medians), max(medians)),
                "colour": BELOW if key == "N" else ABOVE,
            }
        )
    return components, spreads, data["audit_summary"]["error_rate"]


def fig4() -> tuple[Path, int, int]:
    components, spreads, audit_error = load_h4()
    w, h = 860, 520
    svg = Svg(w, h)
    svg.text(28, 16, "Exploratory", size=12, weight=700, fill=MUTED, baseline="hanging")
    svg.text(28, 36, "The shift lands in the assumption nothing pins down",
             size=20, weight=700, baseline="hanging")
    svg.text(28, 66, "If bias takes the path of least resistance it should move spots per giraffe, not the giraffe count.",
             size=13, fill=MUTED, baseline="hanging")

    # left: room to move
    svg.text(28, 106, "How pinned is the input?", size=15, weight=700, baseline="hanging")
    lleft, lright, ltop, lbot = 48, 400, 164, 404
    xmax = max(s["ratio"] for s in spreads) + 0.7

    def lx(ratio):
        return lleft + (ratio - 0.9) / (xmax - 0.9) * (lright - lleft)

    ticks = [1, 2, 3, 4, 5]
    for t in ticks:
        if t > xmax:
            continue
        svg.line(lx(t), ltop, lx(t), lbot, stroke=FAINT, sw=0.8)
        svg.text(lx(t), lbot + 16, "same" if t == 1 else f"{t}\u00d7", size=11, fill=MUTED,
                 anchor="middle")
    svg.line(lx(1), ltop, lx(1), lbot, stroke=RULE, sw=1)

    for i, row in enumerate(spreads):
        y = ltop + 55 + i * 110
        svg.text(lleft, y - 28, row["label"], size=14, weight=700, baseline="hanging")
        svg.text(lleft, y - 10, row["range"], size=12, fill=MUTED, baseline="hanging")
        svg.line(lx(1), y + 18, lx(row["ratio"]), y + 18, stroke=row["colour"], sw=10, cap="round")
        svg.circle(lx(1), y + 18, 6, fill=row["colour"])
        svg.circle(lx(row["ratio"]), y + 18, 6, fill=row["colour"])
        svg.text(lx(row["ratio"]) + 12, y + 18, f"{row['ratio']:.1f}\u00d7",
                 size=16, weight=700, baseline="middle")

    svg.text((lleft + lright) / 2, lbot + 38, "Spread of model medians",
             size=12, fill=INK, anchor="middle")

    # right: where it landed
    svg.text(460, 106, "Where the shift landed", size=15, weight=700, baseline="hanging")
    rleft, rright, rtop, rbot = 470, 820, 164, 404

    def rx(p):
        return rleft + (p + 6) / 24 * (rright - rleft)

    for tick, label in ((-5, "\u22125%"), (0, "0"), (5, "+5%"), (10, "+10%"), (15, "+15%")):
        svg.line(rx(tick), rtop, rx(tick), rbot, stroke=FAINT, sw=0.8)
        svg.text(rx(tick), rbot + 16, label, size=11, fill=MUTED, anchor="middle")
    svg.line(rx(0), rtop, rx(0), rbot, stroke=RULE, sw=1)

    bars = [
        ("ln_N", "Giraffe population", BELOW),
        ("ln_S", "Spots per giraffe", ABOVE),
        ("ln_residual", "Leftover", "#8a8a8a"),
    ]
    for i, (key, label, colour) in enumerate(bars):
        y = rtop + 40 + i * 70
        row = components[key]
        est = row["geometric_shift_pct"]
        lo = row["geometric_ci95_low_pct"]
        hi = row["geometric_ci95_high_pct"]
        svg.text(rleft, y - 18, label, size=13, weight=700, baseline="hanging")
        svg.line(rx(lo), y + 10, rx(hi), y + 10, stroke=colour, sw=10, cap="round")
        svg.circle(rx(est), y + 10, 5.5, fill=INK, stroke="white", sw=1.1)
        svg.text(rx(hi) + 10, y + 10, pct(est), size=16, weight=700, baseline="middle")

    svg.text((rleft + rright) / 2, rbot + 38, "Condition shift",
             size=12, fill=INK, anchor="middle")

    svg.text(
        28, 490,
        f"Equal-weight nine models. {audit_error:.0%} extraction-audit error; "
        "gate pass rates differ by up to 17 pp. Not a breakdown of the +15.5% headline.",
        size=11, fill=MUTED, baseline="hanging",
    )

    path = OUT / "fig5_premise_locus.svg"
    svg.write(path)
    return path, w, h


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for builder in (fig1, fig3, fig_qwen, fig2, fig4):
        svg_path, w, h = builder()
        png_path = svg_path.with_suffix(".png")
        rasterize(svg_path, png_path, w, h)
        print(svg_path)
        print(png_path)


if __name__ == "__main__":
    main()
