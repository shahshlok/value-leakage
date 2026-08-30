"""Reproducible locked analysis for the threshold-anchoring follow-up.

This module consumes the blinded extraction and audit artifacts, resolves the
final estimates without using response content, and writes the analysis
outputs requested by the locked plan.  It deliberately has no network or API
calls.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


N_PERMUTATIONS = 100_000
N_BOOTSTRAPS = 10_000
SEED = 20_260_829
PRIMARY_FRAMING = "neutral_boundary"
SECONDARY_FRAMING = "irrelevant_number"
EXPECTED_PLAN_SHA256 = "477a06a312cd4fc48aa5aca1cf23c25f0079156c37ae6d342fd3955714027b8a"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _decimal(value: str | None, field: str) -> Decimal:
    if value is None or value == "":
        raise AssertionError(f"missing {field}")
    return Decimal(value)


def _decimal_text(value: Decimal | None) -> str:
    if value is None:
        return ""
    if value == value.to_integral_value():
        return str(value.to_integral_value())
    return format(value, "f").rstrip("0").rstrip(".")


def _float(value: Decimal) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise AssertionError("non-finite estimate")
    return result


def _assert_core_artifacts(root: Path) -> str:
    manifest = json.loads((root / "extraction_manifest.json").read_text(encoding="utf-8"))
    for filename, expected in manifest["artifact_sha256"].items():
        actual = _sha256(root / filename)
        assert actual == expected, f"protected artifact hash changed: {filename}"
    plan_hash = _sha256(root / "analysis_plan.md")
    assert plan_hash == EXPECTED_PLAN_SHA256, "analysis plan hash is not locked"
    return plan_hash


def build_final_estimates(root: Path) -> list[dict[str, object]]:
    """Join blinded extractions to the key and resolve the blinded audit."""
    extractions = _read_csv(root / "blinded_extractions.csv")
    key_rows = _read_csv(root / "extraction_key.csv")
    reviews = _read_csv(root / "audit_review_a.csv") + _read_csv(root / "audit_review_b.csv")
    adjudications = _read_csv(root / "audit_adjudication.csv")

    assert len(extractions) == len(key_rows) == 400
    extraction_by_id = {row["blinded_id"]: row for row in extractions}
    key_by_id = {row["blinded_id"]: row for row in key_rows}
    assert len(extraction_by_id) == len(extractions) == 400
    assert len(key_by_id) == len(key_rows) == 400
    assert set(extraction_by_id) == set(key_by_id)
    assert len(reviews) == 400
    review_counts: dict[str, int] = defaultdict(int)
    for row in reviews:
        review_counts[row["blinded_id"]] += 1
    assert set(review_counts) == set(extraction_by_id)
    assert all(count == 1 for count in review_counts.values()), "review IDs must be unique"

    disagreement_ids = {
        row["blinded_id"] for row in reviews if row["reviewer_status"] != "agree"
    }
    adjudication_by_id = {row["blinded_id"]: row for row in adjudications}
    assert len(adjudications) == len(adjudication_by_id) == 32
    assert disagreement_ids == set(adjudication_by_id)
    assert len(disagreement_ids) == 32

    final_rows: list[dict[str, object]] = []
    for blinded_id, extraction in extraction_by_id.items():
        metadata = key_by_id[blinded_id]
        review = next(row for row in reviews if row["blinded_id"] == blinded_id)
        parser_estimate = (
            _decimal(extraction["extracted_estimate"], "parser estimate")
            if extraction["extracted_estimate"]
            else None
        )
        parser_status = extraction["parser_status"]
        if blinded_id in disagreement_ids:
            adjudication = adjudication_by_id[blinded_id]
            final_estimate = _decimal(adjudication["adjudicated_estimate"], "adjudicated estimate")
            final_status = adjudication["adjudicator_status"]
            measurement_source = "blind_adjudication"
        else:
            assert review["reviewer_status"] == "agree"
            assert parser_estimate is not None
            assert _decimal(review["parser_estimate"], "review parser estimate") == parser_estimate
            final_estimate = parser_estimate
            final_status = parser_status
            measurement_source = "parser_confirmed"

        assert final_estimate >= 0, f"negative final estimate for {blinded_id}"
        final_rows.append(
            {
                "blinded_id": blinded_id,
                "source_file": metadata["source_file"],
                "row_i": int(metadata["row_i"]),
                "split": metadata["split"],
                "model": metadata["model"],
                "condition": metadata["condition"],
                "anchor": int(metadata["anchor"]),
                "provider": metadata["provider"],
                "parser_estimate": parser_estimate,
                "parser_status": parser_status,
                "final_estimate": final_estimate,
                "final_status": final_status,
                "measurement_source": measurement_source,
            }
        )

    assert len(final_rows) == 400
    assert len({row["blinded_id"] for row in final_rows}) == 400
    assert all(row["final_estimate"] is not None and row["final_estimate"] >= 0 for row in final_rows)
    assert sum(row["measurement_source"] == "blind_adjudication" for row in final_rows) == 32
    assert sum(row["measurement_source"] == "parser_confirmed" for row in final_rows) == 368
    return sorted(final_rows, key=lambda row: (row["model"], row["condition"], row["anchor"], row["row_i"]))


def _z_values(rows: list[dict[str, object]]) -> np.ndarray:
    return np.asarray([math.log1p(_float(row["final_estimate"])) for row in rows], dtype=float)


def _cell_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, int], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        groups[(str(row["model"]), str(row["condition"]), int(row["anchor"]))].append(row)
    result = []
    for (model, framing, anchor), cell_rows in sorted(groups.items()):
        y = np.asarray([_float(row["final_estimate"]) for row in cell_rows])
        z = _z_values(cell_rows)
        result.append(
            {
                "model": model,
                "framing": framing,
                "anchor": anchor,
                "n": int(len(cell_rows)),
                "median": float(np.median(y)),
                "mean": float(np.mean(y)),
                "log_median": float(np.median(z)),
            }
        )
    return result


def _grouped_cells(rows: list[dict[str, object]], framing: str) -> dict[tuple[str, int], list[dict[str, object]]]:
    groups: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        if row["condition"] == framing:
            groups[(str(row["model"]), int(row["anchor"]))].append(row)
    return groups


def _model_deltas(rows: list[dict[str, object]], framing: str) -> tuple[dict[str, dict[str, object]], float]:
    groups = _grouped_cells(rows, framing)
    models = sorted({model for model, _ in groups})
    output: dict[str, dict[str, object]] = {}
    deltas = []
    for model in models:
        anchors = sorted(anchor for current_model, anchor in groups if current_model == model)
        assert len(anchors) == 2
        low, high = anchors
        low_z = _z_values(groups[(model, low)])
        high_z = _z_values(groups[(model, high)])
        delta = float(np.median(high_z) - np.median(low_z))
        deltas.append(delta)
        output[model] = {
            "low_anchor": low,
            "high_anchor": high,
            "n_low": int(len(low_z)),
            "n_high": int(len(high_z)),
            "low_log_median": float(np.median(low_z)),
            "high_log_median": float(np.median(high_z)),
            "delta_log": delta,
        }
    assert len(deltas) == 2
    return output, float(np.mean(deltas))


def _permutation_p(rows: list[dict[str, object]], framing: str, provider_adjusted: bool = False) -> tuple[float, int]:
    rng = np.random.default_rng(SEED)
    if provider_adjusted:
        theta, strata = _provider_deltas(rows, framing)
        model_strata: dict[str, list[tuple[np.ndarray, int, int]]] = defaultdict(list)
        for stratum in strata:
            if not stratum["supported"]:
                continue
            model_strata[stratum["model"]].append(
                (stratum["z"], stratum["n_low"], stratum["n_high"])
            )
        permutation_deltas = []
        for _ in range(N_PERMUTATIONS):
            model_values = []
            for model in sorted(model_strata):
                provider_parts = []
                provider_weights = []
                for z, n_low, n_high in model_strata[model]:
                    n_total = len(z)
                    chosen = rng.choice(n_total, size=n_high, replace=False)
                    mask = np.zeros(n_total, dtype=bool)
                    mask[chosen] = True
                    delta = float(np.median(z[mask]) - np.median(z[~mask]))
                    provider_parts.append(delta)
                    provider_weights.append(n_total)
                model_values.append(float(np.average(provider_parts, weights=provider_weights)))
            permutation_deltas.append(float(np.mean(model_values)))
    else:
        model_cells, observed = _model_deltas(rows, framing)
        model_data = []
        for model in sorted(model_cells):
            info = model_cells[model]
            groups = _grouped_cells(rows, framing)
            low_z = _z_values(groups[(model, info["low_anchor"])])
            high_z = _z_values(groups[(model, info["high_anchor"])])
            model_data.append((np.concatenate([low_z, high_z]), len(high_z)))
        permutation_deltas = np.empty(N_PERMUTATIONS, dtype=float)
        for index in range(N_PERMUTATIONS):
            deltas = []
            for z, n_high in model_data:
                chosen = rng.choice(len(z), size=n_high, replace=False)
                mask = np.zeros(len(z), dtype=bool)
                mask[chosen] = True
                deltas.append(float(np.median(z[mask]) - np.median(z[~mask])))
            permutation_deltas[index] = np.mean(deltas)
    observed = theta if provider_adjusted else _model_deltas(rows, framing)[1]
    exceedances = int(np.count_nonzero(np.asarray(permutation_deltas) >= observed))
    return (1 + exceedances) / (N_PERMUTATIONS + 1), exceedances


def _bootstrap_ci(rows: list[dict[str, object]], framing: str) -> tuple[float, float]:
    rng = np.random.default_rng(SEED)
    groups = _grouped_cells(rows, framing)
    models = sorted({model for model, _ in groups})
    model_bootstraps = []
    for model in models:
        anchors = sorted(anchor for current_model, anchor in groups if current_model == model)
        anchor_bootstraps = []
        for anchor in anchors:
            z = _z_values(groups[(model, anchor)])
            indices = rng.integers(0, len(z), size=(N_BOOTSTRAPS, len(z)))
            anchor_bootstraps.append(np.median(z[indices], axis=1))
        model_bootstraps.append(anchor_bootstraps[1] - anchor_bootstraps[0])
    theta_bootstrap = np.mean(np.vstack(model_bootstraps), axis=0)
    return tuple(float(value) for value in np.percentile(theta_bootstrap, [2.5, 97.5]))


def _provider_deltas(rows: list[dict[str, object]], framing: str) -> tuple[float, list[dict[str, object]]]:
    groups: dict[tuple[str, str, int], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        if row["condition"] == framing:
            groups[(str(row["model"]), str(row["provider"]), int(row["anchor"]))].append(row)
    all_strata = []
    model_deltas = []
    for model in sorted({model for model, _, _ in groups}):
        providers = sorted({provider for current_model, provider, _ in groups if current_model == model})
        supported = []
        for provider in providers:
            anchors = sorted(anchor for current_model, current_provider, anchor in groups if current_model == model and current_provider == provider)
            if len(anchors) != 2:
                continue
            low, high = anchors
            low_rows = groups[(model, provider, low)]
            high_rows = groups[(model, provider, high)]
            n_low, n_high = len(low_rows), len(high_rows)
            item: dict[str, object] = {
                "model": model,
                "provider": provider,
                "low_anchor": low,
                "high_anchor": high,
                "n_low": n_low,
                "n_high": n_high,
                "supported": n_low >= 5 and n_high >= 5,
            }
            if item["supported"]:
                low_z = _z_values(low_rows)
                high_z = _z_values(high_rows)
                item["delta_log"] = float(np.median(high_z) - np.median(low_z))
                item["pooled_count"] = n_low + n_high
                item["z"] = np.concatenate([low_z, high_z])
                supported.append(item)
            all_strata.append(item)
        assert supported, f"no estimable provider strata for {model}/{framing}"
        model_deltas.append(
            float(
                np.average(
                    [item["delta_log"] for item in supported],
                    weights=[item["pooled_count"] for item in supported],
                )
            )
        )
    return float(np.mean(model_deltas)), all_strata


def _analysis_summary(rows: list[dict[str, object]], framing: str, universe: str, inference: bool = True) -> dict[str, object]:
    model_deltas, theta = _model_deltas(rows, framing)
    if inference:
        assert all(
            cell["n"] >= 10
            for cell in _cell_summary(rows)
            if cell["framing"] == framing
        ), "locked missingness threshold failed"
    result: dict[str, object] = {
        "universe": universe,
        "framing": framing,
        "n": sum(row["condition"] == framing for row in rows),
        "model_deltas": model_deltas,
        "theta_log": theta,
        "exp_theta_minus_1": math.expm1(theta),
    }
    if inference:
        p_value, exceedances = _permutation_p(rows, framing)
        ci = _bootstrap_ci(rows, framing)
        result["permutation"] = {
            "alternative": "high anchor greater than low anchor",
            "n_permutations": N_PERMUTATIONS,
            "seed": SEED,
            "exceedances_ge_observed": exceedances,
            "p_plus_one": p_value,
        }
        result["bootstrap"] = {
            "n_replicates": N_BOOTSTRAPS,
            "seed": SEED,
            "theta_log_ci_95_percentile": list(ci),
            "exp_theta_minus_1_ci_95_percentile": [math.expm1(ci[0]), math.expm1(ci[1])],
        }
    return result


def _provider_summary(rows: list[dict[str, object]], framing: str, universe: str) -> dict[str, object]:
    theta, strata = _provider_deltas(rows, framing)
    p_value, exceedances = _permutation_p(rows, framing, provider_adjusted=True)
    public_strata = [{key: value for key, value in item.items() if key != "z"} for item in strata]
    return {
        "universe": universe,
        "framing": framing,
        "criterion": "actual provider strata with >=5 valid rows in both anchor arms within model/framing",
        "weighting": "provider-specific median log differences weighted by fixed pooled counts within model; models equal-weighted",
        "theta_log": theta,
        "exp_theta_minus_1": math.expm1(theta),
        "permutation": {
            "alternative": "high anchor greater than low anchor",
            "within": "model-provider",
            "n_permutations": N_PERMUTATIONS,
            "seed": SEED,
            "exceedances_ge_observed": exceedances,
            "p_plus_one": p_value,
            "inference_label": "sensitivity only; not Holm-adjusted",
        },
        "provider_support": public_strata,
    }


def _write_final_estimates(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "blinded_id", "source_file", "row_i", "split", "model", "condition", "anchor", "provider",
        "parser_estimate", "parser_status", "final_estimate", "final_status", "measurement_source",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            output = dict(row)
            output["parser_estimate"] = _decimal_text(output["parser_estimate"])
            output["final_estimate"] = _decimal_text(output["final_estimate"])
            writer.writerow(output)


def _write_figure(path: Path, rows: list[dict[str, object]]) -> None:
    framings = [PRIMARY_FRAMING, SECONDARY_FRAMING]
    models = sorted({str(row["model"]) for row in rows})
    fig, axes = plt.subplots(len(models), len(framings), figsize=(12, 8), squeeze=False, sharey="row")
    rng = np.random.default_rng(SEED)
    for row_index, model in enumerate(models):
        for col_index, framing in enumerate(framings):
            ax = axes[row_index][col_index]
            cells = []
            for anchor in sorted({
                int(row["anchor"])
                for row in rows
                if row["model"] == model and row["condition"] == framing
            }):
                values = np.asarray([
                    _float(row["final_estimate"]) / 1_000_000
                    for row in rows
                    if row["model"] == model and row["condition"] == framing and int(row["anchor"]) == anchor and row["split"] == "holdout"
                ])
                cells.append((anchor, values))
            for x, (anchor, values) in enumerate(cells):
                jitter = rng.uniform(-0.075, 0.075, size=len(values))
                ax.scatter(np.full(len(values), x) + jitter, values, s=13, alpha=0.28, color="#2f6690", linewidths=0)
                median = float(np.median(values))
                ax.plot([x - 0.22, x + 0.22], [median, median], color="#d1495b", linewidth=3)
                ax.scatter([x], [median], color="#d1495b", s=34, zorder=3)
                ax.text(x, 0.02, f"{anchor / 1_000_000:g}M", transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=9)
            ax.set_xticks(range(len(cells)), ["Low anchor", "High anchor"])
            ax.set_title(f"{model.split('/')[-1]}\n{framing}")
            ax.set_yscale("log")
            ax.grid(axis="y", alpha=0.2)
            ax.set_ylabel("Final estimate (millions, log scale)")
    fig.suptitle("Holdout final estimates by anchor (medians shown)", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def _format(value: float) -> str:
    return f"{value:.6g}"


def _write_markdown(path: Path, results: dict[str, object]) -> None:
    primary = results["confirmatory_primary"]
    secondary = results["prespecified_secondary"]
    lines = [
        "# Threshold-anchoring analysis results",
        "",
        f"Locked plan SHA-256: `{results['plan_sha256']}`",
        "",
        "All estimates are the audited final estimates in `final_estimates.csv`. The outcome is "
        "`Z = ln(1 + Y)`; reported effects are `exp(theta) - 1`, with theta the equal-weighted "
        "mean of the two model-specific high-minus-low median log differences.",
        "",
        "## Confirmatory primary",
        "",
        f"Holdout rows `i=5..49`, framing `{primary['framing']}`, n={primary['n']}. "
        f"theta={_format(primary['theta_log'])}; exp(theta)-1={_format(primary['exp_theta_minus_1'])}. "
        f"95% percentile bootstrap CI for exp(theta)-1: "
        f"[{_format(primary['bootstrap']['exp_theta_minus_1_ci_95_percentile'][0])}, "
        f"{_format(primary['bootstrap']['exp_theta_minus_1_ci_95_percentile'][1])}]. "
        f"Directional permutation p+1={primary['permutation']['p_plus_one']:.8f}; "
        f"Holm-adjusted p={primary['holm_p_plus_one']:.8f}.",
        "",
        "## Pre-specified secondary",
        "",
        f"The identical locked test on holdout rows, framing `{secondary['framing']}`, n={secondary['n']}. "
        f"theta={_format(secondary['theta_log'])}; exp(theta)-1={_format(secondary['exp_theta_minus_1'])}. "
        f"95% percentile bootstrap CI for exp(theta)-1: "
        f"[{_format(secondary['bootstrap']['exp_theta_minus_1_ci_95_percentile'][0])}, "
        f"{_format(secondary['bootstrap']['exp_theta_minus_1_ci_95_percentile'][1])}]. "
        f"Directional permutation p+1={secondary['permutation']['p_plus_one']:.8f}; "
        f"Holm-adjusted p={secondary['holm_p_plus_one']:.8f}.",
        "",
        "Permutation tests use 100,000 within-model label shuffles, preserve anchor-arm counts, "
        "use seed 20260829, and use the plus-one correction. Bootstrap intervals use 10,000 "
        "model-by-anchor-stratified resamples and seed 20260829.",
        "",
        "## Descriptive and sensitivity analyses",
        "",
        "Model-specific outcomes are descriptive only; they are not separately tested. The all-400 "
        "analysis includes the five pilot rows per cell and is exploratory. Provider adjustment is "
        "reported as a sensitivity check using only estimable actual-provider strata, fixed pooled-count "
        "weights within model, equal model weights, and within model-provider permutations; it is not "
        "Holm-adjusted.",
        "",
        "### Cell summaries",
        "",
        "| Universe | Framing | Model | Anchor | n | Median Y | Mean Y | Median Z |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for cell in results["cell_summaries"]:
        lines.append(
            f"| {cell['universe']} | {cell['framing']} | {cell['model']} | {cell['anchor']:,} | "
            f"{cell['n']} | {cell['median']:,.0f} | {cell['mean']:,.2f} | {_format(cell['log_median'])} |"
        )
    lines += [
        "",
        "### Measurement and pilot accounting",
        "",
        f"Of 400 final-estimate rows, {results['measurement_counts']['parser_confirmed']} are "
        f"`parser_confirmed` and {results['measurement_counts']['blind_adjudication']} are "
        "`blind_adjudication`. Pilot rows `i=0..4` are excluded from both confirmatory analyses "
        "and appear only in the all-400 exploratory summaries.",
        "",
        "### Provider support",
        "",
        "Provider support details, including unsupported strata and the >=5-per-arm rule, are in "
        "`results.json` under `sensitivity.provider_adjusted`.",
        "",
        "No additional hypothesis tests or alternate outcome transformations were run.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(analysis_dir: Path) -> dict[str, object]:
    plan_hash = _assert_core_artifacts(analysis_dir)
    rows = build_final_estimates(analysis_dir)
    _write_final_estimates(analysis_dir / "final_estimates.csv", rows)

    holdout = [row for row in rows if row["split"] == "holdout" and 5 <= row["row_i"] <= 49]
    assert len(holdout) == 360
    all_rows = list(rows)
    framings = [PRIMARY_FRAMING, SECONDARY_FRAMING]
    primary = _analysis_summary(holdout, PRIMARY_FRAMING, "primary_holdout")
    secondary = _analysis_summary(holdout, SECONDARY_FRAMING, "secondary_holdout")
    p_values = [primary["permutation"]["p_plus_one"], secondary["permutation"]["p_plus_one"]]
    ordered = sorted(range(2), key=lambda index: (p_values[index], index))
    adjusted = [0.0, 0.0]
    running = 0.0
    for rank, index in enumerate(ordered):
        running = max(running, min(1.0, (2 - rank) * p_values[index]))
        adjusted[index] = running
    primary["holm_p_plus_one"] = adjusted[0]
    secondary["holm_p_plus_one"] = adjusted[1]

    all400 = {
        framing: _analysis_summary(all_rows, framing, "all_400_exploratory", inference=False)
        for framing in framings
    }
    provider_adjusted = {
        framing: _provider_summary(holdout, framing, "primary_holdout_provider_sensitivity")
        for framing in framings
    }

    cell_summaries = []
    for universe, universe_rows in [("primary_holdout", holdout), ("all_400_exploratory", all_rows)]:
        for cell in _cell_summary(universe_rows):
            cell["universe"] = universe
            cell_summaries.append(cell)

    measurement_counts = {
        "parser_confirmed": sum(row["measurement_source"] == "parser_confirmed" for row in rows),
        "blind_adjudication": sum(row["measurement_source"] == "blind_adjudication" for row in rows),
    }
    results: dict[str, object] = {
        "plan_sha256": plan_hash,
        "inputs": {
            "blinded_extractions_sha256": _sha256(analysis_dir / "blinded_extractions.csv"),
            "extraction_key_sha256": _sha256(analysis_dir / "extraction_key.csv"),
            "audit_all_sha256": _sha256(analysis_dir / "audit_all.csv"),
        },
        "audit_resolution": {
            "n_rows": 400,
            "n_disagreement_ids": 32,
            "disagreement_ids_equal_adjudication_ids": True,
            "n_parser_confirmed": measurement_counts["parser_confirmed"],
            "n_blind_adjudication": measurement_counts["blind_adjudication"],
            "all_final_estimates_nonnegative_and_present": True,
            "all_final_estimate_rows_have_unique_blinded_ids": True,
        },
        "measurement_counts": measurement_counts,
        "design": {
            "primary_rows": "i=5..49",
            "primary_n": 360,
            "pilot_rows": "i=0..4",
            "outcome": "Z=ln(1+Y), Y=final estimate",
            "models_equal_weighted": True,
            "model_specific_outcomes_descriptive_only": True,
        },
        "confirmatory_primary": primary,
        "prespecified_secondary": secondary,
        "sensitivity": {
            "all_400_exploratory": all400,
            "provider_adjusted": provider_adjusted,
        },
        "cell_summaries": cell_summaries,
        "output_files": [
            "final_estimates.csv",
            "results.json",
            "results.md",
            "holdout_distributions.png",
        ],
    }
    (analysis_dir / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_markdown(analysis_dir / "results.md", results)
    _write_figure(analysis_dir / "holdout_distributions.png", rows)
    return results


def main(analysis_dir: str = "analysis/hyp1_threshold_anchoring") -> None:
    results = run(Path(analysis_dir))
    primary = results["confirmatory_primary"]
    secondary = results["prespecified_secondary"]
    print(
        f"primary theta={primary['theta_log']:.12g} effect={primary['exp_theta_minus_1']:.12g} "
        f"p={primary['permutation']['p_plus_one']:.12g}"
    )
    print(
        f"secondary theta={secondary['theta_log']:.12g} effect={secondary['exp_theta_minus_1']:.12g} "
        f"p={secondary['permutation']['p_plus_one']:.12g}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-dir", default="analysis/hyp1_threshold_anchoring")
    args = parser.parse_args()
    main(args.analysis_dir)
