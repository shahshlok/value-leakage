# Hypothesis 1: does a neutral number move the estimate?

## Bottom line

The neutral-number results are consistent with anchoring: the models gave higher median estimates in the higher-number conditions, even without a good or bad cause. The effect was more consistent across wording conditions for Qwen 3.5 than Qwen 3.8.

Changing which side benefited the good cause produced smaller shifts in our full moral dataset. Qwen 3.5 gives suggestive evidence of this extra moral-direction effect; Qwen 3.8 remains uncertain. We cannot conclude that anchoring explains all of the original value-leakage result, or that we have established a particular reasoning mechanism.

This report presents the full datasets: **400 neutral responses and 200 moral responses**, with 50 responses per model and condition. All tables use the median final numerical answer. M means million. These are estimates of the total number of spots on living giraffes, not measurements of the true total.

## 1. Neutral number, no moral consequence

We used two ways of putting a number into the same Fermi question:

- **Neutral boundary:** the number separated answers into two bookkeeping groups. Neither group was preferred, the classification had no consequences, and the cutoff was described as independent of the correct answer.
- **Irrelevant number:** the prompt included a number described as unrelated to the question, with no donation or good/bad outcome.

Within each wording condition, we changed only the number. Qwen 3.5 received 41M or 85M; Qwen 3.8 received 40M or 80M. There were 50 responses at each number for each model and wording condition.

| Wording | Model | Numbers supplied, low → high | Median answer, low → high | Change |
|---|---|---:|---:|---:|
| Neutral boundary | Qwen 3.5 | 41M → 85M | 39M → 51.875M | +33.0% |
| Neutral boundary | Qwen 3.8 | 40M → 80M | 24M → 29M | +20.8% |
| Irrelevant number | Qwen 3.5 | 41M → 85M | 41M → 49M | +19.5% |
| Irrelevant number | Qwen 3.8 | 40M → 80M | 28.5M → 29.125M | +2.2% |

**What this tells us:** estimates moved upward when the neutral boundary moved upward. Qwen 3.5 also moved under the irrelevant-number wording. Qwen 3.8 barely moved under that wording, so the number's role in the prompt may matter. We did not establish a separate statistical interaction between model and wording.

The models did not simply copy the larger number. For example, Qwen 3.5's median was about 52M when the boundary was 85M. Anchoring can mean a partial shift, not agreement with the number.

Strictly, this tests **sensitivity to the size of a supplied number**, not the effect of a number's presence versus absence. We did not collect a same-setup number-free baseline. Also, neutral conditions were collected in separate blocks rather than interleaved, which limits a fully isolated causal claim.

## 2. What we found in Aditya's existing responses

We next checked his existing final answers for these two models. This is our preliminary reanalysis of his dataset, not a reproduction of his trajectory or MRF analysis.

The threshold stays fixed within each model. Only the assignment of good and bad causes switches:

- **Below-good:** an answer at or below the threshold benefits the good cause.
- **Above-good:** an answer above the threshold benefits the good cause.

| Model | Historical threshold | Below-good median | Above-good median | Change |
|---|---:|---:|---:|---:|
| Qwen 3.5 | 41M | 38M, 88 usable | 44M, 95 usable | +15.8% |
| Qwen 3.8 | 39.5M | 39.15M, 80 usable | 40.8M, 93 usable | +4.2% |

Each historical condition had 100 attempted responses. This quick check used only answers with a clear parser-extracted final estimate. Missing or ambiguous responses were excluded; unlike our new data, these historical extractions have not had a complete answer-by-answer audit. Unequal missingness can affect the comparison.

Both point estimates moved in the direction that benefited the good cause, more strongly for Qwen 3.5. Since the numerical threshold did not change, a direction-insensitive pull toward that number alone would not predict this difference. This is a reason to investigate moral-direction sensitivity, not proof of what happened inside the reasoning.

## 3. Our full moral run

We collected 200 moral responses: 50 below-good and 50 above-good for each model. We reused Aditya's moral prompt template verbatim. Qwen 3.5's threshold remained 41M. Qwen 3.8's was 40M rather than the historical 39.5M, matching our neutral low boundary. Conditions were mixed in randomized request order.

| Model | Below-good median | Above-good median | Change | 95% bootstrap interval for change |
|---|---:|---:|---:|---:|
| Qwen 3.5 | 38.5M | 42M | +9.1% | +1.0% to +21.1% |
| Qwen 3.8 | 29M | 31M | +6.9% | −2.5% to +22.2% |

The full Qwen 3.5 sample suggests a modest moral-direction effect: the median moves from below the threshold to above it when the good cause switches sides. The Qwen 3.8 sample points in the same direction, but its uncertainty interval includes no difference. Its two medians also remain below its 40M threshold: moving upward is not the same as crossing the threshold or always choosing the good outcome.

For context, at the same low thresholds our neutral-boundary medians were 39M for Qwen 3.5 and 24M for Qwen 3.8. Qwen 3.5's moral medians straddle its neutral median; both Qwen 3.8 moral medians are higher than its neutral median. These are separate-batch, differently worded comparisons, not a concurrently randomized three-condition experiment. They do not isolate why those levels differ.

All 200 new moral responses were usable after reviewing the final answers. There were no errors, empty answers, or truncated responses. Large answers were kept, including a 445M answer for Qwen 3.5. We did not remove inconvenient outliers.

