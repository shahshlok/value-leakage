"""Analyze the completed 40-response moral-direction pilot."""

from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import sys
import numpy as np
from collections import Counter, defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from value_leakage.anchoring_extract import PARSER_VERSION, parse_content

SEED = 20260829
BOOTSTRAPS = 10_000
CSV_FIELDS = ("opaque_id", "source_row", "model", "condition", "threshold",
              "extracted_numeric", "parser_status", "failure", "empty",
              "truncated", "outcome", "final_estimate", "measurement_source")
def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))
def opaque_id(cell_id: str, i: int) -> str:
    digest = hashlib.sha256(f"moral-pilot\0{cell_id}\0{i}".encode()).hexdigest()
    return f"p_{digest[:20]}"
def load_records(run: Path) -> list[dict]:
    config = read(run / "config.json")
    if config.get("observed_summary", {}).get("attempts_completed") != 40:
        raise AssertionError("the pilot has not finished all 40 attempts")
    cells = config.get("cells", [])
    if config.get("planned_attempts") != 40 or config.get("count_per_cell") != 10:
        raise AssertionError("config does not specify the completed 40-response plan")
    if len(cells) != 4 or len({c.get("cell_id") for c in cells}) != 4:
        raise AssertionError("config must define four unique cells")
    expected = {}
    for cell in cells:
        key = (cell["model_name"], cell["condition"], cell["anchor"])
        expected[key] = cell
    files = sorted(p for p in run.rglob("*.json") if p.name != "config.json")
    if len(files) != 4:
        raise AssertionError(f"expected exactly four response JSON files, found {len(files)}")
    records = []
    seen = set()
    for path in files:
        payload = read(path)
        key = (path.parent.name, payload.get("condition"), payload.get("threshold"))
        cell = expected.get(key)
        if cell is None or key in seen:
            raise AssertionError(f"unexpected or duplicate response cell: {path}")
        seen.add(key)
        if payload.get("model") != cell.get("model") or payload.get("condition") != cell["condition"]:
            raise AssertionError(f"response metadata disagrees with config: {path}")
        rows = payload.get("rows")
        if not isinstance(rows, list) or len(rows) != 10:
            raise AssertionError(f"{path} must contain exactly 10 rows")
        indices = [row.get("i") for row in rows if isinstance(row, dict)]
        if len(indices) != 10 or len(set(indices)) != 10 or set(indices) != set(range(10)):
            raise AssertionError(f"{path} must contain exactly unique i=0..9")
        for row in rows:
            content = row.get("content")
            failed = bool(row.get("error"))
            empty = not isinstance(content, str) or not content.strip()
            truncated = bool(row.get("truncated"))
            parsed = parse_content(content)  # visible content only; no custom parser
            status = parsed.status
            outcome = "unusable"
            if parsed.estimate is not None and status == "clear" and not failed and not empty and not truncated:
                outcome = "above_threshold" if parsed.estimate > cell["anchor"] else "below_threshold"
            records.append({
                "opaque_id": opaque_id(cell["cell_id"], row["i"]),
                "source_row": f"{path.relative_to(ROOT).as_posix()}:{row['i']}",
                "model": cell["model_name"], "condition": cell["condition"],
                "threshold": cell["anchor"],
                "extracted_numeric": "" if parsed.estimate is None else format(parsed.estimate, "f"),
                "parser_status": status, "failure": failed, "empty": empty,
                "truncated": truncated, "outcome": outcome,
                "visible_content": content if isinstance(content, str) else "",
                "provider": row.get("response_provider") or "unknown",
                "cost": (row.get("usage") or {}).get("cost", 0) or 0,
            })
    if seen != set(expected):
        raise AssertionError(f"missing configured cells: {set(expected) - seen}")
    if len(records) != 40 or len({r["opaque_id"] for r in records}) != 40:
        raise AssertionError("pilot must contain 40 unique response rows")
    return records
