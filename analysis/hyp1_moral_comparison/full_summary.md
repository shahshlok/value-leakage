# Full-run descriptive moral comparison

Full run: all 200 moral responses (50 per model/condition cell) and all 400 neutral responses (50 per model/framing/anchor cell). The early 40 moral responses were collected under the same protocol and are included here; the locked fresh-extension and neutral-holdout analyses remain sensitivities. Bootstrap conditions independently (10,000 resamples; seed 20260830); intervals are pointwise 95% percentile intervals.

## ALL200 moral direction (descriptive)

| Model | Below-good median (n) | Above-good median (n) | Ratio - 1 (95% CI) |
|---|---:|---:|---:|
| qwen3.5-122b-a10b | 38500000.0 (50) | 42000000.0 (50) | 0.0909 (0.00962, 0.211) |
| qwen3p8-2p4t-a95b | 29000000.0 (50) | 31000000.0 (50) | 0.069 (-0.025, 0.222) |

## ALL400 neutral numerical anchoring (descriptive)

| Model | Framing | Low anchor median (n) | High anchor median (n) | High/low - 1 (95% CI) |
|---|---|---:|---:|---:|
| qwen/qwen3.5-122b-a10b | neutral_boundary | 39000000.0 (50) | 51875000.0 (50) | 0.33 (0.147, 0.578) |
| qwen/qwen3.5-122b-a10b | irrelevant_number | 41000000.0 (50) | 49000000.0 (50) | 0.195 (0.0238, 0.5) |
| qwen/qwen3.8-2.4t-a95b | neutral_boundary | 24000000.0 (50) | 29000000.0 (50) | 0.208 (-0.16, 0.237) |
| qwen/qwen3.8-2.4t-a95b | irrelevant_number | 28500000.0 (50) | 29125000.0 (50) | 0.0219 (-0.094, 0.25) |

## Sensitivity analyses

The locked fresh extension (160 responses) is the unseen-data check; its intervals are compatible with zero, weakening the moral-direction evidence from the descriptive ALL200 combination. The neutral holdout remains a prior 360-response reference. The ALL200 combination is not a preregistered confirmation.

| Model | Fresh extension below (n) | Fresh extension above (n) | Ratio - 1 (95% CI) |
|---|---:|---:|---:|
| qwen3.5-122b-a10b | 38750000.0 (40) | 40500000.0 (40) | 0.0452 (-0.0216, 0.201) |
| qwen3p8-2p4t-a95b | 29125000.0 (40) | 30000000.0 (40) | 0.03 (-0.0769, 0.157) |

## Reference context

See the root [hypothesis_1_report.md](../../hypothesis_1_report.md) for the human-facing synthesis. The neutral holdout medians and audit references are retained in `full_results.json`; the holdout has 45 usable observations per anchor/cell. Historical moral medians and original neutral pooled references are separate context, not interchangeable fresh evidence.

This is a descriptive uncertainty statement, not a significance claim. Number-magnitude manipulation at two anchors supports number sensitivity, not presence-versus-absence (there is no contemporaneous number-free baseline). Multiple providers are routing variation, not evidence that weights or quantization changed. Missingness and ambiguous counts are retained per cell in `full_results.json`; zero estimates are valid values. Neutral-anchor and moral-direction experiments are independent, not a matched three-arm design.

Plot caveats: jitter shows every valid individual value and retains outliers, black bars mark medians, values are plotted in millions on a log scale (linear near zero in the lower row), and y-scales are shared within each model row. Prompt, provider, and batch differences remain possible.
