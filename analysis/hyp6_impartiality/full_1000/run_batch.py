"""Frozen 1,000-trace OpenCode classifier. Offline preflight unless --run.

100 per model, 50 per incentive condition, excluding 30 calibration sources.
Resume skips every attempted trace, including failures: no automatic retries.
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import random
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
BASE = ROOT.parent / "opencode_pilot" / "run_pilot_curl.py"
SEED = 46062028
N_PER_CELL = 50
CONCURRENCY = 50


def source_key(item):
    return item["model_dir"], item["condition"], item["row_i"]


def initialize():
    spec = importlib.util.spec_from_file_location("curl_impl", BASE)
    impl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(impl)
    impl.ROOT = ROOT
    prompt = (ROOT.parent / "opencode_pilot_v4" / "system_prompt.txt").read_text().strip()
    calibration = json.loads((ROOT.parent / "opencode_pilot_v4_high" / "manifest.json").read_text())
    assert hashlib.sha256(prompt.encode()).hexdigest() == calibration["system_prompt_sha256"]
    impl.original.JUDGE_SYSTEM = prompt
    impl.original.JUDGE_SCHEMA = {"type": "json_object"}
    base_request = impl.make_request

    def make_request(item):
        request = base_request(item)
        request["reasoning_effort"] = "high"
        return request

    impl.make_request = make_request
    return impl


def select(impl):
    rng = random.Random(SEED)
    excluded = {source_key(item) for item in impl.original.build_selection()}
    selection, inventory = [], []
    directories = impl.original.find_model_dirs()
    assert len(directories) == 10
    for directory in directories:
        pool = impl.original.pooled_rows(directory)
        for condition in impl.original.INCENTIVIZED_CONDITIONS:
            candidates = [r for r in pool if r["condition"] == condition and source_key(r) not in excluded]
            assert len(candidates) >= N_PER_CELL
            inventory.append({"model_dir": directory.name, "condition": condition,
                              "available_after_calibration_exclusion": len(candidates), "selected": N_PER_CELL})
            selection.extend(rng.sample(candidates, N_PER_CELL))
    rng.shuffle(selection)
    for n, item in enumerate(selection, 1):
        item["trace_id"] = f"S{n:04d}"
    assert len(selection) == len({source_key(r) for r in selection}) == 1000
    assert not {source_key(r) for r in selection} & excluded
    assert set(Counter((r["model_dir"], r["condition"]) for r in selection).values()) == {50}
    return selection, inventory


async def run(impl, selection, key, done):
    semaphore = asyncio.Semaphore(CONCURRENCY)
    pending = [r for r in selection if r["trace_id"] not in done]
    tasks = [asyncio.create_task(impl.classify(r, key, semaphore)) for r in pending]
    started = time.perf_counter()
    n_done = len(done)
    print(f"Start: selected=1000; already_attempted={n_done}; pending={len(pending)}; concurrency=50; timeout=240s/4min; retries=0", flush=True)
    with (ROOT / "raw_judge_outputs.jsonl").open("a") as checkpoint:
        for task in asyncio.as_completed(tasks):
            record = await task
            checkpoint.write(json.dumps(record, ensure_ascii=False) + "\n")
            checkpoint.flush()
            os.fsync(checkpoint.fileno())
            n_done += 1
            print(f"{n_done}/1000 {record['trace_id']} HTTP={record['http_status']} finish={record['finish_reason']} elapsed={record['elapsed_seconds']}s", flush=True)
    print(f"Invocation elapsed: {time.perf_counter() - started:.1f}s", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    impl = initialize()
    selection, inventory = select(impl)
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "judge_model": "glm-5.3-flash", "endpoint": impl.ENDPOINT,
        "reasoning_effort": "high", "temperature": 0, "response_format": {"type": "json_object"},
        "max_tokens": None, "concurrency": CONCURRENCY, "timeout_seconds": 240, "retries": 0,
        "seed": SEED, "n_selected": 1000, "n_per_model": 100, "n_per_condition_per_model": 50,
        "sampling": "Random within model/condition from nonempty original reasoning; excludes all 30 calibration sources; randomized dispatch order.",
        "system_prompt_sha256": hashlib.sha256(impl.original.JUDGE_SYSTEM.encode()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "curl_implementation_sha256": hashlib.sha256(BASE.read_bytes()).hexdigest(),
        "inventory": inventory,
        "selection": [{k:v for k,v in r.items() if k != "reasoning"} | {
            "reasoning_characters": len(r["reasoning"]),
            "reasoning_sha256": hashlib.sha256(r["reasoning"].encode()).hexdigest()
        } for r in selection],
        "limitations": "Known long-trace false negatives and timeouts accepted by user as report limitations. Missing labels are not negatives. Judge labels are exploratory, not proof of unfaithfulness.",
    }
    manifest_path = ROOT / "manifest.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        for field in ("selection", "system_prompt_sha256", "reasoning_effort", "response_format", "timeout_seconds", "retries"):
            assert old[field] == manifest[field], f"Resume mismatch: {field}"
    else:
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        (ROOT / "system_prompt.txt").write_text(impl.original.JUDGE_SYSTEM + "\n")
    if not args.run:
        print("Offline preflight passed: 1000 unique traces; 100/model; 50/condition/model; no calibration overlap; frozen high-reasoning request. No API calls.")
        return
    load_dotenv(REPO / ".env")
    key = os.environ.get("OPENCODE_API_KEY")
    if not key:
        raise SystemExit("OPENCODE_API_KEY is not set")
    for name in ("requests", "responses"):
        (ROOT / name).mkdir(exist_ok=True)
    checkpoint = ROOT / "raw_judge_outputs.jsonl"
    records = [json.loads(line) for line in checkpoint.read_text().splitlines()] if checkpoint.exists() else []
    done = {r["trace_id"] for r in records}
    assert len(done) == len(records) and done <= {r["trace_id"] for r in selection}
    # A saved request without a checkpoint is an ambiguous prior attempt. Do not
    # silently resend it on resume and risk duplicate charges.
    ambiguous = {p.stem for p in (ROOT / "requests").glob("*.json")} - done
    if ambiguous:
        raise SystemExit(f"Uncheckpointed prior requests require reconciliation before resume: {sorted(ambiguous)}")
    asyncio.run(run(impl, selection, key, done))


if __name__ == "__main__":
    main()