def bootstrap_ratio(above: list[float], below: list[float], seed: int) -> dict:
    if not above or not below or min(above + below) <= 0:
        return {"ratio": None, "bootstrap_95_ci": None}
    rng = np.random.default_rng(seed)
    draws = np.median(rng.choice(above, (BOOTSTRAPS, len(above))), axis=1) / np.median(
        rng.choice(below, (BOOTSTRAPS, len(below))), axis=1)
    return {"ratio": statistics.median(above) / statistics.median(below),
            "bootstrap_resamples": BOOTSTRAPS,
            "bootstrap_95_ci": np.quantile(draws, [0.025, 0.975]).tolist()}
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=ROOT / "runs/moral_pilot_qwen_pair")
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()
    records = load_records(args.run)
    for row in records:
        row["final_estimate"] = row["extracted_numeric"] if row["outcome"] != "unusable" else ""
        row["measurement_source"] = "parser_only"
    if args.audit:
        with args.audit.open(newline="", encoding="utf-8") as handle:
            audit_rows = list(csv.DictReader(handle))
        audit_by_id = {row["opaque_id"]: row for row in audit_rows}
        if len(audit_rows) != 40 or set(audit_by_id) != {r["opaque_id"] for r in records}:
            raise ValueError("audit must cover each of the 40 IDs exactly once")
        for row in records:
            audited = audit_by_id[row["opaque_id"]]
            if audited["status"] not in {"clear", "ambiguous"}:
                raise ValueError("unexpected audit status")
            row["final_estimate"] = ""
            row["measurement_source"] = "condition_label_hidden_audit"
            row["outcome"] = "unusable"
            if audited["status"] == "clear":
                value = float(audited["final_estimate"])
                if not math.isfinite(value) or value <= 0 or not audited["evidence"] or audited["evidence"] not in row["visible_content"]:
                    raise ValueError(f"invalid audit value or evidence: {row['opaque_id']}")
                if not row["failure"] and not row["empty"] and not row["truncated"]:
                    row["final_estimate"] = audited["final_estimate"]
                    row["outcome"] = "above_threshold" if value > row["threshold"] else "below_threshold"
    csv_rows = [{field: row[field] for field in CSV_FIELDS} for row in records]
    with (OUT / "pilot_extractions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader(); writer.writerows(csv_rows)
    audit = [{"opaque_id": r["opaque_id"], "visible_content": r["visible_content"]} for r in records]
    random.Random(SEED).shuffle(audit)
    (OUT / "pilot_audit_packet.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    cells = defaultdict(list)
    models = defaultdict(lambda: defaultdict(list))
    for cell in read(args.run / "config.json")["cells"]:
        cells[(cell["model_name"], cell["condition"], cell["anchor"])]
        models[cell["model_name"]]
    for row in records:
        if row["outcome"] != "unusable":
            cells[(row["model"], row["condition"], row["threshold"])].append(row)
            models[row["model"]][row["condition"]].append(float(row["final_estimate"]))
    cell_results = {}
    for key, rows in sorted(cells.items()):
        values = [float(r["final_estimate"]) for r in rows]
        cell_results["/".join(map(str, key))] = {"n_usable": len(rows), "median": statistics.median(values) if values else None}
    quality = {"failures": sum(r["failure"] for r in records), "empty": sum(r["empty"] for r in records),
               "truncated": sum(r["truncated"] for r in records),
               "parser_status": dict(sorted(Counter(r["parser_status"] for r in records).items()))}
    results = {"pilot": "exploratory_audited" if args.audit else "exploratory_unaudited", "parser_version": PARSER_VERSION,
               "seed": SEED, "n_records": len(records), "n_usable": sum(r["outcome"] != "unusable" for r in records),
               "cells": cell_results, "models": {m: bootstrap_ratio(v["above_good"], v["below_good"], SEED + i) for i, (m, v) in enumerate(sorted(models.items()))},
               "quality": quality,
               "providers": dict(sorted(Counter(r["provider"] for r in records).items())),
               "cost": sum(float(r["cost"]) for r in records),
               "audit_corrections_applied": bool(args.audit),
               "audit_path": str(args.audit) if args.audit else None,
               "audit_changed_or_resolved": sum(r["final_estimate"] != r["extracted_numeric"] for r in records) if args.audit else 0,
               "historical_samples_combined": False}
    (OUT / "pilot_results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    audit_note = "All 40 final answers reviewed with condition labels hidden; answer text itself may reveal the condition." if args.audit else "Unaudited parser output."
    lines = ["# Moral comparison pilot", "", f"Exploratory 40-response pilot. {audit_note}", "",
             "Aditya's original moral wording was reused. Within each model, only which side benefits the good cause changes; the threshold stays fixed.", "",
             "| Model | Threshold | Below-good median | Above-good median | Change |",
             "|---|---:|---:|---:|---:|"]
    for model, value in results["models"].items():
        selected = [r for r in records if r["model"] == model]
        threshold = selected[0]["threshold"]
        below = cell_results[f"{model}/below_good/{threshold}"]
        above = cell_results[f"{model}/above_good/{threshold}"]
        label = "Qwen 3.5" if "qwen3.5" in model else "Qwen 3.8"
        fmt = lambda v: "unavailable" if v is None else f"{v / 1e6:g}M"
        shift = "unavailable" if value["ratio"] is None else f"{(value['ratio'] - 1) * 100:+.0f}%"
        lines.append(f"| {label} | {fmt(threshold)} | {fmt(below['median'])} (n={below['n_usable']}) | {fmt(above['median'])} (n={above['n_usable']}) | {shift} |")
    lines += ["", "## Uncertainty", "", "Median-ratio intervals resample above-good and below-good independently (10,000 draws, seed 20260829). They are rough pilot intervals, not definitive evidence.", ""]
    for model, value in results["models"].items():
        ci = value["bootstrap_95_ci"]
        label = "Qwen 3.5" if "qwen3.5" in model else "Qwen 3.8"
        interval = "unavailable" if ci is None else f"{(ci[0]-1)*100:+.0f}% to {(ci[1]-1)*100:+.0f}%"
        lines.append(f"- {label}: 95% interval for the median change: {interval}.")
    lines += ["", "## What this tells us", "",
              "If above-good estimates exceed below-good estimates, this is consistent with sensitivity to the moral consequence beyond a direction-insensitive numerical anchor. It does not identify where the effect enters reasoning or establish human-like motivation.", "",
              "Only 10 responses per condition were generated. OpenRouter chose multiple providers. Do not claim a stable model ranking or treat a null-compatible interval as proof of no effect.", "",
              "The earlier neutral results and Aditya's data are reference points only. Neutral wording and generation batches differ. Historical Qwen 3.8 used Fireworks and a 39.5M threshold, versus OpenRouter and 40M here.", "",
              "## Data quality and files", "",
              f"Completed: {results['n_records']}; usable after measurement: {results['n_usable']}. Recorded cost: ${results['cost']:.6f}.",
              f"Quality counts: `{results['quality']}`. The parser's five flagged answers remain recorded even after audit resolution.",
              f"Audit changes or resolutions: {results['audit_changed_or_resolved']}. Providers: `{results['providers']}`.", "",
              "Raw data: `runs/moral_pilot_qwen_pair/`. Numerical results: `pilot_results.json`. Row-level estimates and mapping: `pilot_extractions.csv`. Audit evidence: `pilot_audit.csv`. Historical check: `historical_check.md`.", "",
              "Reproduce: `uv run --offline python analysis/hyp1_moral_comparison/pilot_analyze.py --audit analysis/hyp1_moral_comparison/pilot_audit.csv`.", ""]
    (OUT / "pilot_summary.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
