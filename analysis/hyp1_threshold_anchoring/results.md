# Threshold-anchoring analysis results

Locked plan SHA-256: `477a06a312cd4fc48aa5aca1cf23c25f0079156c37ae6d342fd3955714027b8a`

All estimates are the audited final estimates in `final_estimates.csv`. The outcome is `Z = ln(1 + Y)`; reported effects are `exp(theta) - 1`, with theta the equal-weighted mean of the two model-specific high-minus-low median log differences.

## Confirmatory primary

Holdout rows `i=5..49`, framing `neutral_boundary`, n=180. theta=0.230828; exp(theta)-1=0.259643. 95% percentile bootstrap CI for exp(theta)-1: [0.0300524, 0.372312]. Directional permutation p+1=0.00093999; Holm-adjusted p=0.00187998.

## Pre-specified secondary

The identical locked test on holdout rows, framing `irrelevant_number`, n=180. theta=0.146808; exp(theta)-1=0.158132. 95% percentile bootstrap CI for exp(theta)-1: [0.0245538, 0.352082]. Directional permutation p+1=0.00547995; Holm-adjusted p=0.00547995.

Permutation tests use 100,000 within-model label shuffles, preserve anchor-arm counts, use seed 20260829, and use the plus-one correction. Bootstrap intervals use 10,000 model-by-anchor-stratified resamples and seed 20260829.

## Descriptive and sensitivity analyses

Model-specific outcomes are descriptive only; they are not separately tested. The all-400 analysis includes the five pilot rows per cell and is exploratory. Provider adjustment is reported as a sensitivity check using only estimable actual-provider strata, fixed pooled-count weights within model, equal model weights, and within model-provider permutations; it is not Holm-adjusted.

### Cell summaries

| Universe | Framing | Model | Anchor | n | Median Y | Mean Y | Median Z |
|---|---|---|---:|---:|---:|---:|---:|
| primary_holdout | irrelevant_number | qwen/qwen3.5-122b-a10b | 41,000,000 | 45 | 40,500,000 | 43,107,777.78 | 17.5168 |
| primary_holdout | irrelevant_number | qwen/qwen3.5-122b-a10b | 85,000,000 | 45 | 52,000,000 | 101,475,555.56 | 17.7668 |
| primary_holdout | neutral_boundary | qwen/qwen3.5-122b-a10b | 41,000,000 | 45 | 39,600,000 | 51,268,222.22 | 17.4943 |
| primary_holdout | neutral_boundary | qwen/qwen3.5-122b-a10b | 85,000,000 | 45 | 52,000,000 | 54,978,666.67 | 17.7668 |
| primary_holdout | irrelevant_number | qwen/qwen3.8-2.4t-a95b | 40,000,000 | 45 | 28,000,000 | 29,720,000.00 | 17.1477 |
| primary_holdout | irrelevant_number | qwen/qwen3.8-2.4t-a95b | 80,000,000 | 45 | 29,250,000 | 29,122,222.22 | 17.1914 |
| primary_holdout | neutral_boundary | qwen/qwen3.8-2.4t-a95b | 40,000,000 | 45 | 24,000,000 | 27,637,777.78 | 16.9936 |
| primary_holdout | neutral_boundary | qwen/qwen3.8-2.4t-a95b | 80,000,000 | 45 | 29,000,000 | 28,376,666.67 | 17.1828 |
| all_400_exploratory | irrelevant_number | qwen/qwen3.5-122b-a10b | 41,000,000 | 50 | 41,000,000 | 45,817,000.00 | 17.5291 |
| all_400_exploratory | irrelevant_number | qwen/qwen3.5-122b-a10b | 85,000,000 | 50 | 49,000,000 | 95,528,000.00 | 17.7071 |
| all_400_exploratory | neutral_boundary | qwen/qwen3.5-122b-a10b | 41,000,000 | 50 | 39,000,000 | 49,721,900.00 | 17.4791 |
| all_400_exploratory | neutral_boundary | qwen/qwen3.5-122b-a10b | 85,000,000 | 50 | 51,875,000 | 54,195,800.00 | 17.7643 |
| all_400_exploratory | irrelevant_number | qwen/qwen3.8-2.4t-a95b | 40,000,000 | 50 | 28,500,000 | 28,988,000.00 | 17.1653 |
| all_400_exploratory | irrelevant_number | qwen/qwen3.8-2.4t-a95b | 80,000,000 | 50 | 29,125,000 | 29,740,000.00 | 17.1871 |
| all_400_exploratory | neutral_boundary | qwen/qwen3.8-2.4t-a95b | 40,000,000 | 50 | 24,000,000 | 28,376,000.00 | 16.9936 |
| all_400_exploratory | neutral_boundary | qwen/qwen3.8-2.4t-a95b | 80,000,000 | 50 | 29,000,000 | 28,479,000.00 | 17.1828 |

### Measurement and pilot accounting

Of 400 final-estimate rows, 368 are `parser_confirmed` and 32 are `blind_adjudication`. Pilot rows `i=0..4` are excluded from both confirmatory analyses and appear only in the all-400 exploratory summaries.

### Provider support

Provider support details, including unsupported strata and the >=5-per-arm rule, are in `results.json` under `sensitivity.provider_adjusted`.

No additional hypothesis tests or alternate outcome transformations were run.
