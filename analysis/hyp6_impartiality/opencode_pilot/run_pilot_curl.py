"""Thirty-trace OpenCode pilot via curl. Defaults to an offline dry run.

Use --run to send the selected reasoning traces. Never scales beyond 30.
Results are checkpointed per request. Existing results prevent accidental reruns.
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
MODEL = "glm-5.3-flash"
ENDPOINT = "https://opencode.ai/zen/go/v1/chat/completions"
CONCURRENCY = 50
REQUEST_TIMEOUT_SECONDS = 240
OUTPUT_CAP = None

spec = importlib.util.spec_from_file_location("original_pilot", ROOT.parent / "pilot" / "run_pilot.py")
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)


def make_request(item):
    return {
        "model": MODEL, "temperature": 0, "reasoning_effort": "low",
        "response_format": original.JUDGE_SCHEMA,
        "messages": [
            {"role": "system", "content": original.JUDGE_SYSTEM},
            {"role": "user", "content": item["reasoning"]},
        ],
    }


async def classify(item, key, semaphore):
    async with semaphore:
        trace_id = item["trace_id"]
        request_path = ROOT / "requests" / f"{trace_id}.json"
        response_path = ROOT / "responses" / f"{trace_id}.json"
        request_path.write_text(json.dumps(make_request(item), ensure_ascii=False))
        started = time.perf_counter()
        process = await asyncio.create_subprocess_exec(
            "curl", "--silent", "--show-error", "--max-time", str(REQUEST_TIMEOUT_SECONDS),
            "--retry", "0", "--header", "@-",
            "--header", "Content-Type: application/json",
            "--data-binary", "@" + str(request_path),
            "--output", str(response_path), "--write-out", "%{http_code}",
            ENDPOINT, stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await process.communicate(("Authorization: Bearer " + key + "\n").encode())
        except asyncio.CancelledError:
            if process.returncode is None:
                process.terminate()
                await process.wait()
            raise
        record = {k:v for k,v in item.items() if k != "reasoning"}
        record.update(
            model=item["model_dir"], judge_model=MODEL,
            http_status=stdout.decode().strip(), curl_exit_code=process.returncode,
            elapsed_seconds=round(time.perf_counter() - started, 3),
            finished_at_utc=datetime.now(timezone.utc).isoformat(),
        )
        try:
            response = json.loads(response_path.read_text())
        except (OSError, json.JSONDecodeError):
            response = {}
        record["response"] = response
        record["usage"] = response.get("usage")
        choice = (response.get("choices") or [{}])[0]
        record["finish_reason"] = choice.get("finish_reason")
        record["raw_content"] = choice.get("message", {}).get("content") or ""
        try:
            record["parsed"] = json.loads(record["raw_content"])
        except json.JSONDecodeError:
            record["parsed"] = None
        record["reasoning_tokens"] = ((response.get("usage") or {}).get("completion_tokens_details") or {}).get("reasoning_tokens")
        record["error"] = None
        if process.returncode or record["http_status"] != "200":
            record["error"] = stderr.decode().strip() or str(response.get("error") or f"HTTP {record['http_status']}")
        return record


async def run(selection, key):
    semaphore = asyncio.Semaphore(CONCURRENCY)
    tasks = [asyncio.create_task(classify(item, key, semaphore)) for item in selection]
    start = time.perf_counter()
    with (ROOT / "raw_judge_outputs.jsonl").open("x") as checkpoint:
        for n, task in enumerate(asyncio.as_completed(tasks), 1):
            record = await task
            checkpoint.write(json.dumps(record, ensure_ascii=False) + "\n")
            checkpoint.flush()
            os.fsync(checkpoint.fileno())
            print(f"{n}/30 {record['trace_id']} HTTP={record['http_status']} finish={record['finish_reason']} elapsed={record['elapsed_seconds']}s reasoning_tokens={record['reasoning_tokens']}", flush=True)
    print(f"Batch elapsed: {time.perf_counter() - start:.1f}s", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    selection = original.build_selection()
    assert len(selection) == 30
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": MODEL, "endpoint": ENDPOINT, "reasoning_effort": "low",
        "temperature": 0, "concurrency": CONCURRENCY, "max_tokens": OUTPUT_CAP,
        "per_request_timeout_seconds": REQUEST_TIMEOUT_SECONDS, "automatic_retries": 0,
        "system_prompt_sha256": hashlib.sha256(original.JUDGE_SYSTEM.encode()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "response_format": original.JUDGE_SCHEMA,
        "selection": [{k:v for k,v in item.items() if k != "reasoning"} | {
            "reasoning_sha256": hashlib.sha256(item["reasoning"].encode()).hexdigest()
        } for item in selection],
        "caveat": "A successful request does not independently establish provider-enforced schema or reasoning controls. Validate every returned output. Truncations/errors are missing labels, not negatives.",
    }
    if (ROOT / "raw_judge_outputs.jsonl").exists():
        raise SystemExit("Existing checkpoint found; refusing to issue duplicate pilot requests.")
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if not args.run:
        print(f"Startup: timeout={REQUEST_TIMEOUT_SECONDS}s/4min; concurrency ceiling={CONCURRENCY}; actual trace count={len(selection)}", flush=True)
        print("Offline preflight: frozen prompt unchanged; low effort; no explicit output cap; no retries. No network calls made.")
        return
    load_dotenv(REPO / ".env")
    key = os.environ.get("OPENCODE_API_KEY")
    if not key:
        raise SystemExit("OPENCODE_API_KEY is not set")
    for name in ("requests", "responses"):
        (ROOT / name).mkdir(exist_ok=True)
    asyncio.run(run(selection, key))


if __name__ == "__main__":
    main()
