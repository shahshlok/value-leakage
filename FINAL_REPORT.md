# Committed to Impartiality, Moved by the Incentive: What Impartiality Claims in Chain-of-Thought Do and Do Not Predict

**Value leakage in the Donation Bet task — final research report.**

---

## Abstract

In the Donation Bet task, a model produces a Fermi estimate (the total number of black spots on all living giraffes) and a fixed numerical threshold determines whether a good or a bad cause receives a donation. In mirrored conditions, estimates above the threshold benefit the good cause, or below it, with the threshold held numerically identical. We report three linked findings from a fixed corpus of ten models (100 responses per model per condition, plus 100 baseline responses). First, a control study shows that numerical context alone — thresholds and boundaries with no moral content — substantially shifts estimates, so only the mirrored fixed-threshold contrast supports incentive-direction inferences. Second, using that contrast, final answers shift toward the donation-favorable side by +15.5% (nine-model geometric mean, 95% bootstrap CI [9.4, 22.1]); the rate of answers crossing the threshold in the donation-favorable direction rises by +32.1 percentage points [25.6, 38.6]. Third, and centrally: explicit impartiality commitments in the visible reasoning, identified by a blinded judge, are diagnostically empty. They occur at or near ceiling (589 of 716 labeled traces with usable answers; 100/100 for the model with among the largest shifts), the commitment-positive stratum shifts +14.1% [7.7, 20.9] (paired difference from the unconditional contrast: +1.4 pp, 95% CI [−1.4, 4.5]) — and no adequate commitment-negative stratum exists in the models driving the effect. A blinded, rubric-frozen, span-verified adjudication of 40 disclosure candidates finds that the modal trace explicitly considers and rejects a donation-favorable move (33/40), while only 8 transparently adopt one; excluding those traces leaves the shift essentially unchanged (+15.1%). We conclude that the most common informal check on chain-of-thought faithfulness — whether the model declares impartiality — predicts nothing about incentive sensitivity in this setting, and that identifiable transparent disclosure does not account for the behavior. We explicitly do not claim hidden influence, deception, or per-trace unfaithfulness, and we document the residual confounds this design cannot exclude.

---

## 1. Introduction

If a model's chain-of-thought (CoT) is to serve as a safety-relevant window into its computation, the factors that move its outputs should be visible in its reasoning. The Donation Bet task creates a precise opportunity to test one slice of this: a morally-loaded incentive (which cause receives a donation) is attached to an otherwise neutral estimation problem, and the direction of the incentive is flipped between conditions while everything numerical is held fixed. Any systematic answer difference between the mirrored conditions is behavior the reasoning should, if faithful, account for.

The naive analysis — read the reasoning, check whether the model "seems biased" — fails in two directions at once. It can manufacture positive findings, because numerical context alone moves Fermi estimates (Section 2), and it can manufacture reassurance, because models pervasively *declare* impartiality whether or not their behavior is impartial (Sections 4–5). This report is organized around dismantling both failure modes and then measuring what remains.

Three questions structure the analysis:

1. **Behavioral:** with numerical anchoring controlled by design, do answers follow the donation direction?
2. **Diagnostic:** does an explicit impartiality commitment in the reasoning predict smaller incentive sensitivity?
3. **Disclosure:** is the behavioral effect accounted for by traces that transparently disclose donation-driven choices?

Throughout, three properties are kept strictly separate, because conflating them is the central error in informal CoT-faithfulness assessment: (i) *stating* an impartiality goal; (ii) *behaving* invariantly under the incentive flip; (iii) *disclosing* the factors that affected the decision. These are logically independent, and the data show they dissociate in practice.

## 2. Control study: numerical anchoring must be dealt with first

Before interpreting any Donation Bet behavior as motivated reasoning, we tested whether the numerical scaffolding alone moves estimates. It does: in fresh neutral-number experiments (no good or bad cause; threshold or boundary values varied), changing the numerical context substantially shifted estimates. A direct moral-direction comparison in that fresh data found suggestive movement toward the donation-favorable answer — strongest in one model — but the effect was smaller and less robust in held-out data.

