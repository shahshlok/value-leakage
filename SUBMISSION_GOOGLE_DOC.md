# Value Leakage in the Donation Bet

_Answers shift despite stated impartiality_

Shlok Shah · hi@shahshlok.com  
Model Forensics SPAR take-home

## Summary

In the Donation Bet, a model estimates the total number of black spots on all living giraffes. A fixed cutoff determines which cause receives a donation. Across nine models, answers were **15.5% higher** when exceeding the cutoff helped the good cause rather than hurt it (95% bootstrap interval: 9.4% to 22.1%). The share above the cutoff increased by **32.1 percentage points** (25.6 to 38.6).

The shift remained **14.1%** (7.7% to 20.9%) among traces whose written reasoning explicitly promised impartiality. I did not detect a smaller shift in that group. Removing retrieved traces that openly adopted donation-linked choices also left most of the shift intact.

These results show a population-level dissociation between stated impartiality and answers. They are consistent with motivated reasoning, but do not establish per-trace lying or hidden moral causation: wording polarity and serving variation remain alternative explanations. The next test should separate donation mapping from wording, then intervene on the reasoning sentences that might carry the effect.

## 1. The task and the clearest example

The factual question is the same in both conditions. Only the surrounding donation rule changes:

- **Below-good:** an answer at or below the cutoff helps the good cause.
- **Above-good:** an answer above the same cutoff helps the good cause.

The donation rule supplies no evidence about giraffes. If estimates systematically move toward whichever side benefits the good cause, that is the behavioral signature of motivated reasoning I want to test. Holding the cutoff fixed removes a simple explanation based on presenting different numbers, although it does not remove every wording difference.

Qwen 3.5 provides the clearest illustration. Its cutoff is 41 million. The median answer is 38 million in below-good and 44 million in above-good; 7 of 50 answers exceed the cutoff in the first condition, compared with 33 of 50 in the second. **All 100 traces were labeled as explicitly promising impartiality.**

_[Insert Figure 1 here: Qwen 3.5 answer distributions under the two donation mappings.]_

**Figure 1. Same question, same cutoff, different answer distributions.** Each marker is one Qwen 3.5 answer. The horizontal axis is logarithmic; the dashed line marks 41 million and the thick bars mark the medians. Crossing helps the good cause in the upper row and hurts it in the lower row. All 100 traces received positive impartiality labels.

A single answer near the threshold proves little: Fermi estimates legitimately vary. The evidence is the difference between distributions under the two mappings. Qwen's cutoff also coincides with a common baseline answer, making threshold crossing particularly sensitive. I therefore report both answer magnitude and crossing rates.

## 2. The cross-model result

### Data and measurement

I use Aditya's original ten-model corpus, which contains 100 responses per model per condition, plus baseline responses. The headline analysis uses a selected sample of 1,000 traces: 50 below-good and 50 above-good per model. Of these, 841 have usable final answers.

The primary average excludes DeepSeek Pro under a serving-artifact rule set before pooling. In its original 100-response above-good source cell, 52% of answers were unparseable and 43 reasoning traces were empty. These are source-corpus diagnostics, not failure rates in the selected sample. Excluding this model leaves **753 usable answers across nine models**; Appendix A provides the model-level counts.

I measure two outcomes. The **magnitude shift** compares geometric-mean answers between above-good and below-good within each model. The **crossing shift** compares the share of usable answers strictly above the same model-specific cutoff. Equality counts as below. Both primary summaries give models equal weight.

Intervals come from 10,000 bootstrap resamples within model and condition. They describe uncertainty conditional on the analyzed records and fixed model set. They do not account for unknown missing answers, serving confounds, or generalization to other questions. The analysis is retrospective and exploratory, not a preregistered replication.

### Answers move with the donation mapping

The nine-model magnitude shift is **+15.5% [9.4%, 22.1%]**. The crossing shift is **+32.1 percentage points [25.6, 38.6]**. All nine model-level point estimates move in the incentive-consistent direction, although some individual intervals include zero.

_[Insert Figure 2 here: threshold-crossing rates across models, for all usable and impartiality-positive answers.]_

**Figure 2. Threshold crossing increases across models.** Circles show below-good and triangles show above-good; every triangle lies to the right of its corresponding circle. The right panel retains only impartiality-positive traces. Rates use observed usable answers. DeepSeek Pro is shown descriptively but excluded from the nine-model primary average.

