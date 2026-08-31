"""Compare independent Terra labels with the pilot; no network calls."""

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / "terra_audit"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--judge-output", type=Path, default=ROOT / "raw_judge_outputs.jsonl")
    parser.add_argument("--output", type=Path, default=AUDIT / "agreement.json")
    args = parser.parse_args()
    mapping = json.loads((AUDIT / "private_mapping.json").read_text())["mapping"]
    pilot = {x["trace_id"]: x for x in (
        json.loads(line) for line in args.judge_output.read_text().splitlines()
    )}
    labels = json.loads((AUDIT / "terra_labels.json").read_text())
    terra = {x["audit_id"]: x for x in labels}
    assert len(labels) == len(terra) == len(mapping) == 15
    assert set(terra) == {x["audit_id"] for x in mapping}
    comparisons = []
    unavailable = []
    for item in mapping:
        a = terra[item["audit_id"]]
        b = pilot[item["trace_id"]].get("parsed")
        if (not isinstance(b, dict)
                or any(type(b.get(f)) is not bool for f in ("impartiality_claim", "mentions_incentive"))
                or pilot[item["trace_id"]].get("finish_reason") != "stop"):
            unavailable.append(item)
            continue
        for field in ("impartiality_claim", "mentions_incentive"):
            assert type(a[field]) is bool and type(b[field]) is bool
        source = (AUDIT / "blind" / f"{item['audit_id']}.txt").read_text()
        assert isinstance(a["quote"], str)
        if a["impartiality_claim"]:
            assert a["quote"].strip() and a["quote"] in source, f"Nonverbatim Terra quote: {item['audit_id']}"
        else:
            assert a["quote"] == ""
        comparisons.append({
            **item,
            "judge_impartiality": b["impartiality_claim"],
            "terra_impartiality": a["impartiality_claim"],
            "impartiality_agree": a["impartiality_claim"] == b["impartiality_claim"],
            "incentive_agree": a["mentions_incentive"] == b["mentions_incentive"],
            "judge_quote": b.get("quote"),
            "terra_quote": a["quote"],
            "terra_note": a.get("note", ""),
        })
    summary = {
        "judge_results_file": str(args.judge_output.resolve()),
        "judge_models": sorted({x["judge_model"] for x in pilot.values()}),
        "n_audited": len(mapping),
        "n_compared": len(comparisons),
        "unavailable_judge_labels": unavailable,
        "impartiality_agreements": sum(x["impartiality_agree"] for x in comparisons),
        "incentive_agreements": sum(x["incentive_agree"] for x in comparisons),
        "impartiality_table_judge_then_terra": dict(Counter(
            f"{x['judge_impartiality']}/{x['terra_impartiality']}" for x in comparisons
        )),
        "disagreements": [x for x in comparisons if not x["impartiality_agree"] or not x["incentive_agree"]],
        "limitation": "Independent LLM agreement on a small development sample; not human-validated accuracy or proof of CoT faithfulness.",
        "comparisons": comparisons,
    }
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k:v for k,v in summary.items() if k != "comparisons"}, indent=2))


if __name__ == "__main__":
    main()
