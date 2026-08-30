"""Final audited moral-comparison analysis; run after full_estimates.csv exists."""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ANCHOR_CSV = ROOT / "analysis/hyp1_threshold_anchoring/final_estimates.csv"
HISTORICAL = HERE / "historical_check.json"
N_BOOT = 10_000
SEED = 20260830


def median(values):
    return float(np.median(values)) if values else None


def numbers(rows):
    return [float(r["final_estimate"]) for r in rows if r["final_estimate"].strip()]


def ratio_result(above, below, seed):
    out = {"ratio": None, "ratio_minus_1": None, "ci95_ratio": None,
           "ci95_ratio_minus_1": None, "bootstrap_undefined_replicates": 0,
           "bootstrap_resamples": N_BOOT, "seed": seed}
    a, b = median(above), median(below)
    if a is None or b is None or b == 0:
        return out
    out["ratio"], out["ratio_minus_1"] = a / b, a / b - 1
    rng = np.random.default_rng(seed)
    ad = rng.choice(above, (N_BOOT, len(above)))
    bd = rng.choice(below, (N_BOOT, len(below)))
    den = np.median(bd, axis=1)
    undefined = den == 0
    out["bootstrap_undefined_replicates"] = int(undefined.sum())
    if not undefined.any():
        ci = np.quantile(np.median(ad, axis=1) / den, [0.025, 0.975]).tolist()
        out["ci95_ratio"] = ci
        out["ci95_ratio_minus_1"] = [x - 1 for x in ci]
    return out


def cell_summary(rows):
    valid = numbers(rows)
    status = Counter(r.get("audit_status", "") or "missing" for r in rows)
    providers = Counter(r.get("provider", "") or "unknown" for r in rows)
    parser_status = Counter((r.get("parser_status", "") or "missing") for r in rows)
    measurement_source = Counter((r.get("measurement_source", "") or "missing") for r in rows)
    return {"n_total": len(rows), "n_valid": len(valid), "median": median(valid),
            "missingness": {"n_missing": len(rows) - len(valid),
                            "n_ambiguous": status.get("ambiguous", 0),
                            "rate": (len(rows) - len(valid)) / len(rows) if rows else None},
            "provider_counts": dict(sorted(providers.items())),
            "audit_status_counts": dict(sorted(status.items())),
            "parser_status_counts": dict(sorted(parser_status.items())),
            "measurement_source_counts": dict(sorted(measurement_source.items()))}


def read_moral(path):
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    expected = {"opaque_id", "model", "model_id", "condition", "threshold", "split",
                "final_estimate", "audit_status", "provider"}
    if len(rows) != 200 or not rows or not expected <= set(rows[0]):
        raise ValueError("full_estimates.csv must contain 200 rows with the audited schema")
    if len({r["opaque_id"] for r in rows}) != 200:
        raise ValueError("opaque_id values must be unique")
    if Counter((r["model"], r["condition"]) for r in rows) != Counter({
            (m, c): 50 for m in {r["model"] for r in rows} for c in {"below_good", "above_good"}}):
        raise ValueError("expected exactly 50 rows in each model/condition cell")
    models = {r["model"] for r in rows}
    expected_extension = Counter({(m, c, "extension"): 40 for m in models for c in {"below_good", "above_good"}})
    if Counter((r["model"], r["condition"], r["split"]) for r in rows if r["split"] == "extension") != expected_extension:
        raise ValueError("expected 40 extension rows in each model/condition cell")
    if Counter(r["split"] for r in rows) != Counter({"pilot": 40, "extension": 160}):
        raise ValueError("expected 40 pilot and 160 extension rows")
    if Counter(r.get("audit_status", "") for r in rows) != Counter({"clear": 200}):
        raise ValueError("all 200 moral rows must have audit_status=clear")
    for r in rows:
        if r["final_estimate"].strip():
            value = float(r["final_estimate"])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"invalid final estimate for {r['opaque_id']}")
    return rows


def analysis(rows, split_name, seed, splits=None):
    subset = list(rows) if splits is None else [r for r in rows if r["split"] in splits]
    models = sorted({r["model"] for r in subset})
    cells, effects = {}, {}
    for model in models:
        by = {}
        for condition in ("below_good", "above_good"):
            cr = [r for r in subset if r["model"] == model and r["condition"] == condition]
            by[condition] = cell_summary(cr)
        cells[model] = by
        effects[model] = ratio_result(numbers([r for r in subset if r["model"] == model and r["condition"] == "above_good"]),
                                      numbers([r for r in subset if r["model"] == model and r["condition"] == "below_good"]), seed)
    return {"universe": split_name, "n_rows": len(subset), "cells": cells, "effects": effects}


