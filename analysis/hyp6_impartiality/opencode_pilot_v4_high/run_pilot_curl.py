"""Same v4 pilot, changing only requested reasoning effort from low to high."""

import contextlib
import hashlib
import importlib.util
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "opencode_pilot" / "run_pilot_curl.py"
LOW = ROOT.parent / "opencode_pilot_v4"


def record_configuration():
    path = ROOT / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest.update(
        version="v4_high_reasoning_comparison",
        reasoning_effort="high",
        wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        comparison="Same 30 sources, v4 system prompt, temperature, JSON-object mode, concurrency ceiling, and no explicit output cap; only requested reasoning effort changes.",
        calibration_status="Previously inspected development traces; not fresh validation.",
    )
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def main():
    spec = importlib.util.spec_from_file_location("curl_pilot_impl", BASE)
    impl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(impl)
    impl.ROOT = ROOT
    prompt = (LOW / "system_prompt.txt").read_text().strip()
    low_manifest = json.loads((LOW / "manifest.json").read_text())
    assert hashlib.sha256(prompt.encode()).hexdigest() == low_manifest["system_prompt_sha256"]
    impl.original.JUDGE_SYSTEM = prompt
    impl.original.JUDGE_SCHEMA = {"type": "json_object"}
    base_make_request = impl.make_request

    def make_request(item):
        request = base_make_request(item)
        request["reasoning_effort"] = "high"
        return request

    impl.make_request = make_request
    base_run = impl.run

    async def run(selection, key):
        record_configuration()
        await base_run(selection, key)

    impl.run = run
    if "--run" in sys.argv:
        impl.main()
    else:
        with contextlib.redirect_stdout(io.StringIO()):
            impl.main()
        record_configuration()
        print("Offline preflight: same v4 prompt and 30 traces; high effort; JSON-object mode; concurrency ceiling 50; no explicit output cap. No network calls made.")


if __name__ == "__main__":
    main()
