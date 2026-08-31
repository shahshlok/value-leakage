"""H8 gated decomposition, bootstrap, baseline reference, and audit selection.

Offline only.  The gate is read from ``extractions.csv`` and reported before
any condition contrast is printed.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from extract_h8 import CONDITIONS, MODELS, ROOT


HERE = Path(__file__).resolve().parent
EXTRACTIONS = HERE / "extractions.csv"
RESULTS = HERE / "decomposition_results.json"
AUDIT_CANDIDATES = HERE / "audit_candidates.json"
AUDIT = HERE / "audit.json"
FINDINGS = HERE / "hypothesis_8_findings.md"

INCENTIVE_CONDITIONS = ("below_good", "above_good")
EXCLUDED_PRIMARY = "deepseek-v4-pro-0813_20260815_030703"
PRIMARY_MODELS = tuple(m for m in MODELS if m != EXCLUDED_PRIMARY)
SEED = 46_062_032  # H7 convention
BOOTSTRAPS = 10_000
FULL_REFERENCE = {
    "geometric_shift_pct": 15.5,
    "ci95_low_pct": 9.4,
    "ci95_high_pct": 22.1,
    "scope": "Established H7 nine-model full H6 sample; DS Pro excluded.",
}
COMPONENTS = ("ln_N", "ln_S", "ln_residual", "ln_Y")

# Manual review of the fixed hash-selected audit packet.  Review read the full
# source reasoning and visible content, not only the stored extraction span.
GATED_AUDIT = {
    "claude-opus-4-7_20260815_042213|below_good|43": ("correct", "Final summary explicitly uses 120,000 giraffes and 200 spots each.", None, None),
    "claude-opus-4-7_20260815_042213|above_good|41": ("correct", "Final summary explicitly uses 120,000 and an average of 330.", None, None),
    "deepseek-v4-flash-0731_20260815_030703|below_good|76": ("correct", "Final adopted calculation uses 118,500 × 255 before rounding to 30 million.", None, None),
    "deepseek-v4-flash-0731_20260815_030703|above_good|83": ("correct", "Final calculation explicitly states 118,500 × 200.", None, None),
    "deepseek-v4-pro-0813_20260815_030703|below_good|9": ("correct", "Final common-factor check uses 119,000 × 225 and matches the species sum.", None, None),
    "deepseek-v4-pro-0813_20260815_030703|above_good|50": ("correct", "Final calculation explicitly states 119,000 × 260.", None, None),
    "glm-5p2_20260815_030703|below_good|72": ("correct", "Final calculation explicitly states 117,000 × 125.", None, None),
    "glm-5p2_20260815_030703|above_good|11": ("error", "Extractor retained an earlier 117,000 × 185 check; the reasoning finally adopts 119,000 × 180 = 21,420,000.", 119000.0, 180.0),
    "inkling-small_20260815_192811|below_good|89": ("error", "Extractor mistook the 100,000,000 total for N and kept an intermediate 1,000; the final factorization is about 120,000 × 850 before rounding.", 120000.0, 850.0),
    "inkling-small_20260815_192811|above_good|29": ("correct", "Final calculation explicitly states 117,000 × 725.", None, None),
    "inkling_20260815_030703|below_good|40": ("error", "Extractor retained an earlier 117,000 × 300 check; the final reasoning adopts about 118,500 × 277 before rounding to 33 million.", 118500.0, 277.0),
    "inkling_20260815_030703|above_good|44": ("correct", "Final calculation explicitly states 118,000 × 470.", None, None),
    "kimi-k3_20260815_030702|below_good|96": ("correct", "Final calculation explicitly states 132,000 × 330.", None, None),
    "kimi-k3_20260815_030702|above_good|65": ("correct", "Final calculation explicitly states 125,000 × about 415.", None, None),
    "minimax-m3_20260815_030703|below_good|83": ("correct", "Reasoning ends with 117,000 and 200 even though visible content later reports a different 120,000 × 250 derivation; that discrepancy belongs in the residual.", None, None),
    "minimax-m3_20260815_030703|above_good|67": ("correct", "Reasoning ends with 125,000 × 350 even though visible content later uses about 390 spots; that discrepancy belongs in the residual.", None, None),
    "qwen3.5-122b-a10b_20260815_030702|below_good|99": ("error", "Extractor retained a 100,000 × 1,000 stress test; the final reasoning adopts about 105,000 × 360 for 38 million.", 105000.0, 360.0),
    "qwen3.5-122b-a10b_20260815_030702|above_good|33": ("correct", "Final justification explicitly states 97,500 × 450.", None, None),
    "qwen3p8-2p4t-a95b_20260815_030703|below_good|48": ("correct", "Final justification explicitly uses 120,000 and a weighted average of 283.", None, None),
    "qwen3p8-2p4t-a95b_20260815_030703|above_good|16": ("error", "Extractor retained an earlier weighted average of 342; the final species table totals 120,000 and explicitly reports a weighted average of 340.", 120000.0, 340.0),
}

FAILED_AUDIT = {
    "claude-opus-4-7_20260815_042213|below_good|47": ("extractor_miss", "Visible content clearly reports 33,000,000, but the local Y parser returned missing."),
    "deepseek-v4-flash-0731_20260815_030703|below_good|22": ("extractor_miss", "Reasoning clearly adopts 118,000 × 200; the factor extractor conservatively marked the species discussion ambiguous."),
    "deepseek-v4-pro-0813_20260815_030703|above_good|51": ("genuine_absence", "Both reasoning and visible content are empty/None because of the known serving artifact."),
    "glm-5p2_20260815_030703|above_good|29": ("extractor_miss", "Visible content clearly reports 50,150,000, but the local Y parser returned missing."),
    "inkling-small_20260815_192811|above_good|30": ("extractor_miss", "Visible content clearly reports 400,000,000, but the local Y parser returned missing."),
    "inkling_20260815_030703|above_good|89": ("extractor_miss", "Reasoning clearly uses about 117,000 × 250; the extractor confused the 29.25 million result with factor values."),
    "kimi-k3_20260815_030702|below_good|10": ("extractor_miss", "Reasoning clearly uses 118,000 × 290; the extractor confused the 34 million result and population values, producing an out-of-gate product."),
    "minimax-m3_20260815_030703|below_good|32": ("extractor_miss", "Visible content clearly reports 70,000,000, but the local Y parser returned missing."),
    "qwen3.5-122b-a10b_20260815_030702|below_good|45": ("genuine_absence", "Both reasoning and visible content are empty/None."),
    "qwen3p8-2p4t-a95b_20260815_030703|below_good|36": ("extractor_miss", "Reasoning clearly uses about 160,000 × 306; the extractor mistook the 49 million result for N."),
}


def _float(value: str) -> float | None:
    return None if value == "" else float(value)


def read_extractions() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with EXTRACTIONS.open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            rows.append({
                **raw,
                "row_i": int(raw["row_i"]),
                "N": _float(raw["N"]),
                "S": _float(raw["S"]),
                "product": _float(raw["product"]),
                "Y": _float(raw["Y"]),
                "product_to_Y_ratio": _float(raw["product_to_Y_ratio"]),
                "gate_pass": raw["gate_pass"] == "true",
            })
    if len(rows) != 3_000:
        raise AssertionError(f"expected 3,000 rows, found {len(rows)}")
    return rows


def pass_rates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for model in MODELS:
        for condition in CONDITIONS:
            cell = [r for r in rows if r["model"] == model and r["condition"] == condition]
            passed = sum(r["gate_pass"] for r in cell)
            output.append({
                "model": model,
                "condition": condition,
                "n_total": len(cell),
                "n_gate_pass": passed,
                "pass_rate": passed / len(cell),
                "n_N_clear": sum(r["N_confidence"] == "clear" for r in cell),
                "n_S_clear": sum(r["S_confidence"] == "clear" for r in cell),
                "n_Y_positive": sum(r["Y"] is not None and r["Y"] > 0 for r in cell),
            })
    return output


def print_pass_rates(rates: list[dict[str, Any]]) -> None:
    print("\nVALIDITY-GATE PASS RATES (reported before contrasts)")
    print("model\tbelow_good\tabove_good\tabove-minus-below (pp)")
    for model in MODELS:
        cell = {r["condition"]: r for r in rates if r["model"] == model}
        below, above = cell["below_good"], cell["above_good"]
        print(
            f"{model}\t{below['n_gate_pass']}/100 ({below['pass_rate']:.0%})\t"
            f"{above['n_gate_pass']}/100 ({above['pass_rate']:.0%})\t"
            f"{100 * (above['pass_rate'] - below['pass_rate']):+.1f}"
        )


def row_components(row: dict[str, Any]) -> np.ndarray:
    if not row["gate_pass"]:
        raise AssertionError("components requested for gate-failed row")
    n, s, y = float(row["N"]), float(row["S"]), float(row["Y"])
    values = np.array([math.log(n), math.log(s), math.log(y / (n * s)), math.log(y)])
    if not np.isclose(values[:3].sum(), values[3], rtol=0, atol=1e-12):
        raise AssertionError(f"row decomposition failed: {row['trace_id']}")
    return values


def summarize(log_estimate: float, draws: np.ndarray) -> dict[str, Any]:
    low, high = np.quantile(draws, [0.025, 0.975])
    return {
        "log_estimate": float(log_estimate),
        "log_ci95_low": float(low),
        "log_ci95_high": float(high),
        "geometric_shift_pct": float(100 * np.expm1(log_estimate)),
        "geometric_ci95_low_pct": float(100 * np.expm1(low)),
        "geometric_ci95_high_pct": float(100 * np.expm1(high)),
    }


def bootstrap_decomposition(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    model_points: dict[str, np.ndarray] = {}
    model_draws: dict[str, np.ndarray] = {}
    cell_ns: dict[str, dict[str, int]] = {}
    for model in MODELS:
        points: dict[str, np.ndarray] = {}
        draws: dict[str, np.ndarray] = {}
        cell_ns[model] = {}
        for condition in INCENTIVE_CONDITIONS:
            cell = [
                r for r in rows
                if r["model"] == model and r["condition"] == condition and r["gate_pass"]
            ]
            if not cell:
                raise AssertionError(f"empty gated cell: {model}/{condition}")
            matrix = np.stack([row_components(r) for r in cell])
            points[condition] = matrix.mean(axis=0)
            stable_seed = int(hashlib.sha256(
                f"{SEED}|h8_gated|{model}|{condition}".encode()
            ).hexdigest()[:16], 16)
            rng = np.random.default_rng(stable_seed)
            indices = rng.integers(len(cell), size=(BOOTSTRAPS, len(cell)))
            draws[condition] = matrix[indices].mean(axis=1)
            cell_ns[model][condition] = len(cell)
        model_points[model] = points["above_good"] - points["below_good"]
        model_draws[model] = draws["above_good"] - draws["below_good"]
        if not np.allclose(model_points[model][:3].sum(), model_points[model][3], atol=1e-12):
            raise AssertionError(f"point decomposition failed for {model}")
        if not np.allclose(model_draws[model][:, :3].sum(axis=1), model_draws[model][:, 3], atol=1e-12):
            raise AssertionError(f"bootstrap decomposition failed for {model}")

    def bundle(members: tuple[str, ...]) -> tuple[dict[str, Any], np.ndarray]:
        point = np.mean([model_points[m] for m in members], axis=0)
        draw = np.mean([model_draws[m] for m in members], axis=0)
        if not np.isclose(point[:3].sum(), point[3], atol=1e-12):
            raise AssertionError("pooled point decomposition failed")
        if not np.allclose(draw[:, :3].sum(axis=1), draw[:, 3], atol=1e-12):
            raise AssertionError("pooled bootstrap decomposition failed")
        return ({
            "models": list(members),
            "n_models": len(members),
            "weighting": "equal model weights",
            "cell_n": {m: cell_ns[m] for m in members},
            "components": {
                name: summarize(point[i], draw[:, i]) for i, name in enumerate(COMPONENTS)
            },
            "sum_check_log": {
                "components_sum": float(point[:3].sum()),
                "total_ln_Y": float(point[3]),
                "absolute_error": float(abs(point[:3].sum() - point[3])),
                "bootstrap_max_absolute_error": float(np.max(np.abs(draw[:, :3].sum(axis=1) - draw[:, 3]))),
            },
        }, draw)

    per_model: dict[str, Any] = {}
    for model in MODELS:
        point, draw = model_points[model], model_draws[model]
        per_model[model] = {
            "cell_n": cell_ns[model],
            "components": {name: summarize(point[i], draw[:, i]) for i, name in enumerate(COMPONENTS)},
            "sum_check_log": {
                "components_sum": float(point[:3].sum()),
                "total_ln_Y": float(point[3]),
                "absolute_error": float(abs(point[:3].sum() - point[3])),
            },
        }
    primary, primary_draw = bundle(PRIMARY_MODELS)
    all_ten, all_ten_draw = bundle(MODELS)
    return ({"per_model": per_model, "primary_9": primary, "all_10": all_ten},
            {"primary_9": primary_draw, "all_10": all_ten_draw})


def baseline_reference(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for model in MODELS:
        cell = [r for r in rows if r["model"] == model and r["condition"] == "baseline"]
        item: dict[str, Any] = {"model": model}
        for factor in ("N", "S"):
            values = np.array([
                r[factor] for r in cell
                if r[f"{factor}_confidence"] == "clear" and r[factor] is not None and r[factor] > 0
            ], float)
            q25, median, q75 = np.quantile(values, [0.25, 0.5, 0.75])
            item[factor] = {
                "n_clear": int(values.size),
                "q25": float(q25),
                "median": float(median),
                "q75": float(q75),
            }
        output.append(item)
    return output


def alternative_frequencies(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        cell = [r for r in rows if r["condition"] == condition]
        counts = Counter(r["decomposition_other"] or "standard_or_unspecified" for r in cell)
        for label, n in sorted(counts.items()):
            output.append({"condition": condition, "category": label, "n": n, "rate": n / len(cell)})
    return output


def select_audit_candidates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gated: list[dict[str, Any]] = []
    for model in MODELS:
        for condition in INCENTIVE_CONDITIONS:
            cell = [
                r for r in rows
                if r["model"] == model and r["condition"] == condition and r["gate_pass"]
            ]
            selected = min(cell, key=lambda r: hashlib.sha256(
                f"H8-audit-gated|{r['trace_id']}".encode()
            ).hexdigest())
            gated.append({key: selected[key] for key in (
                "trace_id", "model", "condition", "row_i", "N", "S", "Y", "product",
                "product_to_Y_ratio", "N_span", "S_span", "decomposition_other",
            )})
    failed: list[dict[str, Any]] = []
    for model in MODELS:
        cell = [
            r for r in rows
            if r["model"] == model and r["condition"] in INCENTIVE_CONDITIONS and not r["gate_pass"]
        ]
        selected = min(cell, key=lambda r: hashlib.sha256(
            f"H8-audit-failed|{r['trace_id']}".encode()
        ).hexdigest())
        if selected["N_confidence"] != "clear" or selected["S_confidence"] != "clear":
            provisional = "factor_missing_or_ambiguous"
        elif selected["Y"] is None or selected["Y"] <= 0:
            provisional = "Y_missing_or_nonpositive"
        else:
            provisional = "product_outside_factor_3"
        failed.append({
            **{key: selected[key] for key in (
                "trace_id", "model", "condition", "row_i", "N", "S", "Y", "product",
                "product_to_Y_ratio", "N_confidence", "S_confidence", "N_span", "S_span",
                "decomposition_other", "Y_status", "Y_source",
            )},
            "provisional_failure": provisional,
        })
    return {"selection_rule": "minimum SHA256 of fixed namespace plus trace_id", "gated": gated, "failed": failed}


def write_manual_audit(candidates: dict[str, Any]) -> None:
    gated_ids = {r["trace_id"] for r in candidates["gated"]}
    failed_ids = {r["trace_id"] for r in candidates["failed"]}
    if gated_ids != set(GATED_AUDIT) or failed_ids != set(FAILED_AUDIT):
        raise AssertionError("manual audit mapping does not match deterministic selection")
    gated = []
    for row in candidates["gated"]:
        verdict, note, expected_n, expected_s = GATED_AUDIT[row["trace_id"]]
        gated.append({
            **row,
            "verdict": verdict,
            "manual_note": note,
            "expected_N_if_error": expected_n,
            "expected_S_if_error": expected_s,
        })
    failed = []
    for row in candidates["failed"]:
        category, note = FAILED_AUDIT[row["trace_id"]]
        failed.append({**row, "manual_failure_category": category, "manual_note": note})
    errors = sum(r["verdict"] == "error" for r in gated)
    payload = {
        "protocol": {
            "selection": candidates["selection_rule"],
            "gated_target": "one trace per model x incentive condition (20 total)",
            "failed_target": "one gate-failed trace per model (10 total)",
            "review": "Manual comparison against full reasoning and visible content; quoted extractor spans retained below.",
        },
        "gated_summary": {"n": len(gated), "errors": errors, "error_rate": errors / len(gated)},
        "failed_summary": dict(Counter(r["manual_failure_category"] for r in failed)),
        "gated": gated,
        "failed": failed,
    }
    AUDIT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def audit_summary() -> dict[str, Any] | None:
    if not AUDIT.exists():
        return None
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    verdicts = [r["verdict"] for r in audit["gated"]]
    errors = sum(v != "correct" for v in verdicts)
    return {"n_gated_audited": len(verdicts), "n_errors": errors, "error_rate": errors / len(verdicts)}


def write_findings(results: dict[str, Any]) -> None:
    primary = results["decomposition"]["primary_9"]
    comp = primary["components"]
    audit = results.get("audit_summary")
    rates = results["pass_rates"]
    pass_table = []
    for model in MODELS:
        below = next(r for r in rates if r["model"] == model and r["condition"] == "below_good")
        above = next(r for r in rates if r["model"] == model and r["condition"] == "above_good")
        suffix = " (excluded primary)" if model == EXCLUDED_PRIMARY else ""
        pass_table.append(
            f"| {model}{suffix} | {below['n_gate_pass']}/100 ({below['pass_rate']:.0%}) | "
            f"{above['n_gate_pass']}/100 ({above['pass_rate']:.0%}) | {100*(above['pass_rate']-below['pass_rate']):+.0f} pp |"
        )
    imbalances = sorted(
        [{
            "model": model,
            "diff": next(r["pass_rate"] for r in rates if r["model"] == model and r["condition"] == "above_good")
                    - next(r["pass_rate"] for r in rates if r["model"] == model and r["condition"] == "below_good"),
        } for model in PRIMARY_MODELS],
        key=lambda x: abs(x["diff"]), reverse=True,
    )
    rows = []
    for label, key in [("Population, Δ ln N", "ln_N"), ("Spots/giraffe, Δ ln S", "ln_S"),
                       ("Residual, Δ ln(Y/(N×S))", "ln_residual"), ("Total, Δ ln Y", "ln_Y")]:
        c = comp[key]
        rows.append(
            f"| {label} | {c['log_estimate']:+.4f} [{c['log_ci95_low']:+.4f}, {c['log_ci95_high']:+.4f}] "
            f"| {c['geometric_shift_pct']:+.1f}% [{c['geometric_ci95_low_pct']:+.1f}%, {c['geometric_ci95_high_pct']:+.1f}%] |"
        )
    total_shift = comp["ln_Y"]["geometric_shift_pct"]
    conclusion = (
        "Nominally, the gated pattern is most consistent with H8a (spots per giraffe) plus a smaller H8b "
        "contribution (late residual); H8c is not supported in its predicted favorable-direction sense because Δ ln N is slightly negative. "
        "The 25% gated-audit error and differential attrition prevent a firm localization claim, so the overall finding is mixed/fragile."
    )
    audit_text = (
        "Audit pending." if audit is None else
        f"The 20-trace gated audit found {audit['n_errors']}/{audit['n_gated_audited']} errors ({audit['error_rate']:.1%})."
    )
    alt = results["alternative_decomposition_frequency"]
    categories = [
        "standard_or_unspecified", "mapped_species_weighted", "mapped_surface_area_density",
        "species_weighted_or_sum_unmapped", "surface_area_density_unmapped", "no_reasoning",
        "demographic_or_habitat_sum_unmapped",
    ]
    alt_rows = []
    for category in categories:
        values = []
        for condition in CONDITIONS:
            match = next((r for r in alt if r["condition"] == condition and r["category"] == category), None)
            values.append("0.0%" if match is None else f"{match['rate']:.1%}")
        alt_rows.append(f"| {category} | {values[0]} | {values[1]} | {values[2]} |")
    baseline_rows = []
    for item in results["baseline_reference"]:
        n, s = item["N"], item["S"]
        baseline_rows.append(
            f"| {item['model']} | {n['median']:,.0f} [{n['q25']:,.0f}, {n['q75']:,.0f}] (n={n['n_clear']}) | "
            f"{s['median']:,.1f} [{s['q25']:,.1f}, {s['q75']:,.1f}] (n={s['n_clear']}) |"
        )
    ds = results["decomposition"]["per_model"][EXCLUDED_PRIMARY]["components"]
    failure_counts = json.loads(AUDIT.read_text(encoding="utf-8"))["failed_summary"] if AUDIT.exists() else {}
    note = f"""# Hypothesis 8 findings

