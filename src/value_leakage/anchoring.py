"""Run the threshold-anchoring follow-up experiment.

Pilot (40 generations total):

    uv run python -m value_leakage.anchoring --count 5

Main experiment (400 generations total):

    uv run python -m value_leakage.anchoring --count 50

``count`` is per model x framing x anchor cell. Existing cell files are
skipped; incomplete cells are refilled once per invocation.
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
    "inkling": {
        "model": "thinkingmachines/inkling",
        "provider": None,
        "anchors": (40_000_000, 100_000_000),
        "historical_model": "accounts/fireworks/models/inkling",
    },
    "deepseek-flash": {
        "model": "deepseek/deepseek-v4-flash-0731",
        "provider": None,
        "anchors": (24_000_000, 50_000_000),
        "historical_model": ("accounts/fireworks/models/deepseek-v4-flash-0731"),
    },
}


def _successful_rows(rows: list[dict]) -> list[dict]:
    """Return response rows that contain a successful sample result."""
    return [row for row in rows if "error" not in row]


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
    failures = [row for row in existing_rows + refill_rows if "error" in row]

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
                        "prompt": build_prompt(condition, anchor),
                    }
                )
    return cells


async def pipeline(
    run_path: Path,
    model_names: tuple[str, ...],
    count: int,
    max_concurrent: int,
    max_tokens: int,
    reasoning_effort: str | None,
) -> None:
    for cell in experiment_cells(model_names):
        model_path = run_path / cell["model_name"]
        out_path = model_path / (f"{cell['condition']}_{cell['anchor']}.json")
        model_path.mkdir(parents=True, exist_ok=True)
        if out_path.exists():
            existing = json.loads(out_path.read_text())
            missing = count - len(_successful_rows(existing.get("rows", [])))
            if missing <= 0:
                print(f"Skipping complete cell: {out_path}")
                continue
            print(
                f"Refilling {out_path}: requesting {missing} missing successful row(s)"
            )
            refill_path = out_path.with_suffix(".refill.json")
            try:
                await sample(
                    condition=cell["condition"],
                    threshold=cell["anchor"],
                    count=missing,
                    max_concurrent=max_concurrent,
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
            continue
        await sample(
            condition=cell["condition"],
            threshold=cell["anchor"],
            count=count,
            max_concurrent=max_concurrent,
            model=cell["model"],
            max_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
            out=str(out_path),
            backend="openrouter",
            provider=cell["provider"],
        )


def main(
    models: str = "inkling,deepseek-flash",
    count: int = 5,
    max_concurrent: int = 5,
    max_tokens: int = 64000,
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
    cells = experiment_cells(model_names)
    config = {
        "experiment": "threshold_anchoring",
        "models": {name: MODEL_SPECS[name] for name in model_names},
        "conditions": list(CONDITIONS),
        "count_per_cell": count,
        "n_cells": len(cells),
        "planned_generations": count * len(cells),
        "backend": "openrouter",
        "max_concurrent": max_concurrent,
        "max_tokens": max_tokens,
        "reasoning_effort": reasoning_effort,
        "cells": cells,
        "historical_comparison_caveat": (
            "Original Inkling and DeepSeek Flash data used direct Fireworks "
            "endpoints. Default OpenRouter provider routing may vary in "
            "provider, weights, quantization, serving code, or reasoning "
            "wrapper. Within-run "
            "randomized anchor contrasts remain interpretable."
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