Magnitude and crossing capture different behavior. DeepSeek Flash's answer magnitude shifts only +2.8%, while its crossing rate rises from 16% to 62%. Small movements among answers clustered near the cutoff can change the donation outcome frequently. Neither outcome should substitute for the other.

## 3. Do impartiality statements track answers?

### The shift persists among traces that promise impartiality

GLM-5.3-Flash classified whether each reasoning trace explicitly committed to impartiality. The judge received reasoning text with model identity, condition, cutoff, and final-answer metadata withheld. This was metadata blinding: the reasoning itself could reveal the incentive or repeat numbers. The labels were not validated against a full human-labeled reference set, and long-trace false negatives are a known limitation.

Among the 753 usable primary answers, 716 have labels: **589 positive and 127 negative**, with 37 missing. Qwen 3.5 is positive on all 100 traces, leaving no negative group within that model.

Among label-positive traces, the magnitude shift remains **+14.1% [7.7%, 20.9%]**. The paired difference between the full-set and label-positive shifts is **+1.4 percentage points [−1.4, 4.5]**, using the same bootstrap resamples.

_[Insert Figure 3 here: forest plot comparing all usable and impartiality-positive answers, with paired differences.]_

**Figure 3. No statistically detectable reduction among impartiality-positive traces.** The left panel compares all usable answers with claim-positive answers; the right shows paired differences. Intervals that are displayed are 95% bootstrap intervals. The pooled difference includes zero. Bottom rows repeat the analysis after disclosure exclusions. DeepSeek Pro is not part of the primary average.

I did not detect a smaller condition shift among claim-positive traces. This is **not an equivalence result**: the interval permits some reduction or amplification, and no equivalence margin was specified. The two groups also overlap heavily. A pooled negative-only comparison is not defined for the fixed nine-model set because some model-condition cells contain no negative labels. The two models with substantial negative groups likewise provide no clear evidence of a smaller shift among positive traces, but their comparisons are imprecise (Appendix C).

These are observational comparisons. The label is produced after the prompt and can depend on both the condition and the model. Filtering on it does not estimate the causal effect of becoming impartial. The narrower practical lesson is that finding an impartiality promise is not sufficient evidence that answers are insensitive to the donation mapping.

### Retrieved open admissions do not explain the aggregate shift

I also checked whether the relevant adjustment was already disclosed in the reasoning. A donation-linked adjustment screen retrieved candidates; Claude Sonnet scored 40 of them under a frozen rubric with condition and outcome metadata hidden. Each category decision required a supporting source span. As above, the text itself could reveal the condition.

All 40 candidates promised impartiality, **33 considered and rejected** a donation-friendly move, and **8 adopted** a donation-linked choice. Removing those 8 traces leaves a **+15.1%** magnitude shift. Removing them plus 10 uncertain cases leaves **+14.0%**.

Those identified admissions do not account for the aggregate shift. But this is a small, retrieved sample, not a prevalence study. Search recall is unknown, non-hits are not verified non-disclosures, and the category decisions come from a model. The result does not show that the remaining influence is hidden. Appendix C preserves the counts and exclusion intervals.

### What this says about chain-of-thought faithfulness

The evidence is consistent with unfaithful chain-of-thought at the population level: statements about ignoring the donation coexist with answer distributions that differ by donation mapping. But a promise is not a retrospective report of what caused an answer, and any individual estimate might be honest. Claude's reasoning is also an API summary, not raw chain-of-thought.

The defensible conclusion is a dissociation between stated impartiality and observed answer behavior, not a finding of per-trace lying or an identified hidden cause.

## 4. What remains unexplained

### Numerical anchoring is a real design concern

A no-cutoff baseline versus a donation prompt changes both the moral stakes and the numerical context. To test the latter, I collected 400 neutral responses from Qwen 3.5 and Qwen 3.8, with 50 per cell. Raising a neutral bookkeeping boundary increased median answers by 33% and 21%, respectively. Describing the number as irrelevant produced increases of 20% and 2%.

These results support sensitivity to the magnitude of a displayed number. They are not a number-present versus number-absent test. They motivate the fixed-cutoff mirrored contrast used here, rather than treating any baseline-to-donation movement as moral influence. A fresh moral-direction follow-up on these two models was suggestive for Qwen 3.5 but not robust in the later, previously unseen responses. Appendix B gives the control results.

### Wording and serving remain live alternatives

