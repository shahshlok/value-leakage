"""Standalone, non-resumable moral-direction follow-up runner.

This module intentionally does not use the anchoring runner's refill path or
the shared OpenRouter retry helper.  It is a fresh four-cell run:
10 responses per moral direction at the verified low anchor for each Qwen
model.
"""

import asyncio
import json
import os
import random
import re
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from value_leakage.anchoring import MODEL_SPECS
from value_leakage.api.openrouter.chat_completions import get_openrouter_client
from value_leakage.sample import _flatten_response, build_prompt


RUN_DIR = Path("runs/moral_pilot_qwen_pair")
MODEL_NAMES = ("qwen3.5-122b-a10b", "qwen3p8-2p4t-a95b")
CONDITIONS = ("above_good", "below_good")
LOW_ANCHORS = {
    "qwen3.5-122b-a10b": 41_000_000,
    "qwen3p8-2p4t-a95b": 40_000_000,
}
DEFAULT_COUNT = 10
DEFAULT_CONCURRENCY = 10
DEFAULT_MAX_TOKENS = 64_000
DEFAULT_REASONING_EFFORT = "high"
DEFAULT_SCHEDULE_SEED = 20260829

HISTORICAL_PROMPT_CHECKS = (
    {
        "model_name": "qwen3.5-122b-a10b",
        "condition": "above_good",
        "path": Path("runs/qwen3.5-122b-a10b_20260815_030702/above_good.json"),
        "historical_threshold": 41_000_000,
    },
    {
        "model_name": "qwen3.5-122b-a10b",
        "condition": "below_good",
        "path": Path("runs/qwen3.5-122b-a10b_20260815_030702/below_good.json"),
        "historical_threshold": 41_000_000,
    },
    {
        "model_name": "qwen3p8-2p4t-a95b",
        "condition": "above_good",
        "path": Path("runs/qwen3p8-2p4t-a95b_20260815_030703/above_good.json"),
        "historical_threshold": 39_500_000,
    },
    {
        "model_name": "qwen3p8-2p4t-a95b",
        "condition": "below_good",
        "path": Path("runs/qwen3p8-2p4t-a95b_20260815_030703/below_good.json"),
        "historical_threshold": 39_500_000,
    },
)

