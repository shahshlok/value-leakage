"""Offline answer-only pass. Never reads judge outputs or private reasoning."""

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from value_leakage.anchoring_extract import PARSER_VERSION, parse_content

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def main():
    manifest = json.loads((OUT / "manifest.json").read_text())
    payloads, source_hashes, answers, key = {}, {}, [], []
    for selected in manifest["selection"]:
        path = ROOT / "runs" / selected["model_dir"] / (selected["condition"] + ".json")
        if path not in payloads:
            source_hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
            payloads[path] = json.loads(path.read_text())
        payload = payloads[path]
        source = next(row for row in payload["rows"] if row["i"] == selected["row_i"])
        # Only the visible response is passed into the deterministic parser.
        content = source.get("content")
        result = parse_content(content)
        answers.append({
            "trace_id": selected["trace_id"],
            "estimate": "" if result.estimate is None else str(result.estimate),
            "parser_status": result.status,
            "parser_rule": result.rule,
            "answer_excerpt": result.excerpt,
            "content_sha256": hashlib.sha256((content or "").encode()).hexdigest(),
            "source_finish_reason": source.get("finish_reason"),
        })
        key.append({
            "trace_id": selected["trace_id"], "model_dir": selected["model_dir"],
            "condition": selected["condition"], "row_i": selected["row_i"],
            "threshold": payload["threshold"],
        })
    for filename, rows in (("answer_only_extractions.csv", answers), ("answer_key.csv", key)):
        with (OUT / filename).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    metadata = {
        "n": len(answers), "parser_version": PARSER_VERSION,
        "parser_source_sha256": hashlib.sha256((ROOT / "src/value_leakage/anchoring_extract.py").read_bytes()).hexdigest(),
        "statuses": dict(Counter(row["parser_status"] for row in answers)),
        "source_file_sha256": source_hashes,
        "note": "Deterministic extraction from visible content only, before joining judge labels. Ambiguous/missing answers remain unresolved. This parser has not been independently audited on this sample.",
    }
    (OUT / "answer_extraction_manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({k: metadata[k] for k in ("n", "parser_version", "statuses")}, indent=2))


if __name__ == "__main__":
    main()