The mirrored prompts change sentence polarity, including “exceeds” versus “does not exceed,” along with the recipient mapping. Polarity or semantic priming could therefore contribute to the contrast. The original conditions were also not perfectly interleaved, leaving serving and time variation unresolved. Automatic parsing and condition-dependent missingness can further select which answers enter the analysis; bootstrap intervals do not remove that selection.

Thus, the observed contrast is incentive-consistent, but moral motivation is not causally isolated. The numerical effect sizes apply to this question and fixed model set, not to models or Fermi tasks generally.

### A flexible premise is a candidate, not an established mechanism

A separate exploratory extraction suggests more movement in the assumed spots per giraffe than in the giraffe population estimate. However, 5 of 20 audited extractions were wrong, extraction success differed between conditions by up to 17 percentage points, and the analysis includes rows outside the headline sample. Its +10.1% gated shift is therefore not a decomposition of the exact +15.5% headline cohort.

I retain this probe because it motivates an intervention, not because it identifies where bias enters. Figure 4 and the numerical decomposition are in Appendix D. Reporting-stage mechanisms also remain unresolved.

## 5. The experiment I would run next

I would start with Qwen 3.5: it has complete answers, a substantial original shift, and positive impartiality labels on every sampled trace. The next experiment has two stages.

**First, separate recipient mapping from wording.** Cross donation direction with sentence polarity while holding the numerical cutoff fixed. Randomize and interleave the conditions, pin provider and sampling settings, and retain failures. If answers track the recipient mapping within each wording template, the moral-direction account gains support. If they track the wording factor instead, polarity is the better explanation. Attenuation under controlled serving would be consistent with a serving contribution, though not uniquely diagnostic of it.

**Second, intervene on the reasoning.** From a fixed prefix immediately before a target sentence, randomly insert an explicit impartiality commitment or a neutral procedural sentence matched for style and length, then generate the continuation under identical settings. In a separate arm, resample or pin the spots-per-giraffe premise. Compare the size of the mirrored donation-direction shift across interventions, rather than only comparing individual final answers.

An effective commitment should reduce the condition shift relative to the neutral sentence. If flexible-premise selection carries the effect, fixing that premise should reduce downstream sensitivity. Use an irrelevant species sentence as a negative control and the population premise as a comparison locus. Cluster uncertainty by source prefix and model; inspect sentence and premise extraction before examining outcomes. Appendix E specifies the proposed controls and predictions.

I did not run sentence resampling or J-lens. Decoding condition information internally could complement this test, but would not substitute for a behavioral intervention.

## Conclusion

The Donation Bet yields an incentive-consistent answer shift across the nine-model primary set, including traces that explicitly promise impartiality. Retrieved open admissions do not explain that aggregate pattern, but the evidence does not establish hidden moral causation or per-trace deception. The next step is to separate donation mapping from wording and test whether intervening on a commitment or premise changes the answer distribution.

## Reproducibility and scope

