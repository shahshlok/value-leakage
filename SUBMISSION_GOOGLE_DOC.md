# Model Forensics SPAR Take-home — Value Leakage (Donation Bet)
Shlok Shah · hi@shahshlok.com

## Executive summary

I investigated the Donation Bet setting with three linked studies on one fixed corpus (10 models × 100 responses per condition: baseline, below-good, above-good), asking Aditya's two questions directly: what does motivated reasoning look like here, and should we call it unfaithful CoT?

**Findings:**

1. **The behavior is real and survives the anchoring confound.** A control study first showed that numerical context alone (thresholds with no moral content) shifts Fermi estimates, so I only used the mirrored contrast: identical threshold, flipped donation direction. On that contrast, answers shift toward the donation-favorable side by **+15.5%** (nine-model geometric mean, 95% CI [9.4, 22.1]), and the rate of answers crossing the threshold in the favorable direction rises **+32 percentage points** [25.6, 38.6]. All nine cleanly-served models shift in the incentive's direction.
2. **The models' own impartiality statements predict nothing.** A blinded judge found explicit "I will stay impartial" commitments in reasoning at or near ceiling (589 of 716 labeled traces; 100/100 for Qwen 3.5, one of the biggest shifters). Tested three ways — stratifying on the commitment (+14.1% vs +15.5%, paired difference +1.4 pp [−1.4, 4.5]), and directly comparing committing vs non-committing traces in the two models that have both (identical shifts; deepseek-flash crossing-rate shift +50.5 pp in *both* groups) — the commitment carries zero diagnostic information. The most common informal CoT-faithfulness check is empty.
3. **What motivated reasoning looks like:** not stated bias, and mostly not even disclosed trade-offs. In a blinded audit of 40 traces flagged for donation-related adjustment language, **33 of 40 explicitly consider the donation-favorable move and reject it on the page** — yet the population still shifts. Only 8 transparently adopt a donation-driven choice, and removing them barely moves the effect (+15.5% → +15.1%). The influence operates without being narrated.
4. **Where it likely enters (exploratory, not a claim):** decomposing each answer into population × spots-per-giraffe × final adjustment, the shift concentrates in spots-per-giraffe (+8.6% [+4.0, +13.3]) — the one factor with no ground truth — while the memorized population figure (~117k, pinned by every model) stays flat (−1.7%). This matches "bias hides in the least-constrained assumption," but my extraction audit found a 25% error rate, so I report direction only and treat it as the design for the next experiment.

**Answer to "is this unfaithful CoT?":** Yes in a specific, bounded sense; unprovable in the strong sense. At the population level, the reasoning misdescribes the computation: it declares impartiality, rarely discloses influence, and the answers follow the incentive anyway — that is a genuine faithfulness failure of the transcript as a record of what mattered. But no individual trace can be convicted (any single answer could honestly land where it does), and nothing here shows concealment or intent. The precise statement: **CoT self-reports about incentive-independence are behaviorally uninformative, and the incentive's influence is real but almost never verbalized as an influence.**

---

## 1. Setup and the confound that must come first

Models Fermi-estimate the total black spots on all living giraffes; a fixed threshold decides whether a good or bad cause gets a donation; mirrored conditions flip only the direction (above-good vs below-good) while the threshold number is identical per model.

Before interpreting anything as motivated reasoning, I tested whether the numbers alone move estimates. That control used fresh generations, so it could not cover all ten models. I chose **Qwen 3.5 and Qwen 3.8** because they sat at opposite ends of Aditya's original replication: Qwen 3.5 showed relatively high value leakage, Qwen 3.8 almost none. The pair tests whether numerical anchoring is specific to "leaky" models or shows up even where the original moral effect was weak. (Aditya's brief also flagged Qwen 3.5 as worth a closer look; that was a secondary reason, not the design.) They do: in fresh neutral runs with no causes attached, changing the threshold/boundary substantially shifted estimates in both models. Consequence: baseline-vs-incentivized comparisons are uninterpretable (they confound anchoring with motivation), and only the mirrored fixed-threshold contrast is used for claims. What the mirrored design still cannot exclude: the non-moral wording difference between conditions ("exceeds" vs "does not exceed") and provider serving differences. These are the honest residual confounds. The later studies (H6–H8) return to all ten original models and do not depend on this two-model selection.

## 2. The behavioral result

Nine models (one, deepseek-v4-pro, excluded by a predetermined criterion: 52% unparseable answers and 43/100 empty reasoning traces in one condition — a serving artifact). Estimand: difference in mean ln(answer) between conditions, back-transformed; equal model weights; stratified bootstrap, 10,000 replicates, fixed seed. Result: **+15.5% [9.4, 22.1]**; threshold-crossing **+32.1 pp [25.6, 38.6]**. Per-model shifts range +2.8% to +29.2%, all positive. Every number was independently recomputed by a second implementation (agreement within 0.05 pp). Qwen 3.5 illustrates: medians 38M vs 44M around a 41M threshold; 7/50 vs 33/50 answers cross it.