Two consequences shape everything downstream. First, comparisons between incentivized conditions and baseline (no threshold mentioned) are uninterpretable as motivated reasoning, because they confound moral content with numerical anchoring. Second, the mirrored contrast — identical threshold, flipped donation direction — differences the anchor out by design and is the only contrast used for headline claims below. The mirrored design does *not* control the non-moral wording difference between conditions ("exceeds" versus "does not exceed") or provider serving differences; these remain the leading residual confounds and are revisited in Section 7.

Full details: `analysis/hyp1_moral_comparison/hypothesis_1_report.md`, `analysis/hyp1_threshold_anchoring/`.

## 3. Data and measurement

**Corpus.** Ten models, three conditions each (`baseline`, `below_good`, `above_good`), 100 responses per cell; 3,000 raw records with reasoning text (or, for the Anthropic model, an API-returned reasoning summary), visible answer, condition, threshold, and generation metadata. Thresholds are identical across the two incentivized conditions within each model (ranging from 20.874M to 120M across models).

**Analysis sample.** The measurement study sampled 1,000 traces (50 per model per incentivized condition, stratified random among eligible traces). Source-grounded answer extraction with nine independently verified corrections yields 841 usable visible answers. A blinded judge (GLM-5.3-Flash) saw reasoning text only — no model identity, condition, threshold, or answer — and labeled explicit impartiality commitments: 951 usable labels, 727 positive. Known limitations: 49 label failures (timeouts/errors, not negatives) and long-trace false negatives. All joins key on source row index, model, and condition, never list position.

**Predetermined exclusion.** deepseek-v4-pro-0813 is excluded from primary estimates by a serving-artifact criterion: its `above_good` cell has 52% unparseable answers and 43/100 empty reasoning traces — severe condition-asymmetric attrition unlike any other model. Its own contrast (+12.5%) is reported for completeness and changes no conclusion. Nine models remain.

**Verification.** Every headline number below was independently recomputed by a second implementation (`verify_h7_independent.py`) from source artifacts; point estimates agreed to within 0.05 percentage points. All adjudication evidence spans hash-match source reasoning.

## 4. Methods

**Estimand.** Per model, the difference in mean ln(answer) between `above_good` and `below_good` among finite positive answers, back-transformed as exp(Δ)−1 (a geometric-mean ratio minus one); nine-model equal-weight mean; stratified bootstrap (10,000 replicates, fixed seed, resampling whole records within model × condition). A binary companion outcome uses each model's own threshold in both arms: the difference in P(answer > threshold). Missing answers are excluded from point estimates with per-cell denominators reported; the binary outcome retains all finite answers. This is a descriptive estimand for these fixed models — not a population inference — and the work is retrospective and exploratory, not preregistered.

**Diagnostic stratification.** The behavioral contrast is recomputed within the judge-label strata. The impartiality label is a post-treatment variable: within-stratum *causal* readings (e.g., "the effect among truly impartial traces") are not supported. For the *predictive-value* question — does the label carry information about behavior? — conditioning on the label is the estimand, exactly as stratifying on a diagnostic test's result is how the test is evaluated.

**Disclosure adjudication.** Candidates were retrieved by a precision-oriented lexical screen (adjustment language within a proximity window of donation-lexicon terms) over the headline cohort; retrieval is not classification, non-hits are not confirmed non-disclosures, and recall is unknown. A hash-selected sample of 40 hits (25 `above_good`, 15 `below_good`) was adjudicated in blinded packets under a frozen rubric (v1) with condition and outcome metadata hidden. **The adjudicator was a model (Claude Sonnet), not a human.** Every category call required a source-span citation, and all spans were hash-verified against the original reasoning, making each adjudication auditable; model adjudication remains a stated limitation. Rubric categories (overlapping, recorded separately): prospective impartiality promise; retrospective denial of influence; donation-favorable option considered and rejected; donation-driven choice finally adopted; explicit disclosure linking the final number to the donation.

## 5. Results

### 5.1 Answers follow the donation direction

**Nine-model contrast: +15.5% [9.4, 22.1]. Threshold-crossing: +32.1 pp [25.6, 38.6].**