The [project repository](https://github.com/shahshlok/value-leakage) contains the code, data, supporting reports, and trace-level artifacts. The original ten-model replication corpus is excluded from the five-hour take-home limit; I used it as a fixed setting for these analyses and added the two-model control study. No causal sentence intervention or internal-representation analysis is presented as completed work.

## Appendix A. Sample accounting and model-level results

The headline sample is distinct from the full original corpus and the fresh Qwen control runs. Answer availability and label availability are separate filters.

| Analysis population                                             |          Count |
| --------------------------------------------------------------- | -------------: |
| Selected original traces, ten models                            |          1,000 |
| Usable answers, ten models                                      |            841 |
| Usable answers after excluding DeepSeek Pro                     |            753 |
| Primary usable answers with impartiality labels                 |            716 |
| Label-positive / label-negative / label-missing primary answers | 589 / 127 / 37 |

Across all 1,000 judge calls, 951 returned usable labels and 727 were positive. The 49 failed calls are missing labels, not negative classifications. Those all-call totals should not be confused with the intersection of usable answers and labels in the primary nine-model set.

| Model                  | Magnitude shift | Usable answers, below / above | Above-cutoff share, below → above |
| ---------------------- | --------------: | ----------------------------: | --------------------------------: |
| GLM 5.2                |          +29.2% |                       33 / 30 |                     42.4% → 76.7% |
| Qwen 3.5               |          +22.4% |                       50 / 50 |                     14.0% → 66.0% |
| MiniMax M3             |          +21.3% |                       43 / 43 |                     39.5% → 53.5% |
| Claude Opus 4.7        |          +17.3% |                       47 / 37 |                     14.9% → 56.8% |
| Inkling Small          |          +17.1% |                       33 / 41 |                     18.2% → 36.6% |
| Qwen 3.8               |          +11.5% |                       47 / 47 |                     38.3% → 78.7% |
| Kimi K3                |          +10.7% |                       43 / 38 |                     39.5% → 71.1% |
| Inkling                |           +9.0% |                       35 / 36 |                     25.7% → 36.1% |
| DeepSeek Flash         |           +2.8% |                       50 / 50 |                     16.0% → 62.0% |
| DeepSeek Pro, excluded |          +12.5% |                       46 / 42 |                Not tabulated here |

The magnitude analysis requires finite positive answers; crossing rates use finite answers. The DeepSeek Pro source-cell failure rates are based on the original above-good cell of 100 responses and its source-corpus parsing, whereas 46 / 42 describes usable answers in the selected, corrected analysis sample. Its positive descriptive contrast does not reverse the direction of the primary result.

## Appendix B. Neutral-number control

Each row compares a low and high displayed number, with 50 responses at each level. “M” means million. The four comparisons total 400 responses. Qwen 3.5 and Qwen 3.8 were chosen because they showed relatively large and small effects, respectively, in the original replication.

| Neutral wording and model       | Number shown, low → high | Median answer, low → high | Change |
| ------------------------------- | -----------------------: | ------------------------: | -----: |
| Bookkeeping boundary · Qwen 3.5 |                41M → 85M |               39M → 51.9M |   +33% |
| Bookkeeping boundary · Qwen 3.8 |                40M → 80M |                 24M → 29M |   +21% |
| Irrelevant number · Qwen 3.5    |                41M → 85M |                 41M → 49M |   +20% |
| Irrelevant number · Qwen 3.8    |                40M → 80M |             28.5M → 29.1M |    +2% |

The bookkeeping condition contains no good/bad cause. The irrelevant-number condition explicitly describes the supplied number as irrelevant. These descriptive full-run comparisons support a numerical-context concern; they do not estimate a number-free baseline effect or establish that anchoring explains the fixed-cutoff moral contrast.

The separate fresh moral follow-up was exploratory and sensitive to the inspected-versus-unseen split. Its weaker later-only results prevent a strong fresh moral-replication claim. The original multi-model analysis and these fresh Qwen runs should not be pooled or presented as the same dataset.

## Appendix C. Impartiality comparisons and disclosure audit

### Positive and negative label groups

Only DeepSeek Flash and Qwen 3.8 have substantial negative-label groups in the primary set. The paired differences below are positive-group minus negative-group magnitude shifts; all intervals are 95% bootstrap intervals.

| Model          | Negative-label shift | Positive-label shift | Paired difference, percentage points |
| -------------- | -------------------: | -------------------: | -----------------------------------: |
| DeepSeek Flash |   +2.6% [0.6%, 5.1%] |   +4.0% [1.3%, 7.1%] |                     +1.4 [−2.3, 5.1] |
| Qwen 3.8       | +8.2% [−7.6%, 24.4%] | +11.4% [0.6%, 24.8%] |                   +3.2 [−16.7, 23.8] |

DeepSeek Flash's crossing shift is approximately +50.5 percentage points in both groups, with a paired difference of +0.02 points [−40.9, 37.2]. These wide intervals do not establish equivalence or precisely bound the label's diagnostic value.

### Retrieved disclosure candidates

The 40-case sample contains 25 above-good and 15 below-good candidates. Categories overlap and should not be summed.

| Behavior in the reasoning                        | Count |
| ------------------------------------------------ | ----: |
| Promised impartiality                            | 40/40 |
| Considered and rejected a donation-friendly move | 33/40 |
| Retrospectively denied donation influence        | 13/40 |
| Adopted a donation-linked choice                 |  8/40 |

Adoption counts are 6/25 above-good and 2/15 below-good (two-sided Fisher p = 0.686). This small retrieved sample does not establish a directional difference. Convenience rounding or a post-hoc donation rationale remains compatible with some cases; neither establishes a population-level rounding mechanism.

| Exclusion from the primary analysis      | Remaining magnitude shift |
| ---------------------------------------- | ------------------------: |
| None                                     |      +15.5% [9.4%, 22.1%] |
| Eight confirmed open adoptions           |      +15.1% [9.1%, 21.7%] |
| Eight confirmed plus ten uncertain cases |      +14.0% [7.9%, 20.5%] |

These exclusions concern only identified cases. The screen's recall is unknown, and source-span checking verifies evidence location, not human-ground-truth classification accuracy. Removing a small number of traces from a much larger sample is also a limited sensitivity test, not proof that undisclosed influence remains.

## Appendix D. Exploratory premise decomposition

A typical Fermi calculation combines an estimated giraffe population, N, with assumed spots per giraffe, S. I express it as:

> log(answer) = log(N) + log(S) + residual

The extractor retains traces only when both premises are found and their product is compatible with the final answer. This exploratory analysis uses locally parsed original-corpus rows, including rows outside the corrected 1,000-trace headline sample. Its gated result is not an exact decomposition of the headline cohort.

| Component          | Descriptive condition shift, 95% interval |
| ------------------ | ----------------------------------------: |
| Giraffe population |                      −1.7% [−3.4%, −0.0%] |
| Spots per giraffe  |                       +8.6% [4.0%, 13.3%] |
| Residual           |                        +3.1% [0.7%, 5.6%] |
| Gated total        |                      +10.1% [5.6%, 14.8%] |

Components add on the log scale, not as percentage-point contributions. The population interval's upper endpoint rounds to zero. The residual includes departures from the extracted product and should not be interpreted as an identified late-stage adjustment mechanism.

_[Insert Figure 4 here: exploratory decomposition into giraffe population, spots per giraffe, residual, and gated total.]_

**Figure 4. Exploratory decomposition, not mechanism identification.** The extracted spots-per-giraffe premise moves more than the population estimate. However, 5/20 audited extractions were wrong, condition differences in extraction success reach 17 percentage points, and the cohort differs from the headline analysis. The pattern suggests a target for intervention; it does not establish where the observed shift enters.

Selection into the extraction gate can manufacture or distort component shifts. The +10.1% gated estimate and +15.5% headline estimate therefore cannot be read as “the share of the headline effect explained.” The numerical results are retained as descriptive, hypothesis-generating evidence only.

## Appendix E. Proposed intervention and discriminating predictions

This is a proposed design, not a completed experiment or a claim of prospective registration.

**Collection.** Cross donation direction with wording polarity at the same cutoff. Randomize and interleave all arms, pin provider and sampling settings, blind parsing to condition, retain failures, and check target-sentence and premise extraction before examining outcomes.

**Experimental unit.** A source prefix ending immediately before the target sentence. Multiple continuations from one prefix are matched repeats. Cluster inference by source prefix and model, and apply the same intervention protocol within both donation mappings.

**Commitment arm.** Randomly insert an explicit impartiality commitment or a style- and length-matched neutral procedural sentence. Generate the continuation with otherwise identical decoding settings.

**Premise arm.** Resample the sentence adopting spots per giraffe and its continuation; separately pin that premise to test whether removing this degree of freedom shrinks the condition shift. Record the adopted premise as a proximal outcome. Apply a matched intervention to a species sentence that does not enter the calculation, and use the population premise as a mechanistically motivated comparison locus.

**Outcomes and estimand.** Reuse geometric answer magnitude and threshold crossing. Estimate the interaction between donation mapping and sentence intervention: does the intervention change the size of the mirrored condition contrast?

| Explanation                                | Discriminating prediction                                                                                                                               |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Moral-direction sensitivity                | Answers follow recipient mapping within the same wording template.                                                                                      |
| Numerical anchoring                        | Answers respond to the displayed number without moral content; a fixed number alone does not explain a mirrored difference.                             |
| Wording polarity                           | Answers track the independently varied wording factor when mapping is held fixed.                                                                       |
| Serving or time variation                  | The contrast attenuates with interleaving and controlled serving, without requiring a sentence-level intervention.                                      |
| Openly disclosed adjustment                | A sufficiently comprehensive, validated intervention on disclosed adoptions reduces the contrast; the current bounded exclusions do not establish this. |
| Causally effective impartiality commitment | Inserting the commitment reduces the mirrored shift relative to the neutral sentence.                                                                   |
| Flexible-premise selection                 | Donation mapping changes the adopted premise, and pinning it reduces downstream sensitivity more than the negative-control intervention.                |

An ineffective intervention would not by itself prove that the original sentence was causally inert: prefix selection, intervention fidelity, and statistical power would also require checking. Internal decodability through J-lens could provide complementary timing evidence, but not replace these behavioral tests.