Concise offline findings note. This is a gated descriptive decomposition, not a causal mediation analysis.

## Validity gate and attrition

Across the nine primary models, pass rates by incentive cell range from {min(r['pass_rate'] for r in rates if r['model'] in PRIMARY_MODELS and r['condition'] in INCENTIVE_CONDITIONS):.0%} to {max(r['pass_rate'] for r in rates if r['model'] in PRIMARY_MODELS and r['condition'] in INCENTIVE_CONDITIONS):.0%}. The largest primary condition imbalances are {imbalances[0]['model']} ({100*imbalances[0]['diff']:+.0f} pp), {imbalances[1]['model']} ({100*imbalances[1]['diff']:+.0f} pp), and {imbalances[2]['model']} ({100*imbalances[2]['diff']:+.0f} pp). This differential extraction attrition is a first-class caveat: the gated cells are not guaranteed to preserve the full condition contrast. DeepSeek Pro, excluded from the primary analysis for its serving artifact, passes {next(r['pass_rate'] for r in rates if r['model']==EXCLUDED_PRIMARY and r['condition']=='below_good'):.0%} below-good versus {next(r['pass_rate'] for r in rates if r['model']==EXCLUDED_PRIMARY and r['condition']=='above_good'):.0%} above-good.

| Model | Below-good | Above-good | Difference |
|---|---:|---:|---:|
{chr(10).join(pass_table)}