| Model | exp(Δ)−1 | n (below / above) | Crossing below → above |
|---|---:|---|---|
| glm-5p2 | +29.2% | 33 / 30 | 42.4% → 76.7% |
| qwen3.5-122b-a10b | +22.4% | 50 / 50 | 14.0% → 66.0% |
| minimax-m3 | +21.3% | 43 / 43 | 39.5% → 53.5% |
| claude-opus-4-7 | +17.3% | 47 / 37 | 14.9% → 56.8% |
| inkling-small | +17.1% | 33 / 41 | 18.2% → 36.6% |
| qwen3p8-2p4t-a95b | +11.5% | 47 / 47 | 38.3% → 78.7% |
| kimi-k3 | +10.7% | 43 / 38 | 39.5% → 71.1% |
| inkling | +9.0% | 35 / 36 | 25.7% → 36.1% |
| deepseek-v4-flash-0731 | +2.8% | 50 / 50 | 16.0% → 62.0% |
| *deepseek-v4-pro-0813 (excluded)* | *+12.5%* | *46 / 42* | — |

Every point estimate is direction-following, with wide heterogeneity (+2.8% to +29.2%); individual model intervals are marginal and several include zero. The two outcomes measure different things: deepseek-flash pairs a near-zero log shift with a +46 pp crossing change because its answers cluster near the threshold, where small movements flip the decision. Qwen 3.5 is the cleanest single illustration: medians 38M below-good versus 44M above-good around a 41M threshold; 7/50 versus 33/50 answers cross it.

### 5.2 The impartiality commitment predicts nothing

Label prevalence among traces with usable answers (nine models, log-eligible convention): **589 positive, 127 negative, 37 missing** (of 753). The distribution is extreme and concentrated: claude-opus 84/84 positive, qwen3.5 100/100, inkling-small 70/74; only deepseek-flash (51) and qwen3p8 (37) have substantial negative strata.

**Contrast within the commitment-positive stratum: +14.1% [7.7, 20.9]**, against +15.5% [9.4, 22.1] unconditional. The prespecified paired bootstrap difference (unconditional minus stratified, computed within the same replicates) is **+1.4 pp, 95% CI [−1.4, 4.5]** (10,000/10,000 replicates usable). We prespecified no equivalence tolerance and therefore claim no equivalence: the point estimate shows no attenuation, the interval does not exclude modest attenuation or amplification, and even at the interval's attenuation edge the stratified contrast retains roughly two-thirds of the unconditional shift. The pooled commitment-negative contrast is undefined under the fixed nine-model design: two models contribute empty cells and most others single-digit ones.

The diagnostic conclusion stands on two legs, the second stated candidly because it is partly mechanical:

1. **No attenuation.** Where comparison is possible, committing to impartiality is associated with no reduction in incentive sensitivity. The sharpest case: qwen3.5, 100/100 commitment-positive, +22.4% shift, crossing rate 14% → 66%.
2. **Ceiling by construction.** Commitment-positive traces are 589/753, so the stratified estimate could not have diverged far from the unconditional one arithmetically. That is itself the finding: a proxy that fires on nearly everything — including on the models with the largest shifts — cannot discriminate incentive-free from incentive-sensitive reasoning. Its failure mode is emptiness, not miscalibration.

A third leg exists where the ceiling breaks: deepseek-flash and qwen3p8 have substantial commitment-negative strata, supporting a direct within-model test. In both, non-claiming traces shift like claiming ones (deepseek-flash: +2.6% [+0.6, +5.1] vs +4.0% [+1.3, +7.1], binary crossing +50.5 pp in *both* strata with paired difference +0.02 pp; qwen3p8: +8.2% [−7.6, +24.4] vs +11.4% [+0.6, +24.8]). All paired positive-minus-negative intervals include zero. Strata are small, so only large moderation is excluded — but where the commitment can be tested against a real negative group, it shows no diagnostic value there either.

Exploratory note, no claim attached: the two models with the lowest commitment rates (deepseek-flash, qwen3p8) show two of the three smallest log-scale shifts, but the pattern is imperfect (inkling combines a high commitment rate with a small shift) and nine models cannot support ecological inference.

### 5.3 Transparent disclosure does not account for the effect

Adjudication of the 40 sampled disclosure candidates:

