# Historical Qwen moral-direction check

Exploratory descriptive check only; no significance testing. Historical moral medians use the existing `anchoring_extract.v3` helper on the stored visible `rows[*].content` field. Reasoning and trajectories are not used.

## Signal

| Model ID | Historical threshold | above_good (clear/n) | below_good (clear/n) | above − below |
|---|---:|---:|---:|---:|
| `qwen/qwen3.5-122b-a10b` | 41,000,000 | 44,000,000 (95/100) | 38,000,000 (88/100) | 6,000,000 |
| `accounts/fireworks/models/qwen3p8-2p4t-a95b` | 39,500,000 | 40,800,000 (93/100) | 39,150,000 (80/100) | 1,650,000 |

Counts below are explicit parser outcomes; ambiguous and missing rows were not imputed.

| Model | Condition | Clear | Ambiguous | Missing | Raw errors | Parser rules |
|---|---|---:|---:|---:|---:|---|
| `qwen3.5-122b-a10b` | `above_good` | 95 | 4 | 1 | 1 | `{'conflicting_final_candidates': 1, 'missing_content': 1, 'no_single_final': 2, 'opening_answer_number': 93, 'terminal_result_number': 2, 'unresolved_range': 1}` |
| `qwen3.5-122b-a10b` | `below_good` | 88 | 7 | 5 | 5 | `{'conflicting_final_candidates': 1, 'final_label_next_line_number': 1, 'missing_content': 5, 'no_single_final': 2, 'opening_answer_number': 85, 'terminal_result_number': 2, 'unresolved_range': 4}` |
| `qwen3.8-2.4t-a95b` | `above_good` | 93 | 7 | 0 | 0 | `{'conflicting_final_candidates': 7, 'final_label_next_line_number': 2, 'opening_answer_number': 91}` |
| `qwen3.8-2.4t-a95b` | `below_good` | 80 | 4 | 16 | 16 | `{'conflicting_final_candidates': 3, 'final_label_next_line_number': 2, 'final_label_same_line_number': 2, 'missing_content': 16, 'opening_answer_number': 76, 'unresolved_range': 1}` |

## Threshold and prompt checks

- `qwen/qwen3.5-122b-a10b`: historical moral threshold is **41,000,000** in both conditions; `moral_threshold_equal=True` and saved prompts match `build_prompt` for both conditions (`{'below_good': True, 'above_good': True}`); shared prompt base/suffix equality is `True`.
- Fresh moral threshold is **41,000,000**; numeric difference from historical is **+0**; numeric-only prompt matches are `{'below_good': True, 'above_good': True}`. Fresh wording is the original builder output; this historical check does not use fresh moral responses.
- `accounts/fireworks/models/qwen3p8-2p4t-a95b`: historical moral threshold is **39,500,000** in both conditions; `moral_threshold_equal=True` and saved prompts match `build_prompt` for both conditions (`{'below_good': True, 'above_good': True}`); shared prompt base/suffix equality is `True`.
- Fresh moral threshold is **40,000,000**; numeric difference from historical is **+500,000**; numeric-only prompt matches are `{'below_good': True, 'above_good': True}`. Fresh wording is the original builder output; this historical check does not use fresh moral responses.

The original saved moral wording is defined by [`sample.py`](</Users/shlok/value-leakage/src/value_leakage/sample.py:29>) and the exact saved prompt strings are retained in `historical_check.json`. The only historical-to-fresh wording change is the inserted threshold number.

## Neutral low-anchor context

These are existing audited neutral holdout medians, shown descriptively only and not used in the historical moral comparison:

| Model | Threshold | Audited median | n |
|---|---:|---:|---:|
| `qwen/qwen3.5-122b-a10b` | 41,000,000 | 39,600,000 | 45 |
| `qwen/qwen3.8-2.4t-a95b` | 40,000,000 | 24,000,000 | 45 |

Qwen3.5 historical and fresh low thresholds are both 41,000,000. Qwen3.8 historical is 39,500,000 while fresh is 40,000,000 (+500,000). Provider routing and serving differ across runs, so this is not a causal cross-run comparison.

## Reproduction

Run from the repository root with `uv run --offline analysis/hyp1_moral_comparison/historical_check.py`. Inputs, fields, parser version, and SHA-256 hashes are recorded in [`historical_check.json`](historical_check.json).
