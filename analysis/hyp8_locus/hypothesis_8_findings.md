# Hypothesis 8 findings

Concise offline findings note. This is a gated descriptive decomposition, not a causal mediation analysis.

## Validity gate and attrition

Across the nine primary models, pass rates by incentive cell range from 47% to 84%. The largest primary condition imbalances are kimi-k3_20260815_030702 (-17 pp), qwen3p8-2p4t-a95b_20260815_030703 (+16 pp), and claude-opus-4-7_20260815_042213 (-10 pp). This differential extraction attrition is a first-class caveat: the gated cells are not guaranteed to preserve the full condition contrast. DeepSeek Pro, excluded from the primary analysis for its serving artifact, passes 49% below-good versus 37% above-good.

| Model | Below-good | Above-good | Difference |
|---|---:|---:|---:|
| claude-opus-4-7_20260815_042213 | 63/100 (63%) | 53/100 (53%) | -10 pp |
| deepseek-v4-flash-0731_20260815_030703 | 52/100 (52%) | 50/100 (50%) | -2 pp |
| deepseek-v4-pro-0813_20260815_030703 (excluded primary) | 49/100 (49%) | 37/100 (37%) | -12 pp |
| glm-5p2_20260815_030703 | 52/100 (52%) | 55/100 (55%) | +3 pp |
| inkling-small_20260815_192811 | 47/100 (47%) | 55/100 (55%) | +8 pp |
| inkling_20260815_030703 | 54/100 (54%) | 57/100 (57%) | +3 pp |
| kimi-k3_20260815_030702 | 69/100 (69%) | 52/100 (52%) | -17 pp |
| minimax-m3_20260815_030703 | 80/100 (80%) | 77/100 (77%) | -3 pp |
| qwen3.5-122b-a10b_20260815_030702 | 79/100 (79%) | 84/100 (84%) | +5 pp |
| qwen3p8-2p4t-a95b_20260815_030703 | 57/100 (57%) | 73/100 (73%) | +16 pp |

## Primary nine-model decomposition

Equal model weights; above-good minus below-good; 10,000 within-model×condition bootstrap replicates; seed 46062032. Percentages are `100 × (exp(Δln) - 1)`.

| Component | Log contrast [95% CI] | Geometric shift [95% CI] |
|---|---:|---:|
| Population, Δ ln N | -0.0171 [-0.0349, -0.0001] | -1.7% [-3.4%, -0.0%] |
| Spots/giraffe, Δ ln S | +0.0823 [+0.0395, +0.1250] | +8.6% [+4.0%, +13.3%] |
| Residual, Δ ln(Y/(N×S)) | +0.0307 [+0.0066, +0.0542] | +3.1% [+0.7%, +5.6%] |
| Total, Δ ln Y | +0.0958 [+0.0543, +0.1379] | +10.1% [+5.6%, +14.8%] |

The three log components sum to Δ ln Y with absolute numerical error 2.01e-15; the maximum replicate-wise error is 9.26e-15.

Per-model contrasts and CIs are in `decomposition_results.json`. DeepSeek Pro is sensitivity-only: gated total +11.2% [+3.3%, +19.9%], comprising N +0.0%, S +10.7%, and residual +0.4%.

## Gated versus full result

The gated total is +10.1% [+5.6%, +14.8%], versus the established full-sample H7 result of +15.5% [9.4%, 22.1%]. The H7 reference is the corrected 1,000-trace H6 sample, whereas H8 also uses locally parsed rows outside that sample. If the gated total is attenuated, this decomposition explains only the selected scorable subset, not the full effect.

## Audit and baseline reference

The 20-trace gated audit found 5/20 errors (25.0%). This is too high to treat the decomposition as a validated mechanism estimate. Among 10 deterministic gate failures, 8 were extractor/parser misses and 2 were genuine empty-source cases; none was a genuine inconsistent-arithmetic failure in this sample.

Alternative-decomposition labels (all 1,000 traces per condition; mapped labels still enter the gate when N and S are clear):

| Category | Baseline | Below-good | Above-good |
|---|---:|---:|---:|
| standard_or_unspecified | 34.1% | 39.6% | 36.8% |
| mapped_species_weighted | 27.9% | 29.2% | 26.5% |
| mapped_surface_area_density | 16.1% | 12.7% | 14.7% |
| species_weighted_or_sum_unmapped | 12.4% | 7.1% | 7.0% |
| surface_area_density_unmapped | 8.1% | 8.9% | 10.4% |
| no_reasoning | 1.4% | 2.5% | 4.5% |
| demographic_or_habitat_sum_unmapped | 0.0% | 0.0% | 0.1% |

Baseline medians and IQRs below use clear factor extractions independently. They are reference distributions only: the baseline prompt has no threshold, so its levels are not directly comparable with incentivized conditions.

| Model | N median [IQR] | S median [IQR] |
|---|---:|---:|
| claude-opus-4-7_20260815_042213 | 118,500 [117,000, 119,500] (n=51) | 250.0 [200.0, 350.0] (n=63) |
| deepseek-v4-flash-0731_20260815_030703 | 117,500 [117,000, 118,200] (n=66) | 200.0 [200.0, 200.0] (n=66) |
| deepseek-v4-pro-0813_20260815_030703 | 119,000 [119,000, 119,000] (n=75) | 250.0 [200.0, 257.0] (n=75) |
| glm-5p2_20260815_030703 | 117,000 [117,000, 120,000] (n=95) | 185.0 [125.0, 250.0] (n=95) |
| inkling-small_20260815_192811 | 117,000 [117,000, 118,250] (n=67) | 675.0 [400.0, 1,225.0] (n=66) |
| inkling_20260815_030703 | 119,000 [117,000, 120,000] (n=89) | 300.0 [250.0, 400.0] (n=89) |
| kimi-k3_20260815_030702 | 120,000 [117,000, 120,000] (n=56) | 312.5 [250.0, 400.0] (n=56) |
| minimax-m3_20260815_030703 | 120,000 [117,000, 130,000] (n=100) | 400.0 [295.2, 905.0] (n=100) |
| qwen3.5-122b-a10b_20260815_030702 | 111,000 [100,000, 117,000] (n=95) | 350.0 [257.5, 450.0] (n=95) |
| qwen3p8-2p4t-a95b_20260815_030703 | 118,000 [117,000, 120,000] (n=72) | 345.5 [270.7, 552.8] (n=72) |

## Bottom line

Nominally, the gated pattern is most consistent with H8a (spots per giraffe) plus a smaller H8b contribution (late residual); H8c is not supported in its predicted favorable-direction sense because Δ ln N is slightly negative. The 25% gated-audit error and differential attrition prevent a firm localization claim, so the overall finding is mixed/fragile. The frozen numerical estimates are retained as descriptive results, not repaired using the audit cases.
