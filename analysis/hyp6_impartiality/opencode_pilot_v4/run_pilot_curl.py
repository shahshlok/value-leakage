"""Prepared v4 pilot. Defaults to offline preflight; --run spends API usage."""

import hashlib
import importlib.util
import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "opencode_pilot" / "run_pilot_curl.py"


def main():
    spec = importlib.util.spec_from_file_location("curl_pilot_impl", BASE)
    impl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(impl)
    impl.ROOT = ROOT
    impl.original.JUDGE_SYSTEM = (ROOT / "system_prompt.txt").read_text().strip()
    impl.original.JUDGE_SCHEMA = {"type": "json_object"}
    if "--run" in sys.argv:
        impl.main()
    else:
        with contextlib.redirect_stdout(io.StringIO()):
            impl.main()
        print("V4 offline preflight: revised prompt; JSON-object mode; low effort; 30 development traces; concurrency ceiling 50; no explicit output cap. No network calls made.")
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest.update(
        version="v4_prepared_revision",
        wrapper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        prompt_file_sha256=hashlib.sha256((ROOT / "system_prompt.txt").read_bytes()).hexdigest(),
        calibration_status="Reuses already inspected development traces; not an independent validation.",
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
