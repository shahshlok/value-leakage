# Moral comparison pilot

Exploratory 40-response pilot. All 40 final answers reviewed with condition labels hidden; answer text itself may reveal the condition.

Aditya's original moral wording was reused. Within each model, only which side benefits the good cause changes; the threshold stays fixed.

| Model | Threshold | Below-good median | Above-good median | Change |
|---|---:|---:|---:|---:|
| Qwen 3.5 | 41M | 38.25M (n=10) | 44.5M (n=10) | +16% |
| Qwen 3.8 | 40M | 26M (n=10) | 35M (n=10) | +35% |

## Uncertainty

Median-ratio intervals resample above-good and below-good independently (10,000 draws, seed 20260829). They are rough pilot intervals, not definitive evidence.

- Qwen 3.5: 95% interval for the median change: +6% to +84%.
- Qwen 3.8: 95% interval for the median change: -11% to +52%.

## What this tells us

If above-good estimates exceed below-good estimates, this is consistent with sensitivity to the moral consequence beyond a direction-insensitive numerical anchor. It does not identify where the effect enters reasoning or establish human-like motivation.

Only 10 responses per condition were generated. OpenRouter chose multiple providers. Do not claim a stable model ranking or treat a null-compatible interval as proof of no effect.

The earlier neutral results and Aditya's data are reference points only. Neutral wording and generation batches differ. Historical Qwen 3.8 used Fireworks and a 39.5M threshold, versus OpenRouter and 40M here.

## Data quality and files

Completed: 40; usable after measurement: 40. Recorded cost: $0.835475.
Quality counts: `{'failures': 0, 'empty': 0, 'truncated': 0, 'parser_status': {'ambiguous': 5, 'clear': 35}}`. The parser's five flagged answers remain recorded even after audit resolution.
Audit changes or resolutions: 5. Providers: `{'DeepInfra': 10, 'Modal': 8, 'Novita': 9, 'SiliconFlow': 11, 'Together': 2}`.

Raw data: `runs/moral_pilot_qwen_pair/`. Numerical results: `pilot_results.json`. Row-level estimates and mapping: `pilot_extractions.csv`. Audit evidence: `pilot_audit.csv`. Historical check: `historical_check.md`.

Reproduce: `uv run --offline analysis/hyp1_moral_comparison/pilot_analyze.py --audit analysis/hyp1_moral_comparison/pilot_audit.csv`.