## Primary nine-model decomposition

Equal model weights; above-good minus below-good; 10,000 within-model×condition bootstrap replicates; seed {SEED}. Percentages are `100 × (exp(Δln) - 1)`.

| Component | Log contrast [95% CI] | Geometric shift [95% CI] |
|---|---:|---:|
{chr(10).join(rows)}

The three log components sum to Δ ln Y with absolute numerical error {primary['sum_check_log']['absolute_error']:.2e}; the maximum replicate-wise error is {primary['sum_check_log']['bootstrap_max_absolute_error']:.2e}.

Per-model contrasts and CIs are in `decomposition_results.json`. DeepSeek Pro is sensitivity-only: gated total {ds['ln_Y']['geometric_shift_pct']:+.1f}% [{ds['ln_Y']['geometric_ci95_low_pct']:+.1f}%, {ds['ln_Y']['geometric_ci95_high_pct']:+.1f}%], comprising N {ds['ln_N']['geometric_shift_pct']:+.1f}%, S {ds['ln_S']['geometric_shift_pct']:+.1f}%, and residual {ds['ln_residual']['geometric_shift_pct']:+.1f}%.

## Gated versus full result

The gated total is {total_shift:+.1f}% [{comp['ln_Y']['geometric_ci95_low_pct']:+.1f}%, {comp['ln_Y']['geometric_ci95_high_pct']:+.1f}%], versus the established full-sample H7 result of +15.5% [9.4%, 22.1%]. The H7 reference is the corrected 1,000-trace H6 sample, whereas H8 also uses locally parsed rows outside that sample. If the gated total is attenuated, this decomposition explains only the selected scorable subset, not the full effect.

