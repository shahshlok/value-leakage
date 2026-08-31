"""Offline validation of the v3 judge outputs. Makes no API calls.

Run with: uv run python analysis/hyp6_impartiality/pilot/validate_pilot.py
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from run_pilot import build_selection


ROOT = Path(__file__).resolve().parent
FIELDS = {"mentions_incentive", "impartiality_claim", "quote", "confidence"}


def validate(record, source):
    problems = []
    if record.get("error"):
        problems.append("api_error")
    if record.get("finish_reason") != "stop":
        problems.append("finish_reason_not_stop")
    for output_key, source_key in (
        ("model", "model_dir"), ("condition", "condition"), ("row_i", "row_i")
    ):
        if record.get(output_key) != source[source_key]:
            problems.append("source_mismatch_" + output_key)
    try:
        parsed = json.loads(record.get("raw_content") or "")
    except (json.JSONDecodeError, TypeError):
        return problems + ["not_strict_json"]
    if not isinstance(parsed, dict) or set(parsed) != FIELDS:
        return problems + ["wrong_fields"]
    if parsed != record.get("parsed"):
        problems.append("saved_parse_mismatch")
    for field in ("mentions_incentive", "impartiality_claim"):
        if type(parsed[field]) is not bool:
            problems.append("not_boolean_" + field)
    confidence = parsed["confidence"]
    if type(confidence) not in (int, float) or not 0 <= confidence <= 1:
        problems.append("invalid_confidence")
    quote = parsed["quote"]
    if not isinstance(quote, str):
        problems.append("quote_not_string")
    elif parsed["impartiality_claim"] is True:
        if not quote.strip() or quote not in source["reasoning"]:
            problems.append("positive_quote_not_verbatim")
    elif parsed["impartiality_claim"] is False and quote != "":
        problems.append("negative_quote_not_empty")
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=ROOT / "raw_judge_outputs.jsonl")
    parser.add_argument("--manifest", type=Path, default=ROOT / "v3_run_manifest.json")
    parser.add_argument("--output", type=Path, default=ROOT / "v3_validation.json")
    args = parser.parse_args()
    selection = {x["trace_id"]: x for x in build_selection()}
    records = [json.loads(line) for line in args.results.read_text().splitlines()]
    manifest = json.loads(args.manifest.read_text())
    for item in manifest["selection"]:
        assert hashlib.sha256(selection[item["trace_id"]]["reasoning"].encode()).hexdigest() == item["reasoning_sha256"]
    ids = Counter(r["trace_id"] for r in records)
    assert set(ids) == set(selection) and all(n == 1 for n in ids.values()), "Missing/duplicate/unexpected trace IDs"
    checks = {r["trace_id"]: validate(r, selection[r["trace_id"]]) for r in records}
    valid = [r for r in records if not checks[r["trace_id"]]]
    tokens = [r["reasoning_tokens"] for r in records if type(r.get("reasoning_tokens")) is int]
    summary = {
        "n_selected": len(selection),
        "n_returned": len(records),
        "n_valid": len(valid),
        "impartiality_positive": sum(r["parsed"]["impartiality_claim"] for r in valid),
        "incentive_positive": sum(r["parsed"]["mentions_incentive"] for r in valid),
        "validation_problems": {k:v for k,v in checks.items() if v},
        "finish_reasons": dict(Counter(r.get("finish_reason") for r in records)),
        "reasoning_tokens_reported": len(tokens),
        "mean_reasoning_tokens": sum(tokens)/len(tokens) if tokens else None,
        "max_reasoning_tokens": max(tokens) if tokens else None,
        "actual_cost": "Actual billed cost not established by this validator; do not infer it from reasoning tokens alone.",
        "interpretation": "Judge-label prevalence in this 30-trace incentivized pilot, not human-validated accuracy or evidence of unfaithfulness.",
    }
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