REQUEST_SETTINGS = {
    "temperature": 1.0,
    "top_p": 1.0,
    "logprobs": False,
    "max_tokens": DEFAULT_MAX_TOKENS,
    "extra_body": {"reasoning": {"effort": DEFAULT_REASONING_EFFORT}},
    "provider_field": "omitted; OpenRouter provider routing is unpinned",
    "seed": "omitted; schedule seed only controls local job order",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalise_threshold(prompt: str) -> str:
    return re.sub(r"(The threshold is )([0-9,]+)(\.)", r"\1{threshold}\3", prompt)


def verify_saved_original_prompts() -> list[dict]:
    """Verify saved Aditya prompts against the imported original builder."""
    checks = []
    for check in HISTORICAL_PROMPT_CHECKS:
        saved = json.loads(check["path"].read_text(encoding="utf-8"))
        historical_prompt = build_prompt(
            check["condition"], check["historical_threshold"]
        )
        fresh_prompt = build_prompt(
            check["condition"], LOW_ANCHORS[check["model_name"]]
        )
        exact_at_saved_threshold = saved["prompt"] == historical_prompt
        equal_except_threshold = _normalise_threshold(saved["prompt"]) == _normalise_threshold(
            fresh_prompt
        )
        if not exact_at_saved_threshold or not equal_except_threshold:
            raise ValueError(
                f"saved original prompt mismatch: {check['path']} "
                f"({check['condition']})"
            )
        checks.append(
            {
                "path": str(check["path"]),
                "condition": check["condition"],
                "historical_threshold": check["historical_threshold"],
                "fresh_threshold": LOW_ANCHORS[check["model_name"]],
                "exact_at_saved_threshold": True,
                "equal_except_threshold": True,
            }
        )
    return checks


def _job_schedule(count: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    schedule = []
    for model_name in MODEL_NAMES:
        jobs = [
            {
                "model_name": model_name,
                "model": MODEL_SPECS[model_name]["model"],
                "condition": condition,
                "threshold": LOW_ANCHORS[model_name],
                "i": i,
            }
            for condition in CONDITIONS
            for i in range(count)
        ]
        rng.shuffle(jobs)
        schedule.extend(jobs)
    for attempt, job in enumerate(schedule):
        job["attempt"] = attempt
        job["prompt"] = build_prompt(job["condition"], job["threshold"])
    return schedule


def _cell_metadata(job: dict, max_tokens: int, reasoning_effort: str) -> dict:
    return {
        "model": job["model"],
        "backend": "openrouter",
        "provider": None,
        "condition": job["condition"],
        "threshold": job["threshold"],
        "prompt": job["prompt"],
        "max_tokens": max_tokens,
        "reasoning_effort": reasoning_effort,
        "request_settings": {
            **REQUEST_SETTINGS,
            "max_tokens": max_tokens,
            "extra_body": {"reasoning": {"effort": reasoning_effort}},
        },
        "rows": [],
    }


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _cost(row: dict) -> float | None:
    value = (row.get("usage") or {}).get("cost")
    return float(value) if isinstance(value, (int, float)) else None


def _annotate_response(i: int, response, started: str, ended: str) -> dict:
    row = _flatten_response(i, response)
    row["request_id"] = getattr(response, "id", None)
    row["request_started_utc"] = started
    row["request_ended_utc"] = ended
    row["duration_seconds"] = (
        datetime.fromisoformat(ended.replace("Z", "+00:00"))
        - datetime.fromisoformat(started.replace("Z", "+00:00"))
    ).total_seconds()

    if "error" in row:
        row["outcome"] = "error"
        return row
    finish_reason = row.get("finish_reason")
    truncated = finish_reason in {"length", "max_tokens", "token_limit"}
    row["truncated"] = truncated
    if truncated:
        row["outcome"] = "truncated"
    elif not isinstance(row.get("content"), str) or not row["content"].strip():
        row["outcome"] = "empty_content"
        row["error"] = "response had empty visible content"
    else:
        row["outcome"] = "success"
    return row


async def _run_model(
    model_name: str,
    jobs: list[dict],
    client,
    states: dict[tuple[str, str], dict],
    max_tokens: int,
    reasoning_effort: str,
    concurrency: int,
    progress: dict,
    progress_lock: asyncio.Lock,
) -> None:
    semaphore = asyncio.Semaphore(concurrency)

    async def one(job: dict) -> None:
        state = states[(job["model_name"], job["condition"])]
        started = _utc_now()
        try:
            async with semaphore:
                started = _utc_now()
                response = await client.chat.completions.create(
                    model=job["model"],
                    messages=[{"role": "user", "content": job["prompt"]}],
                    temperature=1.0,
                    top_p=1.0,
                    logprobs=False,
                    max_tokens=max_tokens,
                    extra_body={"reasoning": {"effort": reasoning_effort}},
                )
            row = _annotate_response(job["i"], response, started, _utc_now())
        except Exception as exc:
            ended = _utc_now()
            row = {
                "i": job["i"],
                "error": f"{type(exc).__name__}: {exc}",
                "outcome": "error",
                "request_id": None,
                "request_started_utc": started,
                "request_ended_utc": ended,
            }

        async with state["lock"]:
            state["payload"]["rows"].append(row)
            state["payload"]["rows"].sort(key=lambda item: item["i"])
            _atomic_write_json(state["path"], state["payload"])

        async with progress_lock:
            progress["completed"] += 1
            outcome = row.get("outcome", "error")
            progress["outcomes"][outcome] += 1
            cost = _cost(row)
            if cost is not None:
                progress["cost"] += cost
            provider = row.get("response_provider") or "n/a"
            cost_text = f"${cost:.6f}" if cost is not None else "n/a"
            print(
                f"[{progress['completed']}/{progress['total']}] {model_name} "
                f"{job['condition']} i={job['i']} outcome={outcome} "
                f"provider={provider} cost={cost_text}"
            )

    await asyncio.gather(*(one(job) for job in jobs))


def _build_config(
    count: int,
    concurrency: int,
    max_tokens: int,
    reasoning_effort: str,
    schedule_seed: int,
    schedule: list[dict],
    prompt_checks: list[dict],
) -> dict:
    cells = []
    for model_name in MODEL_NAMES:
        for condition in CONDITIONS:
            job = next(
                item
                for item in schedule
                if item["model_name"] == model_name
                and item["condition"] == condition
            )
            cells.append(
                {
                    "model_name": model_name,
                    "model": job["model"],
                    "provider": None,
                    "condition": condition,
                    "anchor": LOW_ANCHORS[model_name],
                    "cell_id": f"{model_name}/{condition}_{LOW_ANCHORS[model_name]}",
                    "prompt": job["prompt"],
                }
            )
    return {
        "experiment": "moral_direction_followup_replication",
        "models": {
            name: {
                **MODEL_SPECS[name],
                "fresh_low_anchor": LOW_ANCHORS[name],
                "historical_moral_threshold": (
                    39_500_000 if name == "qwen3p8-2p4t-a95b" else 41_000_000
                ),
            }
            for name in MODEL_NAMES
        },
        "conditions": list(CONDITIONS),
        "count_per_cell": count,
        "n_cells": len(cells),
        "planned_attempts": len(schedule),
        "backend": "openrouter",
        "provider": None,
        "max_concurrent_per_model": concurrency,
        "max_tokens": max_tokens,
        "reasoning_effort": reasoning_effort,
        "schedule_seed": schedule_seed,
        "request_settings": {
            **REQUEST_SETTINGS,
            "max_tokens": max_tokens,
            "extra_body": {"reasoning": {"effort": reasoning_effort}},
        },
        "prompt_checks": prompt_checks,
        "qwen38_threshold_note": (
            "Historical Qwen 3.8 moral prompts used 39,500,000; this fresh "
            "replication uses 40,000,000, a 500,000 increase."
        ),
        "neutral_comparison_caveat": (
            "Existing neutral low-anchor data are an old/cross-run descriptive "
            "comparison; no fresh neutral cells are generated."
        ),
        "cells": cells,
        "schedule": schedule,
    }


async def run(
    run_dir: Path,
    config: dict,
    count: int,
    concurrency: int,
    max_tokens: int,
    reasoning_effort: str,
) -> None:
    if run_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing run directory: {run_dir}")
    run_dir.mkdir(parents=True)
    config["started_utc"] = _utc_now()
    config_path = run_dir / "config.json"
    _atomic_write_json(config_path, config)

    states = {}
    for model_name in MODEL_NAMES:
        model_dir = run_dir / model_name
        for condition in CONDITIONS:
            job = next(
                item
                for item in config["schedule"]
                if item["model_name"] == model_name
                and item["condition"] == condition
            )
            path = model_dir / f"{condition}_{LOW_ANCHORS[model_name]}.json"
            payload = _cell_metadata(job, max_tokens, reasoning_effort)
            states[(model_name, condition)] = {
                "path": path,
                "payload": payload,
                "lock": asyncio.Lock(),
            }
            _atomic_write_json(path, payload)

    client = get_openrouter_client().with_options(max_retries=0)
    progress = {"completed": 0, "total": len(config["schedule"]), "cost": 0.0, "outcomes": Counter()}
    progress_lock = asyncio.Lock()
    try:
        await asyncio.gather(
            *(
                _run_model(
                    model_name,
                    [job for job in config["schedule"] if job["model_name"] == model_name],
                    client,
                    states,
                    max_tokens,
                    reasoning_effort,
                    concurrency,
                    progress,
                    progress_lock,
                )
                for model_name in MODEL_NAMES
            )
        )
    finally:
        await client.close()
        config["ended_utc"] = _utc_now()
        config["observed_summary"] = {
            "attempts_completed": progress["completed"],
            "outcomes": dict(progress["outcomes"]),
            "recorded_cost_usd": progress["cost"],
        }
        _atomic_write_json(config_path, config)
    print(
        f"Completed {progress['completed']}/{progress['total']} attempts; "
        f"outcomes={dict(progress['outcomes'])}; "
        f"recorded_cost=${progress['cost']:.6f}"
    )


def main(
    count: int = DEFAULT_COUNT,
    concurrency: int = DEFAULT_CONCURRENCY,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    schedule_seed: int = DEFAULT_SCHEDULE_SEED,
    run_dir: str = str(RUN_DIR),
    dry_run: bool = False,
) -> None:
    if count < 1 or concurrency < 1 or max_tokens < 1:
        raise ValueError("count, concurrency, and max_tokens must be positive")
    if set(MODEL_NAMES) - set(MODEL_SPECS):
        raise ValueError("configured Qwen model alias is missing from MODEL_SPECS")
    for model_name, anchor in LOW_ANCHORS.items():
        if anchor not in MODEL_SPECS[model_name]["anchors"]:
            raise ValueError(f"low anchor not present in MODEL_SPECS: {model_name} {anchor}")

    prompt_checks = verify_saved_original_prompts()
    schedule = _job_schedule(count, schedule_seed)
    config = _build_config(
        count,
        concurrency,
        max_tokens,
        reasoning_effort,
        schedule_seed,
        schedule,
        prompt_checks,
    )
    if dry_run:
        print(json.dumps(config, indent=2, ensure_ascii=False))
        return
    asyncio.run(
        run(
            Path(run_dir),
            config,
            count,
            concurrency,
            max_tokens,
            reasoning_effort,
        )
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--reasoning-effort", default=DEFAULT_REASONING_EFFORT)
    parser.add_argument("--schedule-seed", type=int, default=DEFAULT_SCHEDULE_SEED)
    parser.add_argument("--run-dir", default=str(RUN_DIR))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(**vars(args))