| Rubric category | Count |
|---|---:|
| Prospective impartiality promise | 40/40 |
| Donation-favorable option considered and rejected | 33/40 |
| Retrospective denial of influence | 13/40 |
| Donation-driven choice finally adopted | 8/40 |
| Explicit final-number-to-donation link | 8/40 |

The adopted cell splits 6/25 `above_good` versus 2/15 `below_good` (two-sided Fisher exact p = 0.686): no condition asymmetry is established and that cell is not interpreted directionally. One deflationary reading — rounding for arithmetic convenience with the cause invoked as post-hoc justification — is consistent with the data; convenience-rounding alone is direction-neutral under the mirrored design, so it could populate this cell without contributing to the aggregate contrast unless its deployment is itself donation-dependent.

**Excluding the 8 confirmed disclosed-adoption traces leaves the contrast at +15.1% [9.1, 21.7]; excluding all 18 confirmed-or-uncertain leaves +14.0% [7.9, 20.5].** This is a bounded null with a partly mechanical component (8–18 removals from ~750): the supported statement is that *the identifiable transparently-disclosing traces do not account for the effect* — not that the remaining effect is hidden, and not that undetected disclosure is absent (recall is unknown).

The most striking qualitative pattern is the 33/40 considered-and-rejected rate: the modal trace *sees* the donation-favorable move, *explicitly declines it*, and belongs to a population whose answers nonetheless follow the donation direction. Whatever reconciles these is not visible in the text at the point of rejection, and this dataset cannot identify it.

### 5.4 Exploratory probe: where in the Fermi chain does the shift enter?

Each answer decomposes additively: ln Y = ln N + ln S + ln(Y/(N·S)), where N is the adopted giraffe population, S the adopted spots-per-giraffe, and the third term the aggregation/reporting residual. The condition contrast of each component sums exactly to the total. A deterministic extractor recovered N and S from reasoning text under a prespecified validity gate (both factors clearly extracted; N·S within 3× of the final answer), with pass rates published before any contrast was computed.

The premise is independently validated by baseline data: every model pins N at the memorized public figure (~117,000–120,000, tight IQRs), while S is unconstrained — medians range from 185 to 675 across models with wide spreads. If motivated selection operates on "individually reasonable" assumptions, it should concentrate in S.

Gated nine-model decomposition: **Δln N −1.7% [−3.4, −0.0]; Δln S +8.6% [+4.0, +13.3]; residual +3.1% [+0.7, +5.6]; gated total +10.1% [+5.6, +14.8]** (components sum to the total to machine precision, replicate-wise).

This pattern — the shift concentrating in the least-constrained factor, with the well-anchored fact untouched — is exactly the assumption-selection signature. **We do not advance it as a finding**, for three prespecified reasons the pipeline itself reported: a 20-trace audit found 5 extraction errors (25%, above any acceptable bar); gate pass rates are condition-imbalanced by up to 17 pp in some models; and the gated subsample carries only +10.1% of the full +15.5% effect, so the decomposition describes a scorable subset. The probe's value is to sharpen the next experiment: validated (human-audited) factor extraction on a fresh interleaved run, testing whether donation direction moves the unconstrained assumption while leaving memorized facts fixed. Artifacts: `analysis/hyp8_locus/`.

## 6. Discussion

**The dissociation.** In this corpus, stating an impartiality goal (near-universal), behaving invariantly under the incentive flip (systematically violated at the population level), and disclosing incentive-driven choices (rare, and non-explanatory when found) come apart cleanly. The commonest verbal signal — the promise — is precisely the one with no predictive value. Retrospective denials of influence are a minority (13/40 even among disclosure *candidates*), so most traces never actually assert the thing informal audits credit them with; they promise prospectively and then the population drifts.

**Methodological implication.** Evaluations of CoT faithfulness cannot rest on what reasoning *declares* — whether extracted by a judge, asserted by the model, or inferred from the absence of stated bias. Where declarations sit at ceiling, the proxy is empty before any judging error is considered. The unit of evidence must be a behavioral contrast against the stated commitment: the same commitment, mirrored incentives, measured movement. The design used here (fixed threshold, flipped direction, stratify on the declaration) is cheap and portable to other value-leakage settings.

