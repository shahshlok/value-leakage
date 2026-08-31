"""Offline field-level validation and usage summary for completed OpenCode pilots."""

import argparse
import json
from pathlib import Path

FIELDS = {"mentions_incentive", "impartiality_claim", "quote", "confidence"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.run_dir
    results_path = args.results or root / "raw_judge_outputs.jsonl"
    rows = [json.loads(line) for line in results_path.read_text().splitlines()]
    manifest = json.loads((root / "manifest.json").read_text())
    assert len(rows) == len({r["trace_id"] for r in rows}) == len(manifest["selection"])
    issues, quote_warnings = {}, {}
    for row in rows:
        rid = row["trace_id"]
        p = row.get("parsed")
        problems = []
        if row["http_status"] != "200" or row["curl_exit_code"] or row["finish_reason"] != "stop":
            problems.append("request_or_completion_failure")
        if not isinstance(p, dict) or set(p) != FIELDS:
            problems.append("invalid_json_or_fields")
        else:
            if any(type(p[f]) is not bool for f in ("impartiality_claim", "mentions_incentive")):
                problems.append("nonboolean_label")
            if type(p["confidence"]) not in (int, float) or not 0 <= p["confidence"] <= 1:
                problems.append("invalid_confidence")
            if not isinstance(p["quote"], str):
                problems.append("invalid_quote_type")
            elif p["impartiality_claim"] and not p["quote"].strip():
                problems.append("missing_positive_evidence")
            else:
                request = json.loads((root / "requests" / f"{rid}.json").read_text())
                source = request["messages"][1]["content"]
                if p["impartiality_claim"] and p["quote"] not in source:
                    quote_warnings[rid] = p["quote"]
                elif not p["impartiality_claim"] and p["quote"]:
                    quote_warnings[rid] = p["quote"]
        if problems:
            issues[rid] = problems
    usable = [row for row in rows if row["trace_id"] not in issues]
    fields = {}
    for field in ("impartiality_claim", "mentions_incentive"):
        valid = [r for r in rows if isinstance(r.get("parsed"), dict) and type(r["parsed"].get(field)) is bool
                 and r["http_status"] == "200" and r["finish_reason"] == "stop"]
        fields[field] = {"n_boolean_labels": len(valid), "n_positive": sum(r["parsed"][field] for r in valid)}
    assert all(r["judge_model"] == "glm-5.3-flash" for r in rows), "Pricing is specific to GLM-5.3-Flash"
    usage = [r["usage"] for r in rows if isinstance(r.get("usage"), dict)]
    usage_complete = len(usage) == len(rows)
    prompt = sum(u["prompt_tokens"] for u in usage)
    completion = sum(u["completion_tokens"] for u in usage)
    cached = sum((u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) for u in usage)
    reasoning = [r["reasoning_tokens"] for r in rows if type(r.get("reasoning_tokens")) is int]
    price_equivalent = ((prompt - cached) * .15 + cached * .03 + completion * .5) / 1_000_000
    result = {
        "n_selected": len(rows), "n_complete_valid_records": len(usable),
        "field_level_labels": fields, "validation_issues": issues, "quote_warnings": quote_warnings,
        "prompt_tokens": prompt, "cached_prompt_tokens": cached, "completion_tokens": completion,
        "usage_reported_n": len(usage), "usage_complete": usage_complete,
        "reasoning_tokens_reported_n": len(reasoning), "reasoning_tokens": sum(reasoning),
        "mean_reasoning_tokens": sum(reasoning) / len(reasoning) if reasoning else None,
        "max_reasoning_tokens": max(reasoning) if reasoning else None,
        "token_price_equivalent_usd": price_equivalent,
        "projected_1000_usd": price_equivalent * 1000 / len(rows) if usage_complete else None,
        "latency_max_seconds": max(r["elapsed_seconds"] for r in rows),
        "pricing_per_million_usd": {"input": .15, "cached_input": .03, "output": .5},
        "pricing_source": "https://opencode.ai/docs/go/#usage-limits",
        "pricing_checked_date": "2026-08-30",
        "caveat": "Token-price equivalent for reported usage only, not verified Go debit or quota impact; missing usage does not imply zero cost. No full projection if usage is incomplete. Minor quote differences require semantic review, not automatic failure. Inspected pilot traces are development data.",
    }
    (args.output or root / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
