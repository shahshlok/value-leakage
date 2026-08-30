"""Minimal exploratory check of the saved historical Qwen moral runs."""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from value_leakage.anchoring_extract import PARSER_VERSION, parse_content
from value_leakage.sample import build_prompt


HISTORICAL = {
    "qwen3.5-122b-a10b": "runs/qwen3.5-122b-a10b_20260815_030702",
    "qwen3.8-2.4t-a95b": "runs/qwen3p8-2p4t-a95b_20260815_030703",
}
FRESH_THRESHOLDS = {
    "qwen3.5-122b-a10b": 41_000_000,
    "qwen3.8-2.4t-a95b": 40_000_000,
}
NEUTRAL = {
    "qwen3.5-122b-a10b": ("runs/anchoring_pilot_qwen_pair/qwen3.5-122b-a10b/neutral_boundary_41000000.json", 41_000_000),
    "qwen3.8-2.4t-a95b": ("runs/anchoring_pilot_qwen_pair/qwen3p8-2p4t-a95b/neutral_boundary_40000000.json", 40_000_000),
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source(path: Path, field: str) -> dict[str, str]:
    return {"path": rel(path), "sha256": sha256(path), "field": field}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def prompt_record(path: Path, prompt: str, condition: str, threshold: int) -> dict:
    expected = build_prompt(condition, threshold)
    return {
        "condition": condition,
        "threshold": threshold,
        "text": prompt,
        "sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "builder_sha256": hashlib.sha256(expected.encode()).hexdigest(),
        "builder_match": prompt == expected,
        "source": source(path, "prompt"),
        "builder_source": {
            "path": "src/value_leakage/sample.py",
            "symbol": "build_prompt / BELOW_GOOD / ABOVE_GOOD",
        },
    }


def prompt_parts(prompt: str) -> tuple[str, str, str]:
    prefix, note = prompt.split("\n\nNote:", 1)
    clause, suffix = note.split("\n\nSo,", 1)
    return prefix, clause, suffix


def final_summary(path: Path, indices=None) -> dict:
    payload = load(path)
    rows = payload["rows"]
    selected = rows if indices is None else [rows[i] for i in indices]
    parsed = [parse_content(row.get("content")) for row in selected]
    values = [item.estimate for item in parsed if item.estimate is not None]
    status = Counter(item.status for item in parsed)
    rules = Counter(item.rule for item in parsed)
    return {
        "n_rows": len(selected),
        "n_clear": status["clear"],
        "n_ambiguous": status["ambiguous"],
        "n_missing": status["missing"],
        "n_invalid_or_missing": len(selected) - len(values),
        "median_clear": int(statistics.median(values)) if values else None,
        "parser_rule_counts": dict(sorted(rules.items())),
        "raw_error_rows": sum("error" in row for row in selected),
        "raw_empty_content_rows": sum(not (row.get("content") or "").strip() for row in selected),
        "source": source(path, "rows[*].content"),
        "parser": PARSER_VERSION,
    }


def historical_record(name: str, run: str) -> dict:
    run_path = ROOT / run
    config_path = run_path / "config.json"
    threshold_path = run_path / "threshold.json"
    config = load(config_path)
    threshold_data = load(threshold_path)
    moral = {}
    for condition in ("below_good", "above_good"):
        path = run_path / f"{condition}.json"
        payload = load(path)
        moral[condition] = {
            "summary": final_summary(path),
            "saved_payload": {
                "model": payload["model"],
                "backend": payload["backend"],
                "provider": payload.get("provider"),
                "threshold": payload["threshold"],
                "max_tokens": payload["max_tokens"],
                "reasoning_effort": payload["reasoning_effort"],
            },
            "prompt": prompt_record(path, payload["prompt"], condition, threshold_data["threshold"]),
        }
    below_parts = prompt_parts(moral["below_good"]["prompt"]["text"])
    above_parts = prompt_parts(moral["above_good"]["prompt"]["text"])
    estimates = load(run_path / "estimates.json")
    threshold = threshold_data["threshold"]
    return {
        "model_label": name,
        "model_id": config["model_id"],
        "run": run,
        "config": {
            key: config[key]
            for key in ("model_id", "backend", "provider", "target_max_tokens", "target_reasoning_effort", "judge_model")
        },
        "threshold": {
            **threshold_data,
            "source": source(threshold_path, "threshold/n_baseline/n_valid/unknown_rate"),
        },
        "moral_threshold_equal": (
            moral["below_good"]["saved_payload"]["threshold"]
            == moral["above_good"]["saved_payload"]["threshold"]
            == threshold
        ),
        "prompt_builder_matches": {
            condition: moral[condition]["prompt"]["builder_match"]
            for condition in moral
        },
        "prompt_base_and_suffix_equal": below_parts[0] == above_parts[0] and below_parts[2] == above_parts[2],
        "moral": moral,
        "estimates_json_keys": sorted(estimates),
        "moral_final_estimates_stored": all(
            condition in estimates for condition in ("below_good", "above_good")
        ),
        "trajectories_json_keys": sorted(load(run_path / "trajectories.json")),
        "reasoning_or_trajectory_used_for_medians": False,
    }


def neutral_context(name: str, raw_path: str, threshold: int) -> dict:
    raw = ROOT / raw_path
    final_path = ROOT / "analysis/hyp1_threshold_anchoring/final_estimates.csv"
    with final_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    model_id = load(raw)["model"]
    cell = [
        row for row in rows
        if row["model"] == model_id
        and row["condition"] == "neutral_boundary"
        and row["anchor"] == str(threshold)
        and row["split"] == "holdout"
    ]
    values = [int(row["final_estimate"]) for row in cell]
    return {
        "model_label": name,
        "model_id": model_id,
        "threshold": threshold,
        "n_holdout": len(cell),
        "median_audited_final_estimate": int(statistics.median(values)),
        "measurement_sources": dict(Counter(row["measurement_source"] for row in cell)),
        "raw_response_providers": dict(Counter(row["provider"] for row in cell)),
        "source": source(final_path, "final_estimate; condition=neutral_boundary; split=holdout"),
        "raw_source": source(raw, "rows[*].content/response_provider"),
        "not_used_for_historical_moral_medians": True,
    }


def markdown(report: dict) -> str:
    lines = [
        "# Historical Qwen moral-direction check",
        "",
        "Exploratory descriptive check only; no significance testing. Historical moral medians use the existing `anchoring_extract.v3` helper on the stored visible `rows[*].content` field. Reasoning and trajectories are not used.",
        "",
        "## Signal",
        "",
        "| Model ID | Historical threshold | above_good (clear/n) | below_good (clear/n) | above − below |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in report["historical"].values():
        above = item["moral"]["above_good"]["summary"]
        below = item["moral"]["below_good"]["summary"]
        lines.append(
            f"| `{item['model_id']}` | {item['threshold']['threshold']:,} | "
            f"{above['median_clear']:,} ({above['n_clear']}/{above['n_rows']}) | "
            f"{below['median_clear']:,} ({below['n_clear']}/{below['n_rows']}) | "
            f"{above['median_clear'] - below['median_clear']:,} |"
        )
    lines += [
        "",
        "Counts below are explicit parser outcomes; ambiguous and missing rows were not imputed.",
        "",
        "| Model | Condition | Clear | Ambiguous | Missing | Raw errors | Parser rules |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for item in report["historical"].values():
        for condition in ("above_good", "below_good"):
            summary = item["moral"][condition]["summary"]
            lines.append(
                f"| `{item['model_label']}` | `{condition}` | {summary['n_clear']} | "
                f"{summary['n_ambiguous']} | {summary['n_missing']} | {summary['raw_error_rows']} | "
                f"`{summary['parser_rule_counts']}` |"
            )
    lines += ["", "## Threshold and prompt checks", ""]
    for item in report["historical"].values():
        threshold = item["threshold"]["threshold"]
        fresh = report["fresh_prompt_templates"][item["model_label"]]
        lines += [
            f"- `{item['model_id']}`: historical moral threshold is **{threshold:,}** in both conditions; "
            f"`moral_threshold_equal={item['moral_threshold_equal']}` and saved prompts match `build_prompt` "
            f"for both conditions (`{item['prompt_builder_matches']}`); "
            f"shared prompt base/suffix equality is `{item['prompt_base_and_suffix_equal']}`.",
            f"- Fresh moral threshold is **{fresh['threshold']:,}**; numeric difference from historical is "
            f"**{fresh['threshold'] - threshold:+,}**; numeric-only prompt matches are "
            f"`{ {condition: fresh[condition]['numeric_only_match_to_historical'] for condition in ('below_good', 'above_good')} }`. "
            f"Fresh wording is the original builder output; this historical check does not use fresh moral responses.",
        ]
    lines += [
        "",
        "The original saved moral wording is defined by [`sample.py`](</Users/shlok/value-leakage/src/value_leakage/sample.py:29>) and the exact saved prompt strings are retained in `historical_check.json`. The only historical-to-fresh wording change is the inserted threshold number.",
        "",
        "## Neutral low-anchor context",
        "",
        "These are existing audited neutral holdout medians, shown descriptively only and not used in the historical moral comparison:",
        "",
        "| Model | Threshold | Audited median | n |",
        "|---|---:|---:|---:|",
    ]
    for item in report["neutral_low_anchor_context"].values():
        lines.append(f"| `{item['model_id']}` | {item['threshold']:,} | {item['median_audited_final_estimate']:,} | {item['n_holdout']} |")
    lines += [
        "",
        "Qwen3.5 historical and fresh low thresholds are both 41,000,000. Qwen3.8 historical is 39,500,000 while fresh is 40,000,000 (+500,000). Provider routing and serving differ across runs, so this is not a causal cross-run comparison.",
        "",
        "## Reproduction",
        "",
        "Run from the repository root with `UV_CACHE_DIR=/private/tmp/value-leakage-uv-cache uv run --offline python analysis/hyp1_moral_comparison/historical_check.py`. Inputs, fields, parser version, and SHA-256 hashes are recorded in [`historical_check.json`](</Users/shlok/value-leakage/analysis/hyp1_moral_comparison/historical_check.json>).",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    historical = {name: historical_record(name, run) for name, run in HISTORICAL.items()}
    fresh = {}
    for name, threshold in FRESH_THRESHOLDS.items():
        historical_threshold = historical[name]["threshold"]["threshold"]
        fresh[name] = {
            "threshold": threshold,
            "historical_threshold": historical_threshold,
            "threshold_difference_from_historical": threshold - historical_threshold,
            "below_good": {"text": build_prompt("below_good", threshold), "source": "src/value_leakage/sample.py:29-36"},
            "above_good": {"text": build_prompt("above_good", threshold), "source": "src/value_leakage/sample.py:38-45"},
            "saved_response_payload_present": False,
        }
        for condition in ("below_good", "above_good"):
            historical_prompt = historical[name]["moral"][condition]["prompt"]["text"]
            old_number = f"{historical_threshold:,}"
            new_number = f"{threshold:,}"
            fresh[name][condition]["numeric_only_match_to_historical"] = (
                historical_prompt.replace(old_number, new_number) == fresh[name][condition]["text"]
            )
    report = {
        "scope": "exploratory historical above_good vs below_good check",
        "historical": historical,
        "fresh_prompt_templates": fresh,
        "neutral_low_anchor_context": {
            name: neutral_context(name, path, threshold)
            for name, (path, threshold) in NEUTRAL.items()
        },
    }
    (OUT / "historical_check.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "historical_check.md").write_text(markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
