import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from value_leakage.anchoring import (
    CONDITIONS,
    _successful_rows,
    experiment_cells,
    merge_cell_results,
    pipeline,
)
from value_leakage.sample import build_prompt


class AnchoringExperimentTest(unittest.TestCase):
    def test_pilot_has_eight_cells(self):
        cells = experiment_cells(("qwen3.5-122b-a10b", "deepseek-flash"))
        self.assertEqual(len(cells), 8)
        self.assertEqual({cell["condition"] for cell in cells}, set(CONDITIONS))

    def test_expected_anchors(self):
        cells = experiment_cells(("qwen3.5-122b-a10b", "deepseek-flash"))
        anchors = {
            cell["model_name"]: {
                candidate["anchor"]
                for candidate in cells
                if candidate["model_name"] == cell["model_name"]
            }
            for cell in cells
        }
        self.assertEqual(anchors["qwen3.5-122b-a10b"], {41_000_000, 85_000_000})
        self.assertEqual(anchors["deepseek-flash"], {24_000_000, 50_000_000})

    def test_qwen_pins_the_historical_quantization(self):
        """Pinned to the endpoint the historical corpus was collected on.

        qwen3.5 is served fp4, fp8 and bf16 by different providers, so an
        unpinned run would mix quantizations and reintroduce the provider
        confound that picking this model was meant to avoid.
        """
        qwen = experiment_cells(("qwen3.5-122b-a10b",))[0]
        self.assertEqual(qwen["model"], "qwen/qwen3.5-122b-a10b")
        self.assertEqual(qwen["provider"], "deepinfra/fp4")

    def test_neutral_prompts_contain_no_moral_payoff(self):
        for condition in CONDITIONS:
            prompt = build_prompt(condition, 41_000_000)
            self.assertIn("41,000,000", prompt)
            self.assertNotIn("good cause", prompt.lower())
            self.assertNotIn("bad cause", prompt.lower())
            self.assertNotIn("donat", prompt.lower())

    def test_refill_planning_counts_only_successful_rows(self):
        cell = {
            "rows": [
                {"i": 0, "content": "ok"},
                {"i": 1, "error": "timeout"},
                {"i": 2, "error": "timeout"},
            ]
        }
        self.assertEqual(len(_successful_rows(cell["rows"])), 1)
        self.assertEqual(3 - len(_successful_rows(cell["rows"])), 2)
        self.assertEqual(1 - len(_successful_rows(cell["rows"])), 0)

    def test_merge_reindexes_successes_and_keeps_failures_and_metadata(self):
        existing = {
            "model": "old-model",
            "rows": [
                {"i": 7, "content": "old success"},
                {"i": 8, "error": "old failure"},
            ],
        }
        refill = {
            "model": "new-model",
            "provider": "provider-a",
            "rows": [
                {"i": 0, "content": "new success"},
                {"i": 1, "error": "new failure"},
            ],
        }

        merged = merge_cell_results(existing, refill)

        self.assertEqual(
            [row["i"] for row in merged["rows"] if "error" not in row],
            [0, 1],
        )
        self.assertEqual(
            [row["error"] for row in merged["rows"] if "error" in row],
            ["old failure", "new failure"],
        )
        self.assertEqual(merged["model"], "old-model")
        self.assertEqual(merged["refill_attempts"][0]["provider"], "provider-a")

    def test_complete_cells_are_skipped_without_sampling(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_path = Path(temp_dir)
            for cell in experiment_cells(("qwen3.5-122b-a10b",)):
                out_path = (
                    run_path
                    / cell["model_name"]
                    / (f"{cell['condition']}_{cell['anchor']}.json")
                )
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(
                    json.dumps(
                        {
                            "rows": [{"i": 0, "content": "complete"}],
                        }
                    )
                )

            with patch(
                "value_leakage.anchoring.sample",
                new_callable=AsyncMock,
            ) as sample_mock:
                asyncio.run(
                    pipeline(
                        run_path=run_path,
                        model_names=("qwen3.5-122b-a10b",),
                        count=1,
                        max_concurrent=1,
                        max_tokens=1,
                        reasoning_effort=None,
                    )
                )

            sample_mock.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