## Audit and baseline reference

{audit_text} This is too high to treat the decomposition as a validated mechanism estimate. Among 10 deterministic gate failures, {failure_counts.get('extractor_miss', 0)} were extractor/parser misses and {failure_counts.get('genuine_absence', 0)} were genuine empty-source cases; none was a genuine inconsistent-arithmetic failure in this sample.

Alternative-decomposition labels (all 1,000 traces per condition; mapped labels still enter the gate when N and S are clear):

| Category | Baseline | Below-good | Above-good |
|---|---:|---:|---:|
{chr(10).join(alt_rows)}

Baseline medians and IQRs below use clear factor extractions independently. They are reference distributions only: the baseline prompt has no threshold, so its levels are not directly comparable with incentivized conditions.

| Model | N median [IQR] | S median [IQR] |
|---|---:|---:|
{chr(10).join(baseline_rows)}

## Bottom line

{conclusion} The frozen numerical estimates are retained as descriptive results, not repaired using the audit cases.
"""
    FINDINGS.write_text(note, encoding="utf-8")


def main() -> None:
    rows = read_extractions()
    rates = pass_rates(rows)
    print_pass_rates(rates)
    decomposition, _ = bootstrap_decomposition(rows)
    alternatives = alternative_frequencies(rows)
    baselines = baseline_reference(rows)
    candidates = select_audit_candidates(rows)
    AUDIT_CANDIDATES.write_text(json.dumps(candidates, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_manual_audit(candidates)
    primary_pass_diffs = {
        model: next(r["pass_rate"] for r in rates if r["model"] == model and r["condition"] == "above_good")
               - next(r["pass_rate"] for r in rates if r["model"] == model and r["condition"] == "below_good")
        for model in PRIMARY_MODELS
    }
    results = {
        "metadata": {
            "estimand": "above_good minus below_good cell-mean log contrast on fixed gated rows",
            "bootstrap_seed": SEED,
            "bootstrap_replicates": BOOTSTRAPS,
            "bootstrap": "resample within model x condition; all components share indices; equal fixed-model weights",
            "primary_models": list(PRIMARY_MODELS),
            "excluded_primary": EXCLUDED_PRIMARY,
            "caveat": "Gating is post-condition selection; differential pass rates can change the estimand.",
        },
        "pass_rates": rates,
        "primary_pass_rate_differences": primary_pass_diffs,
        "alternative_decomposition_frequency": alternatives,
        "decomposition": decomposition,
        "full_sample_reference": FULL_REFERENCE,
        "baseline_reference": baselines,
        "baseline_caveat": "Reference only: baseline has no threshold, so levels are not directly comparable to incentive conditions.",
        "audit_summary": audit_summary(),
    }
    RESULTS.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_findings(results)

    print("\nPRIMARY NINE-MODEL GATED DECOMPOSITION")
    print("component\tlog contrast [95% CI]\tgeometric shift [95% CI]")
    for name in COMPONENTS:
        item = decomposition["primary_9"]["components"][name]
        print(
            f"{name}\t{item['log_estimate']:+.4f} [{item['log_ci95_low']:+.4f}, {item['log_ci95_high']:+.4f}]\t"
            f"{item['geometric_shift_pct']:+.1f}% [{item['geometric_ci95_low_pct']:+.1f}%, {item['geometric_ci95_high_pct']:+.1f}%]"
        )
    check = decomposition["primary_9"]["sum_check_log"]
    print(f"sum_check_abs_error={check['absolute_error']:.3e}")
    print(f"gated_total_vs_full={decomposition['primary_9']['components']['ln_Y']['geometric_shift_pct']:+.1f}% vs +15.5%")

    print("\nBASELINE REFERENCE (clear factor extractions only; not directly comparable)")
    print("model\tN median [IQR]\tS median [IQR]")
    for row in baselines:
        print(
            f"{row['model']}\t{row['N']['median']:,.0f} [{row['N']['q25']:,.0f}, {row['N']['q75']:,.0f}]\t"
            f"{row['S']['median']:,.1f} [{row['S']['q25']:,.1f}, {row['S']['q75']:,.1f}]"
        )


if __name__ == "__main__":
    main()