def read_neutral(path=ANCHOR_CSV):
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    expected = {"blinded_id", "source_file", "row_i", "split", "model", "condition", "anchor",
                "provider", "parser_status", "final_estimate", "final_status", "measurement_source"}
    if len(rows) != 400 or not rows or not expected <= set(rows[0]):
        raise ValueError("final_estimates.csv must contain 400 rows with the audited schema")
    if len({r["blinded_id"] for r in rows}) != 400:
        raise ValueError("neutral blinded_id values must be unique")
    if Counter((r["model"], r["condition"], r["anchor"]) for r in rows) != Counter(
            {(m, c, a): 50 for m in {r["model"] for r in rows}
             for c in {"neutral_boundary", "irrelevant_number"}
             for a in sorted({r["anchor"] for r in rows if r["model"] == m and r["condition"] == c})}):
        raise ValueError("expected exactly 50 rows in each neutral model/framing/anchor cell")
    for r in rows:
        if r["final_estimate"].strip():
            value = float(r["final_estimate"])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"invalid neutral final estimate for {r['blinded_id']}")
    return rows


def neutral_context(rows, split):
    out = defaultdict(dict)
    subset = [r for r in rows if split is None or r["split"] == split]
    for model in sorted({r["model"] for r in subset}):
        for framing in ("neutral_boundary", "irrelevant_number"):
            for anchor in sorted({r["anchor"] for r in subset if r["model"] == model and r["condition"] == framing}, key=float):
                cell = [r for r in subset if r["model"] == model and r["condition"] == framing
                        and r["anchor"] == anchor]
                vals = [float(r["final_estimate"]) for r in cell if r["final_estimate"].strip()]
                if vals:
                    parser_status = Counter((r.get("parser_status", "") or "missing") for r in cell)
                    measurement_source = Counter((r.get("measurement_source", "") or "missing") for r in cell)
                    final_status = Counter((r.get("final_status", "") or "missing") for r in cell)
                    out[model].setdefault(framing, {})[anchor] = {
                        "anchor": float(anchor), "n_total": len(cell), "n_valid": len(vals), "median": median(vals),
                        "n_missing": len(cell) - len(vals),
                        "parser_status_counts": dict(sorted(parser_status.items())),
                        "measurement_source_counts": dict(sorted(measurement_source.items())),
                        "final_status_counts": dict(sorted(final_status.items())),
                    }
    return {m: dict(v) for m, v in out.items()}


def neutral_analysis(rows, universe, split):
    subset = [r for r in rows if split is None or r["split"] == split]
    cells = neutral_context(rows, split)
    effects = {}
    for model in sorted(cells):
        effects[model] = {}
        for framing in ("neutral_boundary", "irrelevant_number"):
            anchors = sorted(cells[model].get(framing, {}), key=float)
            if len(anchors) != 2:
                effects[model][framing] = ratio_result([], [], SEED)
                continue
            low, high = anchors
            low_rows = [r for r in subset if r["model"] == model and r["condition"] == framing and r["anchor"] == low]
            high_rows = [r for r in subset if r["model"] == model and r["condition"] == framing and r["anchor"] == high]
            result = ratio_result(numbers(high_rows), numbers(low_rows), SEED)
            result.update({"low_anchor": float(low), "high_anchor": float(high)})
            effects[model][framing] = result
    return {"universe": universe, "n_rows": len(subset), "cells": cells, "effects": effects}


def original_neutral_context():
    data = json.loads((ROOT / "analysis/hyp1_threshold_anchoring/results.json").read_text(encoding="utf-8"))
    primary = data["confirmatory_primary"]["bootstrap"]
    secondary = data["prespecified_secondary"]["bootstrap"]
    return {"primary_pooled_ratio_minus_1": data["confirmatory_primary"]["exp_theta_minus_1"],
            "primary_ci95_ratio_minus_1": primary["exp_theta_minus_1_ci_95_percentile"],
            "secondary_pooled_ratio_minus_1": data["prespecified_secondary"]["exp_theta_minus_1"],
            "secondary_ci95_ratio_minus_1": secondary["exp_theta_minus_1_ci_95_percentile"]}


def historical_context():
    data = json.loads(HISTORICAL.read_text(encoding="utf-8"))
    out = {}
    for model, item in data.get("historical", {}).items():
        moral = item.get("moral", {})
        out[model] = {c: moral.get(c, {}).get("summary", {}).get("median_clear")
                      for c in ("below_good", "above_good")}
    return out


def jitter(ax, values, x, color, label, marker="o"):
    if not values:
        return
    rng = np.random.default_rng(17 + x)
    ax.scatter(x + rng.uniform(-0.11, 0.11, len(values)), values, s=13, alpha=.65,
               color=color, edgecolors="none", marker=marker, label=label)
    ax.plot([x - .22, x + .22], [np.median(values)] * 2, color="black", lw=3, solid_capstyle="butt")


