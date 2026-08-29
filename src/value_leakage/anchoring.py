"""Run the threshold-anchoring follow-up experiment.

Pilot (40 generations total):

    uv run python -m value_leakage.anchoring --count 5

Main experiment (400 generations total):

    uv run python -m value_leakage.anchoring --count 50

``count`` is per model x framing x anchor cell. Existing cell files are
skipped; incomplete cells are refilled once per invocation. Requests are run
sequentially, four cells per model.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import fire

from value_leakage.sample import build_prompt, sample

RUNS_ROOT = Path("runs")
CONDITIONS = ("irrelevant_number", "neutral_boundary")
MODEL_SPECS = {
    # Stands in for Inkling, which has the strongest historical signal
    # (MRF 0.063) but is unusable: every OpenRouter endpoint shares an upstream
    # pool that 429s, and the generations that survive run at 4-5 tok/s, ~27
    # minutes each. qwen3.5 is the strongest reachable signal (MRF 0.027, rank 3
    # overall). Its historical provider is retained as comparison metadata;
    # current runs leave provider selection to OpenRouter.
    # inkling-small is NOT a substitute despite the shared family: its baseline
    # drift is -1.17, ~25x every other model, so it is unstable rather than
    # biased and no anchoring shift is measurable inside that.
    "qwen3.5-122b-a10b": {
        "model": "qwen/qwen3.5-122b-a10b",
        "provider": None,
        # 41M sits at the model's own baseline median (~40M); 85M is ~2x it.
        "anchors": (41_000_000, 85_000_000),
        "historical_model": "qwen/qwen3.5-122b-a10b",
        "historical_provider": "deepinfra/fp4",
    },
    "qwen3p8-2p4t-a95b": {
        "model": "qwen/qwen3.8-2.4t-a95b",
        "provider": None,
        # Historical baseline median is 39.5M (88 valid estimates; middle
        # values 39M and 40M), and threshold.json records the same threshold.
        # 40M is the rounded-near anchor; 80M is clearly higher while still
        # within the historical baseline's plausible estimate range.
        "anchors": (40_000_000, 80_000_000),
        "historical_run": "runs/qwen3p8-2p4t-a95b_20260815_030703",
        "historical_model": "accounts/fireworks/models/qwen3p8-2p4t-a95b",
        "historical_baseline_median": 39_500_000,
        "historical_threshold": 39_500_000,
        "anchor_rationale": (
            "40M is rounded close to the historical 39.5M median/threshold; "
            "80M is a clearly higher but historically plausible anchor."
        ),
    },
}


def _has_visible_content(row: dict) -> bool:
    content = row.get("content")
    return isinstance(content, str) and bool(content.strip())


def _successful_rows(rows: list[dict]) -> list[dict]:
    """Return response rows that contain a successful sample result."""
    return [row for row in rows if "error" not in row and _has_visible_content(row)]


def merge_cell_results(
    existing: dict,
    refill: dict,
) -> dict:
    """Merge one refill attempt into a cell while preserving its audit trail.

    Successful rows from the original and refill files are combined and
    reindexed. Failed rows are retained verbatim after them. Refill metadata
    is kept separately so the original cell metadata is not overwritten.
    """
    existing_rows = existing.get("rows", [])
    refill_rows = refill.get("rows", [])
    successes = _successful_rows(existing_rows) + _successful_rows(refill_rows)

    reindexed_successes = [{**row, "i": index} for index, row in enumerate(successes)]
    failures = [
        row
        for row in existing_rows + refill_rows
        if "error" in row or not _has_visible_content(row)
    ]

    merged = dict(existing)
    merged["rows"] = reindexed_successes + failures
    merged["refill_attempts"] = [
        *existing.get("refill_attempts", []),
        {key: value for key, value in refill.items() if key != "rows"},
    ]
    return merged


def experiment_cells(model_names: tuple[str, ...]) -> list[dict]:
    cells = []
    for model_name in model_names:
        spec = MODEL_SPECS[model_name]
        for condition in CONDITIONS:
            for anchor in spec["anchors"]:
                cells.append(
                    {
                        "model_name": model_name,
                        "model": spec["model"],
                        "provider": spec["provider"],
                        "condition": condition,
                        "anchor": anchor,
                        "cell_id": f"{model_name}/{condition}_{anchor}",
                        "prompt": build_prompt(condition, anchor),
                    }
                )
    return cells


async def _run_cell_request(
    run_path: Path,
    cell: dict,
    count: int,
    max_concurrent: int,
    max_tokens: int | None,
    reasoning_effort: str | None,
) -> None:
    """Run one request for a cell and preserve its resumable output file."""
    model_path = run_path / cell["model_name"]
    out_path = model_path / (f"{cell['condition']}_{cell['anchor']}.json")
    model_path.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        existing = json.loads(out_path.read_text())
        missing = count - len(_successful_rows(existing.get("rows", [])))
        if missing <= 0:
            print(f"Skipping complete cell: {out_path}")
            return
        print(f"Refilling {out_path}: requesting {missing} missing successful rows")
        refill_path = out_path.with_suffix(".refill.json")
        try:
            await sample(
                condition=cell["condition"],
                threshold=cell["anchor"],
                count=missing,
                max_concurrent=min(max_concurrent, missing),
                model=cell["model"],
                max_tokens=max_tokens,
                reasoning_effort=reasoning_effort,
                out=str(refill_path),
                backend="openrouter",
                provider=cell["provider"],
            )
            refill = json.loads(refill_path.read_text())
            out_path.write_text(
                json.dumps(
                    merge_cell_results(existing, refill),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        finally:
            refill_path.unlink(missing_ok=True)
        return

    await sample(
        condition=cell["condition"],
        threshold=cell["anchor"],
        count=count,
        max_concurrent=min(max_concurrent, count),
        model=cell["model"],
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        out=str(out_path),
        backend="openrouter",
        provider=cell["provider"],
    )


async def pipeline(
    run_path: Path,
    model_names: tuple[str, ...],
    count: int,
    max_concurrent: int,
    max_tokens: int | None,
    reasoning_effort: str | None,
) -> None:
    if max_concurrent < 1:
        raise ValueError("max_concurrent must be positive")
    for cell in experiment_cells(model_names):
        await _run_cell_request(
            run_path, cell, count, max_concurrent, max_tokens, reasoning_effort
        )


def main(
    models: str = "qwen3.5-122b-a10b,qwen3p8-2p4t-a95b",
    count: int = 5,
    max_concurrent: int = 10,
    max_tokens: int | None = 64000,
    reasoning_effort: str | None = "high",
    run_dir: str | None = None,
    dry_run: bool = False,
):
    """Run all anchoring cells. ``count`` is the number per cell."""
    model_names = tuple(name.strip() for name in models.split(",") if name.strip())
    unknown = sorted(set(model_names) - set(MODEL_SPECS))
    if unknown:
        raise ValueError(f"unknown models {unknown}; choose from {sorted(MODEL_SPECS)}")
    if count < 1:
        raise ValueError("count must be positive")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_path = Path(run_dir) if run_dir else RUNS_ROOT / f"anchoring_{stamp}"
    run_path.mkdir(parents=True, exist_ok=True)
    config_path = run_path / "config.json"
    n_cells = len(experiment_cells(model_names))
    cells = experiment_cells(model_names)
    config = {
        "experiment": "threshold_anchoring",
        "models": {name: MODEL_SPECS[name] for name in model_names},
        "conditions": list(CONDITIONS),
        "count_per_cell": count,
        "n_cells": n_cells,
        "planned_generations": count * n_cells,
        "backend": "openrouter",
        "max_concurrent": max_concurrent,
        "max_tokens": max_tokens,
        "reasoning_effort": reasoning_effort,
        "cells": cells,
        "historical_comparison_caveat": (
            "Historical runs used direct or provider-specific endpoints. "
            "Current OpenRouter runs intentionally leave provider selection "
            "unset, so provider, weights, quantization, serving code, or "
            "reasoning wrapper may vary; historical provider fields are "
            "recorded only as metadata. Within-run anchor contrasts remain "
            "interpretable."
        ),
    }
    (run_path / "config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False)
    )
    print(
        f"Planned {config['planned_generations']} generations across "
        f"{config['n_cells']} cells; config saved to {run_path / 'config.json'}"
    )
    if dry_run:
        return
    asyncio.run(
        pipeline(
            run_path=run_path,
            model_names=model_names,
            count=count,
            max_concurrent=max_concurrent,
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
        )
    )


if __name__ == "__main__":
    fire.Fire(main)