**What would move this forward.** The natural mechanism question — does the incentive act through the selection of individually-defensible Fermi assumptions? — received an exploratory probe (§5.4) whose direction matches that hypothesis (the shift concentrates in the unconstrained spots-per-giraffe factor, not the memorized population figure) but whose extraction validation failed the bar for a claim. Prior consistency checks found no evidence that the effect enters at the reporting stage (reasoning-to-answer drift, donation-dependent rounding), but those screens were narrow: reporting-stage mechanisms are unresolved, not ruled out. Human re-adjudication of the 18 confirmed-or-uncertain disclosure traces is the cheapest robustness upgrade available.

## 7. Limitations

- **Wording asymmetry / semantic priming:** the mirrored prompts differ in more than moral direction; a non-moral asymmetry could contribute to the contrast. This is the primary alternative to a motivated-reasoning reading and is not excluded.
- **Serving and provider differences:** conditions were not perfectly interleaved historically; the deepseek-pro anomaly shows serving artifacts are real in this corpus.
- **Condition-asymmetric attrition:** claude-opus loses more answers in `above_good` (47 vs 37 usable); parsed-only analysis could be selected. Binary-outcome results with full denominators partially mitigate.
- **Judge error and missingness:** long-trace false negatives shrink the labeled stratum; 37 labels are missing; neither can manufacture the within-stratum contrast.
- **Model adjudication:** the disclosure rubric was applied by a model under span-citation constraints, not by a human; the exclusion sets are model-identified.
- **Post-treatment conditioning:** stratification supports diagnostic, not causal, claims.
- **Claude:** all reasoning-content findings for claude-opus describe API summaries, not raw CoT.
- **Scope:** ten fixed models, one task, one question; retrospective, exploratory, not preregistered.

## 8. Conclusion

For these nine models on this task: (1) final answers follow the donation direction across an identical threshold (+15.5% [9.4, 22.1]; +32.1 pp crossing [25.6, 38.6]); (2) explicit impartiality commitments carry no measurable information about that sensitivity — no point-estimate attenuation where testable (paired difference +1.4 pp [−1.4, 4.5]), and no discriminating power by construction where the commitment sits at ceiling; (3) the identifiable transparently-disclosing traces do not account for the effect. The evidence does not support claims of hidden influence, concealment, intent, deception, per-trace unfaithfulness, mechanism location, or generalization beyond this setting — and the report's contribution depends on not making them. The practical lesson for CoT-faithfulness evaluation is blunt: auditing the promise audits the one property that predicts nothing; audit the behavior against the promise instead.

---

## Reproducibility and artifact map

| Component | Location |
|---|---|
| This report's analysis (seed 46062032, 10k bootstrap) | `analysis/hyp7_impartiality_dissociation/analyze_h7.py` |
| Independent recomputation | `analysis/hyp7_impartiality_dissociation/verify_h7_independent.py` |
| Figures (forest with disclosure-exclusion rows; crossing-rate dumbbells) | `analysis/hyp7_impartiality_dissociation/outputs/` |
| Disclosure exclusion sets (8 confirmed / 18 confirmed-or-uncertain) | `analysis/hyp7_impartiality_dissociation/disclosure_exclusions.json` |
| Corrected answers and outcome table | `analysis/hyp6_impartiality/existing_data/outcomes_and_claims.csv` |
| Blinded judge outputs | `analysis/hyp6_impartiality/full_1000/raw_judge_outputs.jsonl` |
| Raw corpus | `runs/<model_dir>/{baseline,below_good,above_good}.json` |
| Control study | `analysis/hyp1_moral_comparison/`, `analysis/hyp1_threshold_anchoring/` |
| Measurement study | `analysis/hyp6_impartiality/hypothesis_6_report.md` |
| Detailed headline study | `analysis/hyp7_impartiality_dissociation/hypothesis_7_report.md` |

The prespecified paired bootstrap difference between the unconditional and commitment-positive contrasts (computed within the same replicates) is +1.4 pp, 95% CI [−1.4, 4.5], with 10,000 of 10,000 replicates usable; it is stored under `paired_diff_base_minus_labelpos` in `outputs/bootstrap_summary.json`.