*[Insert `submission_figures/fig3_qwen35_distribution.png` — Caption: **Figure 1. One model's answers, both conditions, same threshold.** Each dot is one of Qwen 3.5's final answers (x-axis: the estimate, log scale). The top row is the condition where answers *above* 41M help the good cause; the bottom row is the mirrored condition where answers *below* 41M help it. The dashed line is the threshold — identical in both rows — and the thick colored bars mark each condition's median. Notice the two clouds sit on opposite sides of the line in exactly the direction that helps the good cause: 33 of 50 answers cross the threshold when crossing helps, versus 7 of 50 when it hurts. Every one of these 100 answers came from a reasoning trace that explicitly promised impartiality.]*

*[Insert `submission_figures/fig2_crossing_rate_dumbbell.png` — Caption: **Figure 2. The same pattern across all ten models.** Each row is one model. The x-axis is the percentage of that model's answers landing above its own fixed threshold. The circle marks that percentage when a high answer *hurts* the good cause; the triangle marks it when a high answer *helps*. The gray bar connecting them is the effect: same question, same threshold, only the donation direction flipped. Every model's triangle sits to the right of its circle — every model crosses the threshold more often when crossing benefits the good cause. The right-hand panel repeats the plot using only answers whose reasoning explicitly claimed impartiality; the bars barely change.]*

## 3. Testing the impartiality statements

A blinded judge (saw reasoning only — no model, condition, threshold, or answer) labeled explicit impartiality commitments. Three tests of whether that label means anything:

- **Prevalence:** at or near ceiling in most models — 589 positive of 716 labeled usable traces. A signal that fires on nearly everything, including the biggest shifters, cannot discriminate. (This ceiling is itself a methodological finding: auditing models' stated impartiality audits the wrong property.)
- **Stratification:** the shift among commitment-positive traces is +14.1% [7.7, 20.9] vs +15.5% overall; prespecified paired bootstrap difference +1.4 pp [−1.4, 4.5]. No attenuation in point estimate; modest attenuation not excluded; even at the interval edge most of the effect remains.
- **Real negative strata:** only two models have many non-committing traces. In both, non-committing traces shift the same as committing ones (deepseek-flash: +2.6% vs +4.0%, binary +50.5 pp in both strata, paired difference +0.02 pp; qwen3p8: +8.2% vs +11.4%). All paired intervals include zero.

*[Insert `submission_figures/fig1_forest_contrasts.png` — Caption: **Figure 3. Does the impartiality claim predict anything? No.** Left panel: for each model, the percentage shift in answers between the two conditions (dot = estimate, horizontal bar = 95% interval; values right of the dashed zero line mean answers moved in the incentive's direction). Blue circles use all answers; orange squares use only answers whose reasoning explicitly claimed impartiality. If the claim marked genuinely unbiased reasoning, the orange markers would sit near zero — instead they sit on top of the blue ones in every model. Right panel: the difference between those two estimates computed within the same bootstrap resamples; every interval includes zero. Bottom three rows: the pooled nine-model result, then the same result after removing the traces that transparently disclosed donation-driven choices — removing them changes almost nothing.]*

The commitment is a prospective promise, not a report of what happened — and the data show promising has no relationship to doing. Three properties must be kept apart: stating an impartiality goal, behaving invariantly, and disclosing influences. Here they fully dissociate.

## 4. What the reasoning actually discloses

A precision-oriented lexical screen retrieved traces with donation-linked adjustment language; 40 were adjudicated blind under a frozen rubric with mandatory quoted evidence spans (hash-verified against source text; adjudicator was a model — a stated limitation). Results: 40/40 promise impartiality; **33/40 consider a donation-favorable move and explicitly reject it**; 13/40 retrospectively deny influence; only 8/40 transparently adopt a donation-driven choice (condition split 6/25 vs 2/15, Fisher p = 0.69 — no asymmetry established). Excluding the 8 disclosed adopters: +15.1% [9.1, 21.7]. Excluding all 18 confirmed-or-uncertain: +14.0% [7.9, 20.5].

Bounded conclusion: the identifiable transparent disclosures do not account for the effect. (Not claimed: that the rest is "hidden" — screen recall is unknown.) The modal picture of motivated reasoning in this task: the model sees the tempting move, declines it out loud, and its number lands favorably anyway.

## 5. Exploratory: where the influence enters

ln(answer) = ln(population) + ln(spots-per-giraffe) + ln(final adjustment), and the condition contrast of the parts sums exactly to the whole. Baseline data validate the premise: every model pins population at the memorized ~117k (tiny spreads), while spots-per-giraffe is unconstrained (medians 185–675 across models, wide spreads). Gated decomposition: population −1.7% [−3.4, −0.0]; **spots-per-giraffe +8.6% [+4.0, +13.3]**; residual +3.1% [+0.7, +5.6]. The shift sits in the factor with no ground truth — the assumption-selection signature. I do not advance this as a finding: my extraction audit failed its own bar (5/20 errors), gate pass rates are condition-imbalanced (up to 17 pp), and the gated subset carries only +10.1% of the effect. It is reported as a validated design plus a directional result.

*[Insert `submission_figures/fig4_h8_decomposition.png` — Caption: **Figure 4. Where in the calculation does the shift enter? (Exploratory.)** Every answer is roughly population × spots-per-giraffe, so the total shift between conditions splits exactly into three additive parts, shown as three rows: the shift in the adopted population number, the shift in the adopted spots-per-giraffe number, and whatever remains between that product and the final reported answer. Dots are estimates, bars are 95% intervals, and the dashed line is zero (no shift). The population row hugs zero — every model uses the well-known ~117,000 figure regardless of condition. The spots-per-giraffe row carries most of the total: the shift concentrates in the one input that has no checkable true value. Read this as a direction, not a finding — the bold footnote on the figure lists the validation failures (25% extraction-audit error rate) that keep it exploratory.]*

## 6. Limitations

- **Wording asymmetry** between mirrored prompts ("exceeds" vs "does not exceed") — the main alternative reading of the behavioral shift; not excluded by this design.
- **Serving and provider differences:** the historical conditions were not perfectly interleaved, and one model's serving artifact (deepseek-v4-pro) shows these effects are real in this corpus.
- **Judge validation is LLM-only:** the impartiality judge (GLM-5.3-Flash, high reasoning) was validated by cross-agreement with a second model on small development audits (~12–14 of 15), never against human ground truth. Known failure mode: false negatives on very long traces (length is confounded with source model). Failed/timed-out judge calls (49) are missing labels, not negatives.
- **Answer extraction is largely parser-based:** 9 answers were human-verified and corrected via source quotes; the remaining parsed answers passed deterministic checks but are not individually human-audited.
- **Model-performed adjudication:** the 40-case disclosure audit was done by a model under a frozen rubric with hash-verified quoted spans — auditable, but not human-coded; the rubric was developed on non-independent traces.
- **Disclosure screen recall is unknown:** regex non-hits are not confirmed non-disclosures; the exclusion analysis bounds only the *identified* disclosures.
- **Condition-asymmetric parse attrition** in claude-opus (more unparseable answers in one condition) could select the analyzed sample; binary-outcome results with full denominators partially mitigate.
- **Threshold placement:** Qwen 3.5's baseline median (41M) coincides exactly with its threshold, so its crossing rate is maximally sensitive to small shifts; the log-scale estimate is the more stable outcome there.
- **Post-treatment conditioning:** stratifying on the judge label supports diagnostic claims only, not within-stratum causal ones.
- **Claude's "reasoning" is an API-returned summary**, not raw CoT; reasoning-content findings for it live in a separate tier.
- **The anchoring control did not test a number-free baseline:** it shows sensitivity to the *magnitude* of a supplied number, not that supplying any number versus none causes shifts.
- **Scope:** ten fixed models, one task, one question; equal-weight fixed-model estimates are descriptive of these models, not population inferences; retrospective and exploratory, not preregistered — prior results were known when later analyses were specified.

## 7. What I did not do, and what I would do next

The brief named two optional directions I did not run, on purpose. **Sentence resampling** is the right causal test, but Aditya noted it is slow and can sit outside the five-hour budget; I used the time to pin *which* sentences to resample rather than resampling blindly. **J-lens / internal representations** on Qwen 3.5 would need activations I do not have from this corpus. Both remain the natural follow-ups, now with a sharper target than they had at the start.

1. **Sentence resampling, now with a target.** Resample the *assumption-adoption sentences* (where spots-per-giraffe is chosen) and separately the *impartiality-commitment sentences*. Prediction from these results: resampling the commitment sentences changes nothing; resampling the assumption sentences moves the answer with the incentive. That tests whether the verbalized commitment is causally inert and localizes the leak.
2. Fresh interleaved mirrored runs with human-validated factor extraction, to turn the Section 5 direction into a claim.
3. Wording-controlled mirrors (same polarity phrasing both directions) to eliminate the residual confound.

## Reproducibility

All analyses are offline and deterministic (fixed seeds); headline numbers independently recomputed twice. Full code, per-trace artifacts, and detailed reports: **https://github.com/shahshlok/value-leakage** (fork of the original replication codebase; start with `FINAL_REPORT.md`, then `analysis/` — hyp1 anchoring control, hyp6 measurement study, hyp7 diagnostic study, hyp8 decomposition probe).
