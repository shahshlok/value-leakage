"""Consolidate completed moral pilot and extension runs without model calls."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "runs/moral_pilot_qwen_pair"
EXTENSION = ROOT / "runs/moral_extension_qwen_pair"
OUTPUT = ROOT / "runs/moral_full_qwen_pair"
EXPECTED = {"pilot": 10, "extension": 40}


def read(path: Path):
    return json.loads(path.read_text())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cells(config: dict) -> dict:
    return {cell["cell_id"]: cell for cell in config["cells"]}


def validate_source(split: str, directory: Path) -> tuple[dict, dict, dict]:
    config_path = directory / "config.json"
    config = read(config_path)
    assert config.get("ended_utc"), f"{split} is not completed"
    assert config["n_cells"] == 4 and config["count_per_cell"] == EXPECTED[split]
    assert config["planned_attempts"] == EXPECTED[split] * 4
    assert config["observed_summary"]["attempts_completed"] == EXPECTED[split] * 4
    config_cells = cells(config)
    assert len(config_cells) == 4
    payloads = {}
    hashes = {"config.json": digest(config_path)}
    for cell_id, spec in config_cells.items():
        path = directory / f"{cell_id}.json"
        assert path.is_file(), f"missing cell: {path}"
        payload = read(path)
        assert len(payload["rows"]) == EXPECTED[split], f"wrong count: {path}"
        assert {row["i"] for row in payload["rows"]} == set(range(EXPECTED[split])), f"duplicate/missing indices: {path}"
        assert payload["condition"] == spec["condition"]
        assert payload["model"] == spec["model"]
        assert payload["prompt"] == spec["prompt"]
        assert payload["threshold"] == spec["anchor"]
        payloads[cell_id] = payload
        hashes[str(path.relative_to(ROOT))] = digest(path)
    assert sum(len(payload["rows"]) for payload in payloads.values()) == EXPECTED[split] * 4
    return config, payloads, hashes


def comparable(payload: dict) -> dict:
    return {key: payload[key] for key in (
        "model", "backend", "provider", "condition", "threshold", "prompt",
        "max_tokens", "reasoning_effort", "request_settings",
    )}


def main() -> None:
    if OUTPUT.exists():
        raise SystemExit(f"refusing existing output directory: {OUTPUT}")
    sources = {
        "pilot": validate_source("pilot", PILOT),
        "extension": validate_source("extension", EXTENSION),
    }
    pilot_config, pilot_payloads, pilot_hashes = sources["pilot"]
    extension_config, extension_payloads, extension_hashes = sources["extension"]
    pilot_cells, extension_cells = cells(pilot_config), cells(extension_config)
    assert set(pilot_cells) == set(extension_cells)
    for cell_id in pilot_cells:
        assert pilot_cells[cell_id] == extension_cells[cell_id], f"config mismatch: {cell_id}"
        assert comparable(pilot_payloads[cell_id]) == comparable(extension_payloads[cell_id]), (
            f"cell mismatch: {cell_id}"
        )

    OUTPUT.mkdir()
    for cell_id, pilot_payload in pilot_payloads.items():
        combined = []
        for split, payload in (("pilot", pilot_payload), ("extension", extension_payloads[cell_id])):
            source_path = (PILOT if split == "pilot" else EXTENSION) / f"{cell_id}.json"
            for row in sorted(payload["rows"], key=lambda row: row["i"]):
                item = copy.deepcopy(row)
                item["source_i"] = item["i"]
                item["i"] = len(combined)
                item["source_file"] = str(source_path.relative_to(ROOT))
                item["source_split"] = split
                combined.append(item)
        output_payload = copy.deepcopy(pilot_payload)
        output_payload["rows"] = combined
        output_path = OUTPUT / f"{cell_id}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(output_payload, indent=2) + "\n")

    metadata = copy.deepcopy(pilot_config)
    metadata.pop("ended_utc", None)
    metadata.pop("observed_summary", None)
    for key in ("schedule", "schedule_seed", "started_utc"):
        metadata.pop(key, None)
    metadata["experiment"] = "moral_direction_combined_dataset"
    metadata["count_per_cell"] = EXPECTED["pilot"] + EXPECTED["extension"]
    metadata["planned_attempts"] = metadata["count_per_cell"] * 4
    metadata["total_responses"] = metadata["planned_attempts"]
    metadata["actual_count"] = metadata["count_per_cell"]
    metadata["new_model_calls"] = 0
    metadata["recorded_source_cost_usd"] = sum(source[0]["observed_summary"]["recorded_cost_usd"] for source in sources.values())
    metadata["analysis_note"] = "Primary follow-up uses the 160 extension responses; the inspected pilot remains labeled. Combined 200-response analysis is secondary."
    metadata["source_attempts"] = {split: count * 4 for split, count in EXPECTED.items()}
    metadata["source_configs"] = {"pilot": pilot_config, "extension": extension_config}
    metadata["source_config_sha256s"] = {"pilot": pilot_hashes["config.json"], "extension": extension_hashes["config.json"]}
    metadata["source_file_hashes"] = {"pilot": pilot_hashes, "extension": extension_hashes}
    metadata["splits"] = {
        split: {"actual_attempts": count * 4, "count_per_cell": count, "cells": 4}
        for split, count in EXPECTED.items()
    }
    metadata["derived_from"] = [str(PILOT.relative_to(ROOT)), str(EXTENSION.relative_to(ROOT))]
    (OUTPUT / "config.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
