"""Prepare condition-hidden audit packets and assemble audited final estimates."""
import argparse
import csv
import hashlib
import json
import math
import random
from pathlib import Path

from value_leakage.anchoring_extract import parse_content
from pilot_analyze import opaque_id as pilot_id

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = ROOT / "runs/moral_full_qwen_pair"


def read(path):
    return json.loads(path.read_text())


def write_csv(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def records():
    config = read(RUN / "config.json")
    rows, contents = [], {}
    for cell in config["cells"]:
        path = RUN / f"{cell['cell_id']}.json"
        payload = read(path)
        assert payload["prompt"] == cell["prompt"]
        assert payload["model"] == cell["model"]
        assert payload["threshold"] == cell["anchor"]
        assert len(payload["rows"]) == 50
        assert [r["i"] for r in payload["rows"]] == list(range(50))
        for row in payload["rows"]:
            assert row["outcome"] == "success" and row["content"].strip() and not row["truncated"]
            split, i = row["source_split"], row["source_i"]
            assert split == ("pilot" if row["i"] < 10 else "extension")
            assert i == row["i"] - (0 if split == "pilot" else 10)
            digest = hashlib.sha256(f"extension|{cell['cell_id']}|{i}".encode()).hexdigest()[:20]
            ident = pilot_id(cell["cell_id"], i) if split == "pilot" else f"e_{digest}"
            parsed = parse_content(row["content"])
            rows.append(dict(opaque_id=ident, model=cell["model_name"], model_id=cell["model"],
                             condition=cell["condition"], threshold=cell["anchor"], split=split,
                             combined_i=row["i"], source_file=row["source_file"], source_i=i,
                             request_id=row["request_id"], provider=row["response_provider"],
                             parser_status=parsed.status,
                             parser_estimate="" if parsed.estimate is None else str(parsed.estimate)))
            contents[ident] = row["content"]
    assert len(rows) == len(contents) == len({r["request_id"] for r in rows}) == 200
    assert sum(r["split"] == "extension" for r in rows) == 160
    for split, sources in config["source_file_hashes"].items():
        for name, expected in sources.items():
            path = ROOT / f"runs/moral_{'pilot' if split == 'pilot' else 'extension'}_qwen_pair/config.json" if name == "config.json" else ROOT / name
            assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    return rows, contents


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()
    rows, contents = records()
    if not args.finalize:
        write_csv(OUT / "full_parser.csv", rows)
        packets = [dict(opaque_id=r["opaque_id"], visible_content=contents[r["opaque_id"]]) for r in rows if r["split"] == "extension"]
        random.Random(20260830).shuffle(packets)
        for suffix, packet in (("a", packets[:80]), ("b", packets[80:])):
            (OUT / f"full_audit_packet_{suffix}.json").write_text(json.dumps(packet, indent=2))
        manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in RUN.rglob("*.json")}
        (OUT / "full_source_manifest.json").write_text(json.dumps(manifest, indent=2))
        print("Validated 200 rows; prepared two condition-label-hidden 80-answer audit packets.")
        return
    with (OUT / "pilot_audit.csv").open(newline="") as handle:
        audited = list(csv.DictReader(handle))
    for suffix in ("a", "b"):
        audited.extend(read(OUT / f"full_audit_{suffix}.json"))
    by_id = {r["opaque_id"]: r for r in audited}
    assert len(audited) == len(by_id) == 200 and set(by_id) == set(contents)
    differences = []
    for row in rows:
        audit = by_id[row["opaque_id"]]
        assert audit["status"] in {"clear", "ambiguous"}
        row.update(final_estimate="", audit_status=audit["status"], evidence=audit["evidence"],
                   measurement_source="condition_label_hidden_review")
        if audit["status"] == "clear":
            value = float(audit["final_estimate"])
            assert math.isfinite(value) and value >= 0
            assert audit["evidence"] and audit["evidence"] in contents[row["opaque_id"]]
            row["final_estimate"] = value
        if row["parser_estimate"] == "" or row["final_estimate"] == "" or float(row["parser_estimate"]) != row["final_estimate"]:
            differences.append({**row, "visible_content": contents[row["opaque_id"]]})
    write_csv(OUT / "full_estimates.csv", rows)
    (OUT / "full_audit_differences.json").write_text(json.dumps(differences, indent=2))
    print(f"Assembled {len(rows)} audited rows; {len(differences)} parser/audit differences or unresolved cases for review.")


if __name__ == "__main__":
    main()