def figure(rows, path):
    models = sorted({r["model"] for r in rows})
    model_ids = {r["model"]: r["model_id"] for r in rows}
    neutral_rows = read_neutral()
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), squeeze=False)
    colors = {"below_good": "#4c78a8", "above_good": "#f58518",
              ("neutral_boundary", "low"): "#54a24b", ("neutral_boundary", "high"): "#b279a2",
              ("irrelevant_number", "low"): "#72b7b2", ("irrelevant_number", "high"): "#e45756"}
    for i, model in enumerate(models):
        left, right = axes[i]
        neutral = [r for r in neutral_rows if r["model"] == model_ids[model]]
        neutral_labels = []
        for x, (framing, anchor) in enumerate((
                (f, a) for f in ("neutral_boundary", "irrelevant_number")
                for a in sorted({r["anchor"] for r in neutral if r["condition"] == f}, key=float))):
            vals = [float(r["final_estimate"]) / 1e6 for r in neutral
                    if r["condition"] == framing and r["anchor"] == anchor and r["final_estimate"].strip()]
            level = "low" if x % 2 == 0 else "high"
            jitter(left, vals, x, colors[(framing, level)], framing, marker="o" if framing == "neutral_boundary" else "s")
            neutral_labels.append(f"{'boundary' if framing == 'neutral_boundary' else 'irrelevant'}\n{float(anchor)/1e6:g}M")
        left.set_xticks(range(len(neutral_labels)), neutral_labels)
        left.set_title("Neutral numbers · 50 answers per group")
        left.set_xlabel("neutral framing and anchor")
        fresh = [r for r in rows if r["model"] == model]
        for x, condition in enumerate(("below_good", "above_good")):
            vals = [v / 1e6 for v in numbers([r for r in fresh if r["condition"] == condition])]
            jitter(right, vals, x, colors[condition], condition)
        right.set_xticks([0, 1], ["below-good", "above-good"])
        right.set_title("Moral direction · 50 answers per group")
        right.set_xlabel(f"fixed threshold: {float(fresh[0]['threshold']) / 1e6:g}M")
        left.set_ylabel(("Qwen 3.5" if model == "qwen3.5-122b-a10b" else "Qwen 3.8") + "\nestimate (millions)")
        right.set_ylabel("estimate (millions)")
        pooled = [float(r["final_estimate"]) / 1e6 for r in neutral + fresh if r["final_estimate"].strip()]
        positive = bool(pooled) and min(pooled) > 0
        for ax in (left, right):
            if positive:
                ax.set_yscale("log")
            else:
                ax.set_yscale("symlog", linthresh=1)
            if pooled:
                lo, hi = min(pooled), max(pooled)
                ax.set_ylim((lo / 1.5, hi * 1.5) if positive else (-.15, hi * 1.2))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda value, pos: f"{value:,.0f}"))
            ax.grid(axis="y", alpha=.2)
    fig.suptitle("Threshold anchoring: full-run distributions")
    fig.text(.5, .02, "400 neutral + 200 moral answers. Points = individual answers; black bars = medians. All outliers retained.\nLogarithmic scale (linear below 1M in the lower row to include zero); matched scales within each row.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .06, 1, .96))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=HERE / "full_estimates.csv")
    ap.add_argument("--outdir", type=Path, default=HERE)
    args = ap.parse_args()
    rows = read_moral(args.input)
    neutral_rows = read_neutral()
    full_moral = analysis(rows, "all_200", SEED)
    fresh = analysis(rows, "fresh_extension_160", SEED, {"extension"})
    neutral_all = neutral_analysis(neutral_rows, "all_400", None)
    neutral_holdout = neutral_analysis(neutral_rows, "holdout_360", "holdout")
    results = {"design": {"primary": "fresh extension 160; above_good median / below_good median - 1",
                           "full_run": "all 200 moral responses and all 400 neutral responses; descriptive, not preregistered confirmation",
                           "sensitivity": "locked fresh extension 160 and neutral holdout 360",
                           "bootstrap": N_BOOT,
                           "seed": SEED, "interval": "95% percentile; pointwise; no multiplicity adjustment",
                           "resampling": "conditions independently resampled; not paired",
                           "same_protocol_early_responses_included": True,
                           "combined_is_not_preregistered_confirmation": True},
               "full_run": {"moral_all_200": full_moral, "neutral_all_400": neutral_all},
               "sensitivity": {"moral_fresh_extension_160": fresh, "neutral_holdout_360": neutral_holdout},
               "primary_fresh": fresh,
               "secondary_combined": full_moral,
               "references": {"existing_neutral_holdout": neutral_holdout["cells"],
                              "original_neutral_pooled": original_neutral_context(),
                              "historical_check_medians": historical_context(),
                              "neutral_source": str(ANCHOR_CSV),
                              "original_neutral_source": str(ROOT / "analysis/hyp1_threshold_anchoring/results.json"),
                              "historical_source": str(HISTORICAL)}}
    args.outdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / "full_results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    figure(rows, args.outdir / "h1_summary.png")
    lines = ["# Full-run descriptive moral comparison", "", "Full run: all 200 moral responses (50 per model/condition cell) and all 400 neutral responses (50 per model/framing/anchor cell). The early 40 moral responses were collected under the same protocol and are included here; the locked fresh-extension and neutral-holdout analyses remain sensitivities. Bootstrap conditions independently (10,000 resamples; seed 20260830); intervals are pointwise 95% percentile intervals.", "", "## ALL200 moral direction (descriptive)", "", "| Model | Below-good median (n) | Above-good median (n) | Ratio - 1 (95% CI) |", "|---|---:|---:|---:|"]
    for model, e in full_moral["effects"].items():
        b, a = full_moral["cells"][model]["below_good"], full_moral["cells"][model]["above_good"]
        ci = e["ci95_ratio_minus_1"]
        effect = "undefined" if e["ratio_minus_1"] is None else f"{e['ratio_minus_1']:.3g} ({ci[0]:.3g}, {ci[1]:.3g})" if ci else f"{e['ratio_minus_1']:.3g} (CI undefined)"
        lines.append(f"| {model} | {b['median']} ({b['n_valid']}) | {a['median']} ({a['n_valid']}) | {effect} |")
    lines += ["", "## ALL400 neutral numerical anchoring (descriptive)", "", "| Model | Framing | Low anchor median (n) | High anchor median (n) | High/low - 1 (95% CI) |", "|---|---|---:|---:|---:|"]
    for model, framings in neutral_all["cells"].items():
        for framing, cells in framings.items():
            anchors = sorted(cells, key=float)
            low, high = cells[anchors[0]], cells[anchors[-1]]
            e = neutral_all["effects"][model][framing]
            ci = e["ci95_ratio_minus_1"]
            effect = "undefined" if e["ratio_minus_1"] is None else f"{e['ratio_minus_1']:.3g} ({ci[0]:.3g}, {ci[1]:.3g})" if ci else f"{e['ratio_minus_1']:.3g} (CI undefined)"
            lines.append(f"| {model} | {framing} | {low['median']} ({low['n_valid']}) | {high['median']} ({high['n_valid']}) | {effect} |")
    lines += ["", "## Sensitivity analyses", "", "The locked fresh extension (160 responses) is the unseen-data check; its intervals are compatible with zero, weakening the moral-direction evidence from the descriptive ALL200 combination. The neutral holdout remains a prior 360-response reference. The ALL200 combination is not a preregistered confirmation.", "", "| Model | Fresh extension below (n) | Fresh extension above (n) | Ratio - 1 (95% CI) |", "|---|---:|---:|---:|"]
    for model, e in fresh["effects"].items():
        b, a = fresh["cells"][model]["below_good"], fresh["cells"][model]["above_good"]
        ci = e["ci95_ratio_minus_1"]
        effect = "undefined" if e["ratio_minus_1"] is None else f"{e['ratio_minus_1']:.3g} ({ci[0]:.3g}, {ci[1]:.3g})" if ci else f"{e['ratio_minus_1']:.3g} (CI undefined)"
        lines.append(f"| {model} | {b['median']} ({b['n_valid']}) | {a['median']} ({a['n_valid']}) | {effect} |")
    lines += ["", "## Reference context", "", "See the root [hypothesis_1_report.md](../../hypothesis_1_report.md) for the human-facing synthesis. The neutral holdout medians and audit references are retained in `full_results.json`; the holdout has 45 usable observations per anchor/cell. Historical moral medians and original neutral pooled references are separate context, not interchangeable fresh evidence.", "", "This is a descriptive uncertainty statement, not a significance claim. Number-magnitude manipulation at two anchors supports number sensitivity, not presence-versus-absence (there is no contemporaneous number-free baseline). Multiple providers are routing variation, not evidence that weights or quantization changed. Missingness and ambiguous counts are retained per cell in `full_results.json`; zero estimates are valid values. Neutral-anchor and moral-direction experiments are independent, not a matched three-arm design.", "", "Plot caveats: jitter shows every valid individual value and retains outliers, black bars mark medians, values are plotted in millions on a log scale, and y-scales are shared within each model row. Prompt, provider, and batch differences remain possible.", ""]
    lines = [line.replace("values are plotted in millions on a log scale", "values are plotted in millions on a log scale (linear near zero in the lower row)") for line in lines]
    (args.outdir / "full_summary.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
