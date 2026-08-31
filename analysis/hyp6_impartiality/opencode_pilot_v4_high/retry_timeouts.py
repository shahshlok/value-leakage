"""One bounded operational retry of the four HTTP-000 timeouts; same requests."""

import asyncio
import hashlib
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "retry_1"
BASE = ROOT.parent / "opencode_pilot" / "run_pilot_curl.py"
RETRY_TIMEOUT_SECONDS = 240
RETRY_CONCURRENCY = 4


async def main():
    old = [json.loads(line) for line in (ROOT / "raw_judge_outputs.jsonl").read_text().splitlines()]
    failed = [r for r in old if r["http_status"] == "000" and r["curl_exit_code"] == 28]
    assert len(failed) == 4
    checkpoint_path = OUT / "raw_judge_outputs.jsonl"
    if checkpoint_path.exists():
        raise SystemExit("Retry checkpoint exists; refusing duplicate requests.")
    spec = importlib.util.spec_from_file_location("curl_pilot_impl", BASE)
    impl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(impl)
    impl.ROOT = OUT
    selection = {x["trace_id"]: x for x in impl.original.build_selection()}

    def make_request(item):
        request = json.loads((ROOT / "requests" / f"{item['trace_id']}.json").read_text())
        assert request["reasoning_effort"] == "high"
        assert request["messages"][1]["content"] == item["reasoning"]
        return request

    impl.make_request = make_request
    for name in ("requests", "responses"):
        (OUT / name).mkdir(exist_ok=True)
    load_dotenv(ROOT.parents[2] / ".env")
    key = os.environ["OPENCODE_API_KEY"]
    manifest = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "One retry of HTTP-000/curl-28 failures only. No label-based retries. Original requests unchanged.",
        "concurrency": RETRY_CONCURRENCY, "automatic_curl_retries": 0, "timeout_seconds": RETRY_TIMEOUT_SECONDS,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "trace_ids": [r["trace_id"] for r in failed],
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Startup: timeout={RETRY_TIMEOUT_SECONDS}s/4min; concurrency={RETRY_CONCURRENCY}; actual trace count={len(failed)}", flush=True)
    semaphore = asyncio.Semaphore(RETRY_CONCURRENCY)
    tasks = [asyncio.create_task(impl.classify(selection[r["trace_id"]], key, semaphore)) for r in failed]
    with checkpoint_path.open("x") as checkpoint:
        for n, task in enumerate(asyncio.as_completed(tasks), 1):
            record = await task
            record["attempt"] = 2
            checkpoint.write(json.dumps(record, ensure_ascii=False) + "\n")
            checkpoint.flush()
            os.fsync(checkpoint.fileno())
            print(f"{n}/4 {record['trace_id']} HTTP={record['http_status']} finish={record['finish_reason']} elapsed={record['elapsed_seconds']}s", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
