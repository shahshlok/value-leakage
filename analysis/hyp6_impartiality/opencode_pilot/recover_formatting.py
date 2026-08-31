"""Reproduce the three post-hoc formatting recoveries without changing labels.

No API calls. Raw content is retained; recovered quotes must match the source.
This is a pilot diagnostic, not evidence that the server enforced JSON schema.
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    spec = importlib.util.spec_from_file_location("pilot", ROOT.parent / "pilot" / "run_pilot.py")
    pilot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pilot)
    sources = {x["trace_id"]: x["reasoning"] for x in pilot.build_selection()}
    rows = [json.loads(line) for line in (ROOT / "raw_judge_outputs.jsonl").read_text().splitlines()]
    repaired = []
    for row in rows:
        if row["parsed"] is not None:
            continue
        text = row["raw_content"].strip()
        assert text.startswith("```json") and text.endswith("```"), "Unexpected failure; manual review needed"
        text = text.removeprefix("```json").removesuffix("```").strip()
        text = text.replace(chr(92) + "n", "\n").replace(chr(92) * 2 + '"', chr(92) + '"').strip()
        parsed = json.loads(text)
        assert set(parsed) == {"mentions_incentive", "impartiality_claim", "quote", "confidence"}
        assert type(parsed["mentions_incentive"]) is bool and type(parsed["impartiality_claim"]) is bool
        assert type(parsed["confidence"]) in (int, float) and 0 <= parsed["confidence"] <= 1
        assert isinstance(parsed["quote"], str)
        if parsed["impartiality_claim"]:
            assert parsed["quote"] and parsed["quote"] in sources[row["trace_id"]]
        else:
            assert parsed["quote"] == ""
        row["parsed"] = parsed
        row["formatting_recovery_applied"] = True
        row["formatting_recovery_method"] = "Remove JSON fences, decode literal newline formatting and one excess backslash before quotes; verify recovered supporting quote against source."
        repaired.append(row["trace_id"])
    (ROOT / "format_recovered_outputs.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    print("Recovered formatting only for:", ", ".join(repaired))


if __name__ == "__main__":
    main()