**How strong is this evidence?** The full-run moral pattern is suggestive, not a firm replication. Collection was expanded after early same-protocol responses had been inspected, and those responses remain in the full dataset. The previously specified check using only the later, unseen responses gives smaller changes: +4.5% for Qwen 3.5 and +3.0% for Qwen 3.8, with both intervals including zero. That sensitivity check weakens a strong claim of a reproducible moral effect; it does not prove the effect is absent.

## 4. What we can conclude

1. **Neutral numbers matter in this task.** The boundary experiment shows a clear upward shift in median answers at the higher number. The irrelevant-number result is stronger for Qwen 3.5 and weak for Qwen 3.8.
2. **The historical moral answers contain a directional signal.** Both models' medians were higher in above-good than below-good, but the historical check is preliminary and has missing answers.
3. **Our new moral answers show a smaller, less secure signal.** The full sample is suggestive for Qwen 3.5 and uncertain for Qwen 3.8. The unseen-response check is inconclusive for both.
4. **Anchoring is an important control, not a complete explanation.** We cannot subtract the neutral percentage shift from the moral percentage shift: one changes the number, the other changes the consequences at a fixed number. They are different interventions.
5. **This analysis does not locate the bias inside reasoning.** It studies final estimates. It does not establish biased assumptions, unfaithful chain of thought, or a causal role for particular reasoning sentences.

The appropriate take-home claim is: **“We found evidence consistent with neutral numerical anchoring, so a neutral-number control is necessary when interpreting Donation Bet behavior. A fixed-threshold moral follow-up showed suggestive but not robust additional direction sensitivity.”**

## Methods and limits

- **Same-day setup:** the fresh experiment was completed on one day, using the same two OpenRouter model IDs and requested settings: high reasoning, a 64,000-token maximum, temperature 1, top-p 1, and concurrency 10 per model. We have no evidence that model weights or quantization changed during it. We do not present such a change as an observed caveat.
- **Actual routing:** provider selection was unpinned and recorded providers varied. This is observed routing variation, not evidence of changed weights. The neutral cells were collected in blocks, so time and routing cannot be fully separated from condition. The moral directions were interleaved.
- **Historical differences:** Aditya's Qwen 3.5 used a pinned DeepInfra FP4 route; his Qwen 3.8 used Fireworks. Our new runs used unpinned OpenRouter. Historical comparisons are therefore not exact serving replications, and Qwen 3.8's threshold also changed slightly.
- **Full-run presentation:** full-run tables are descriptive summaries of all collected usable responses. Earlier locked analysis splits are preserved rather than silently relabeled. The neutral locked check used 45 responses per cell and found a pooled boundary shift of +26% (95% interval +3% to +37%), with a secondary irrelevant-number shift of +16% (+2% to +35%). These are equal-model-weight log-scale summaries, not the arithmetic average of the full-run table's percentages. The moral unseen-response check used 40 per cell: Qwen 3.5 +4.5% (−2.2% to +20.1%); Qwen 3.8 +3.0% (−7.7% to +15.7%).
- **Measurement:** all 400 neutral final estimates were audited; 32 needed adjudication. All 200 moral final estimates were reviewed with explicit condition labels hidden. The answer itself can reveal the condition, so this is not perfect blinding. Moral review resolved 19 parser ambiguities and corrected one intermediate-versus-final number. Exact evidence spans and source identities are saved.
- **Uncertainty:** moral change is above-good median divided by below-good median, minus one. Intervals use 10,000 independent within-condition bootstrap resamples, seed 20260830. They describe sampling uncertainty under independent, exchangeable responses, not provider confounding or adaptive collection. They are per-model intervals without a multiple-comparison adjustment.
- **Scope:** two selected models and one Fermi question. This does not establish a general ranking of models or that either model's estimate is factually correct.
- **Cost:** recorded cost was about $9.10 for the neutral dataset and $4.34 for the moral dataset, about $13.45 total for these 600 responses. This excludes earlier abandoned model attempts and any analysis tooling.

## Evidence and reproduction

Paths below are relative to the repository root, `/Users/shlok/value-leakage`.

- Neutral raw data: `runs/anchoring_pilot_qwen_pair/` (the directory name is historical; it contains the full 400-response dataset).
- Neutral audited answers and locked analysis: `analysis/hyp1_threshold_anchoring/final_estimates.csv`, `results.json`, `analysis_plan.md`.
- Historical quick check: `analysis/hyp1_moral_comparison/historical_check.json` and `historical_check.md`.
- Full moral raw data and source provenance: `runs/moral_full_qwen_pair/`.
- Moral audited answers and review evidence: `analysis/hyp1_moral_comparison/full_estimates.csv`, `full_audit_differences.json`, and `full_source_manifest.json`.
- Moral analysis, full neutral summaries, and uncertainty: `analysis/hyp1_moral_comparison/full_results.json`.
- Full-run figure: `analysis/hyp1_moral_comparison/h1_summary.png`. Points are individual answers and black bars are medians. The vertical axis is logarithmic, with a linear region near zero in the lower row to include a zero answer. Large answers remain visible.

Reproduce the audited moral table and analysis locally, without new API calls:

```sh
uv run python analysis/hyp1_moral_comparison/full_extract.py --finalize
uv run python analysis/hyp1_moral_comparison/full_analyze.py
```

The frozen plans and raw records are retained for an honest audit trail. H1 collection and analysis are complete; stronger causal or reasoning-mechanism claims would require a separate experiment.
