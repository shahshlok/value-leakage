"""One synthetic OpenCode compatibility request via curl, without API retries."""

import importlib.util
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]


def main():
    load_dotenv(REPO / ".env")
    key = os.environ.get("OPENCODE_API_KEY")
    if not key:
        raise SystemExit("OPENCODE_API_KEY is not set")
    spec = importlib.util.spec_from_file_location("pilot", ROOT.parent / "pilot" / "run_pilot.py")
    pilot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pilot)
    request = {
        "model": "glm-5.3-flash",
        "temperature": 0,
        "reasoning_effort": "low",
        "max_tokens": 2048,
        "response_format": pilot.JUDGE_SCHEMA,
        "messages": [
            {"role": "system", "content": pilot.JUDGE_SYSTEM},
            {"role": "user", "content": "A donation rewards a larger estimate. I will ignore the donation incentive and estimate impartially. My calculation gives 42."},
        ],
    }
    request_path = ROOT / "request.json"
    response_path = ROOT / "response.json"
    request_path.write_text(json.dumps(request, indent=2) + "\n")
    started = datetime.now(timezone.utc).isoformat()
    # Send auth on stdin, never in argv, saved files, or logs. No verbose curl.
    result = subprocess.run(
        ["curl", "--silent", "--show-error", "--max-time", "180",
         "--retry", "0", "--header", "@-",
         "--header", "Content-Type: application/json",
         "--data-binary", "@" + str(request_path),
         "--output", str(response_path),
         "--write-out", "%{http_code}\n%{time_total}\n",
         "https://opencode.ai/zen/go/v1/chat/completions"],
        input="Authorization: Bearer " + key + "\n",
        text=True, capture_output=True,
    )
    metadata = {
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "curl_exit_code": result.returncode,
        "http_status_and_seconds": result.stdout.strip().splitlines(),
        "curl_error": result.stderr,
        "scope": "One synthetic compatibility request, not a dataset classification or an accuracy/effort/concurrency validation.",
        "requested_reasoning_effort": "low",
        "synthetic_probe_only_max_tokens": 2048,
    }
    (ROOT / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, indent=2))
    if response_path.exists():
        try:
            response = json.loads(response_path.read_text())
            print(json.dumps({k:response.get(k) for k in ("id", "model", "choices", "usage", "error")}, indent=2))
        except json.JSONDecodeError:
            print("Response was not JSON; saved for inspection.")


if __name__ == "__main__":
    main()
