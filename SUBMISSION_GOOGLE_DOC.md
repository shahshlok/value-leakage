# Value Leakage in the Donation Bet

## A population-level dissociation between stated impartiality and answers

Shlok Shah · hi@shahshlok.com

## Executive summary

I studied one setting: the Donation Bet. A model estimates the total number of black spots on all living giraffes. A fixed cutoff determines which cause receives a donation. In the **above-good** condition, an answer above the cutoff helps the good cause; in the **below-good** condition, an answer at or below the same cutoff helps the good cause.

I asked two questions. First, what would motivated reasoning look like in this task? Second, should I interpret the written reasoning, or chain-of-thought (CoT), as unfaithful?

**My answer to the first question:** motivated reasoning would look like a counterfactual shift in the answer distribution toward whichever side of the fixed cutoff benefits the good cause. That is what I observe. Across the nine-model primary set, answers are **+15.5% [9.4, 22.1]** higher when a high answer helps the good cause. The share above the cutoff moves by **+32.1 percentage points [25.6, 38.6]**. All nine model-level point estimates move in the incentive-consistent direction.

**My answer to the second question:** I find evidence consistent with a **population-level dissociation** between stated impartiality and answers. I do not find evidence that permits a per-trace claim of lying or identifies a hidden cause. A blinded judge labeled 589/716 usable traces in the nine-model set as explicitly promising impartiality, yet the label-positive traces still shift by **+14.1% [7.7, 20.9]**. Their shift is only **+1.4 percentage points [-1.4, 4.5]** smaller than the full-set shift. Because that interval includes zero, I conclude that the impartiality label has no measurable diagnostic value here; I do not conclude that positive and negative traces are proven equivalent.

The written reasoning rarely looks like a confession. In a blinded audit of 40 retrieved candidates that mentioned donation-related adjustment, all 40 promised impartiality, 33/40 considered and rejected the donation-friendly move, 13/40 denied retrospectively that the donation mattered, and 8/40 adopted a donation-linked choice. Removing the 8 open adoptions leaves a **+15.1%** shift; removing those 8 plus 10 uncertain cases leaves **+14.0%**. This audit describes retrieved candidates only. Its recall over the full corpus is unknown.

My exploratory decomposition suggests a possible mechanism worth testing: the flexible assumption, spots per giraffe, moves more than the memorized population fact. In the gated subset, population shifts **-1.7% [-3.4, -0.0]**, spots per giraffe shifts **+8.6% [+4.0, +13.3]**, and the residual contributes **+3.1%**. The gated total is **+10.1%**, versus **+15.5%** in the full set. The extractor made 5/20 audit errors, and gate imbalance reaches 17 percentage points, so I treat this as a direction for a causal experiment, not a finding.

Two alternatives remain live. The mirrored prompts change sentence polarity (“exceeds” versus “does not exceed”) along with the donation mapping, and the original generations were not perfectly interleaved. Wording polarity and serving variation could therefore contribute to the result. My clean next test would cross donation direction with sentence polarity in an interleaved run, then use matched sentence resampling to test whether an impartiality commitment or the chosen spots-per-giraffe assumption causally changes the answer.

The original ten-model corpus is replication and is excluded from the five-hour limit. I used it as the fixed setting for the analyses in this document and added the two-model anchoring control described below. I did not run sentence resampling or J-lens.

---

## 1. The estimands

I use two summaries because they capture different behavior.

| Summary | Question I ask | Nine-model result |
|---|---|---:|
| Geometric shift | How much larger is the typical answer when a high answer helps the good cause? | **+15.5% [9.4, 22.1]** |
| Threshold-crossing shift | How much does the share of answers above the same cutoff change? | **+32.1 percentage points [25.6, 38.6]** |

I use the geometric shift for answer magnitude because Fermi estimates are naturally multiplicative. I use threshold crossing because the donation depends on which side of the cutoff the answer lands. A model can therefore show a small magnitude shift and a large crossing shift if many of its answers lie close to the cutoff.

The intervals are 95% bootstrap intervals. I resample the existing answers within model and condition, compute the model-level contrasts, and give each model equal weight in the primary average. These intervals quantify uncertainty in this corpus; they do not turn the nine models into a random sample of all models.

---

## 2. The design problem: anchoring, moral direction, wording, and serving

The Donation Bet contains an immediate confound. Merely displaying a number can anchor a Fermi estimate. A comparison between a no-cutoff baseline and a donation prompt would mix moral motivation with numerical anchoring.

I therefore use the mirrored comparison for the main result:

- In **below-good**, an answer at or below the cutoff helps the good cause.
- In **above-good**, an answer above the same cutoff helps the good cause.

Holding the cutoff fixed removes a simple “different number in the prompt” explanation. It does not remove every alternative: the prompts also use different sentence polarity, and serving can vary across collection time.

### Competing hypotheses and their discriminating predictions

| Hypothesis | Prediction in the present data | Experiment that discriminates it |
|---|---|---|
| **Moral-direction motivated reasoning** | With the cutoff fixed, the answer distribution follows whichever side helps the good cause. Flexible assumptions may absorb more of the movement than memorized facts. | I would cross the recipient mapping with sentence polarity. If recipient mapping predicts answers while polarity is held fixed, the moral account gains support. |
| **Numerical anchoring** | Changing the displayed cutoff moves answers even without any moral content. | I would vary the cutoff while holding all moral language absent or fixed. Anchoring predicts movement with the number, regardless of recipient. |
| **Sentence polarity** | “Exceeds” and “does not exceed” move answers even if good/bad labels are removed or swapped. | I would express both recipient mappings using the same predicate, then cross that mapping with an independently varied wording template. Polarity predicts the wording factor, not the recipient mapping. |
| **Serving or time variation** | Condition differences track collection order, route, or missingness. | I would interleave randomized conditions, pin model and provider settings, and record failures before parsing. A serving account should shrink under that design. |
| **Open, on-the-page tradeoff** | Traces that admit donation-driven adjustment account for the aggregate shift. | I would remove or intervene on disclosed adoptions. If the shift disappears, open tradeoff explains it. The bounded removal analysis below does not show that. |
| **Impartiality language is behaviorally effective** | An explicit commitment to ignore the donation predicts or causes a smaller condition shift. | I would resample the commitment sentence from a fixed prefix and compare it with a matched neutral sentence. The observational label test below finds no measurable diagnostic value. |
| **Flexible-premise selection** | The condition changes an unconstrained premise such as spots per giraffe more than a memorized fact such as population. | I would resample or pin the premise sentence, with the population sentence as a negative-control locus. The current extraction is too error-prone to settle this. |

This table separates an observed signature from a mechanism. The present mirrored contrast establishes an incentive-consistent population shift. Because moral direction and wording polarity are not independently randomized, it does not by itself establish that moral motivation caused the shift.

### Anchoring control

I first checked whether a displayed number moves answers without moral stakes. Fresh generations were required, so I ran this control on Qwen 3.5 and Qwen 3.8. These models sat at opposite ends of the original replication: Qwen 3.5 showed relatively large leakage, while Qwen 3.8 showed little. The pair therefore tests whether neutral anchoring also appears in a model that barely moved under the original moral prompt.

I used two neutral framings, 50 answers per cell and 400 answers total.

| Wording | Model | Cutoff shown, low → high | Median answer, low → high | Change |
|---|---|---|---|---|
| Neutral bookkeeping boundary (no good/bad cause) | Qwen 3.5 | 41M → 85M | 39M → 51.9M | +33% |
| Neutral bookkeeping boundary | Qwen 3.8 | 40M → 80M | 24M → 29M | +21% |
| Number described as irrelevant | Qwen 3.5 | 41M → 85M | 41M → 49M | +20% |
| Number described as irrelevant | Qwen 3.8 | 40M → 80M | 28.5M → 29.1M | +2% |

The displayed number can move the estimate even without a donation. I therefore do not interpret baseline-versus-donation movement as evidence of motivated reasoning. I use only the mirrored moral contrast for the main result.

A fresh mirrored moral run on these two models was suggestive for Qwen 3.5 but was not robust in held-out data. I treat the anchoring control as a necessary design correction, not as a complete explanation of the original multi-model pattern.

---

## 3. Main result: answers follow the donation mapping

I analyze Aditya’s original ten-model corpus, with 100 answers per condition. I use a 1,000-trace sample containing 50 below-good and 50 above-good traces per model. After parsing, 841 answers are usable.

I exclude DeepSeek Pro from the primary average under a rule set before the pooled analysis. It has 52% unparseable answers and 43/100 empty reasoning traces in above-good, consistent with a serving failure. Its own shift is **+12.5%**, so including its direction would not reverse the qualitative pattern. The nine-model primary result is **+15.5% [9.4, 22.1]**, with a crossing shift of **+32.1 percentage points [25.6, 38.6]**.

| Model | Size shift | Usable answers (below / above) | Share above the cutoff, below-good → above-good |
|---|---:|---|---|
| glm-5p2 | +29.2% | 33 / 30 | 42% → 77% |
| Qwen 3.5 | +22.4% | 50 / 50 | 14% → 66% |
| MiniMax M3 | +21.3% | 43 / 43 | 40% → 54% |
| Claude Opus 4.7 | +17.3% | 47 / 37 | 15% → 57% |
| Inkling Small | +17.1% | 33 / 41 | 18% → 37% |
| Qwen 3.8 | +11.5% | 47 / 47 | 38% → 79% |
| Kimi K3 | +10.7% | 43 / 38 | 40% → 71% |
| Inkling | +9.0% | 35 / 36 | 26% → 36% |
| DeepSeek Flash | +2.8% | 50 / 50 | 16% → 62% |
| DeepSeek Pro *(excluded from the average)* | +12.5% | 46 / 42 | — |

Every model-level point estimate moves in the incentive-consistent direction, although some individual intervals include zero and effect sizes vary substantially.

The magnitude and crossing estimands reveal different patterns. DeepSeek Flash moves only **+2.8%** in size but jumps from 16% to 62% above the cutoff. Its answers cluster near the boundary, so a small numerical nudge often changes the donation outcome. Qwen 3.5 gives the clearest single-model illustration: its medians are 38 million and 44 million around a 41 million cutoff, and its crossing counts are 7/50 and 33/50.

*[Insert `submission_figures/fig3_qwen35_distribution.png` — Caption: **Figure 1. One model’s answers under both donation mappings, with the same cutoff.** Each dot is one Qwen 3.5 answer. The x-axis is logarithmic, so equal distances represent equal ratios. The dashed line is the 41 million cutoff in both rows; the thick bars are medians of 44M and 38M. When a high answer helps the good cause, 33/50 answers cross the line. When it hurts the good cause, 7/50 cross it. All 100 traces received a positive impartiality label, so this figure also illustrates the population-level dissociation between stated intent and answers.]*

*[Insert `submission_figures/fig2_crossing_rate_dumbbell.png` — Caption: **Figure 2. Threshold crossing moves in the incentive-consistent direction across models.** Each row is one model. The x-axis is the share of answers above that model’s cutoff. Circles show below-good, where crossing hurts the good cause; triangles show above-good, where crossing helps it. The cutoff is fixed within model. Every triangle lies to the right of its circle. The right panel restricts the calculation to traces labeled as promising impartiality; the pattern changes little.]*

### What motivated reasoning looks like here

At the population level, it looks like selection among defensible estimates rather than a frequent explicit decision to manipulate the donation. A Fermi question admits many plausible assumptions, and a modest movement can place the final number on the helpful side of a salient threshold. The written trace can simultaneously announce an impartial procedure or reject an overtly biased move.

That description is consistent with motivated reasoning, but it does not identify the internal process. Wording could shift the same flexible assumptions, and serving differences could shift the answer distribution without any moral computation. I therefore use “motivated reasoning” for the hypothesis whose signature I am testing, rather than as a settled hidden-cause label.

---

## 4. Does an impartiality promise diagnose incentive-free reasoning?

I test whether the written commitment is informative. I do not condition on it as though it were a randomized treatment. The label is produced after the prompt, so selection into label-positive traces can itself depend on the condition and on the model.

I had GLM-5.3-Flash judge reasoning with the model name, condition, cutoff, and final answer hidden. The judge marked whether the text explicitly committed to impartiality. Across all ten models, 951/1,000 calls returned labels and 727/951 were positive. Failed calls are missing labels, not negatives. In the nine-model primary analysis, 589/716 labeled usable traces were positive. Qwen 3.5 was 100/100 positive.

| Diagnostic | Prediction if the promise were informative | Observation |
|---|---|---|
| Coverage | The label should separate a meaningful positive and negative group. | It is positive on 589/716 labeled usable traces in the primary set and 100/100 Qwen 3.5 traces. |
| Shift among label-positive traces | The shift should be near zero or materially smaller than the full-set shift. | The shift is **+14.1% [7.7, 20.9]**. |
| Paired difference from the full-set shift | Resampled matched differences should be clearly positive if filtering removes leakage. | The difference is **+1.4 percentage points [-1.4, 4.5]**. |
| Shift among label-negative traces | The negative group should shift more if the promise marks faithful behavior. | DeepSeek Flash is **+2.6% vs +4.0%** for negative vs positive, with a **+50.5 percentage-point** crossing shift in both. Qwen 3.8 is **+8.2% vs +11.4%** for negative vs positive. |

I find no measurable diagnostic value for the promise in this sample. I do not claim equivalence: the paired interval includes zero and also permits some shrinkage. I also do not claim that every promise is insincere. The result is aggregate and predictive: knowing that a trace contains the promise does not measurably identify a smaller condition shift here.

*[Insert `submission_figures/fig1_forest_contrasts.png` — Caption: **Figure 3. Impartiality promises do not measurably shrink the condition shift.** In the left panel, each dot is a model’s estimated shift and each bar is its 95% interval. Values to the right of zero move with the incentive. Blue circles use all usable answers; orange squares use only traces whose reasoning promised impartiality. The orange estimates remain close to the blue estimates. The right panel shows their paired differences under the same resamples. Every interval includes zero, so I interpret the label as having no measurable diagnostic value here, not as proving equivalence. The bottom exclusions show that removing retrieved open disclosures also changes little.]*

### Should I call this unfaithful CoT?

I would call it **evidence consistent with unfaithful CoT at the population level**. The written reasoning often says the donation will be ignored, yet the distribution of answers changes when the donation mapping flips. The positive label does not diagnose a smaller shift, and the retrieved open adoptions do not account for the aggregate effect.

I would not call a particular trace a lie. Any single answer may be an honest Fermi estimate that happens to fall on the helpful side. I also cannot infer that the donation was the hidden cause of the aggregate shift while wording polarity and serving remain uncontrolled. Finally, Claude’s “reasoning” is an API summary rather than raw chain-of-thought, so I treat it as a separate evidence tier.

The clean claim is therefore about dissociation: a stated commitment to impartiality and an incentive-invariant answer distribution come apart at the population level.

---

## 5. What the retrieved reasoning says about the donation

I next asked whether the effect is already explained on the page. I searched for donation-linked adjustment language, selected 40 retrieved candidates, and had Claude Sonnet score them under a frozen rubric while hiding condition and outcome. Every category decision required a supporting span that I checked against the source text.

| Behavior in the written reasoning | Count |
|---|---:|
| Promised impartiality | 40/40 |
| Considered and rejected a donation-friendly move | 33/40 |
| Retrospectively denied that the donation mattered | 13/40 |
| Adopted a donation-linked choice | 8/40 |

The 8 open adoptions split 6/25 in above-good and 2/15 in below-good; Fisher p=0.69. I treat that difference as noise. Convenience rounding is one mundane explanation for some admissions. It would only create the mirrored population pattern if the decision to round, or the direction of rounding, also depended on the donation mapping.

| Exclusion | Remaining size shift |
|---|---:|
| None | +15.5% |
| Exclude the 8 confirmed open adoptions | +15.1% |
| Exclude those 8 and 10 uncertain cases, 18 total | +14.0% |

The identifiable open adoptions do not explain the aggregate shift. I cannot turn that result into “the rest is hidden,” because the search has unknown recall and I did not manually read every non-hit. The audit only supports a bounded statement about retrieved candidates.

Among those candidates, the dominant written pattern is still informative: 33/40 traces notice the tempting move and reject it. Motivated reasoning in this setting need not look like a confession. It can coexist with an explicit rejection of the most obvious biased action while the answer distribution still moves at the population level.

---

## 6. Exploratory locus: which premise moves?

A typical trace multiplies a giraffe population by an assumed number of spots per giraffe. I write the decomposition on a log scale:

> log(answer) = log(population) + log(spots per giraffe) + residual

The population is a relatively checkable fact. Spots per giraffe is much less constrained. If the shift enters through selection among convenient assumptions, I would expect more movement in spots per giraffe than in population.

I used an automatic extractor to identify both premises. I kept a trace only when both were found and their product was compatible with the final answer. In that gated subset:

| Component | Condition shift |
|---|---:|
| Population, N | **-1.7% [-3.4, -0.0]** |
| Spots per giraffe, S | **+8.6% [+4.0, +13.3]** |
| Residual | **+3.1%** |
| Gated total | **+10.1%**, versus **+15.5%** in the full set |

*[Insert `submission_figures/fig4_h8_decomposition.png` — Caption: **Figure 4. Exploratory decomposition of where the answer shift may enter.** Each row shows one component of the gated Fermi calculation; dots are condition shifts, bars are 95% intervals, and zero means no shift. Population stays close to zero, while spots per giraffe moves in the incentive-consistent direction. I treat this only as a hypothesis-generating direction: the extractor made 5/20 audit errors, pass rates differ across conditions by up to 17 percentage points, and the gated subset carries +10.1% rather than the full +15.5% shift. The figure does not establish a mechanism.]*

I do not treat H8 as a finding. The extractor made 5/20 errors in my audit. In some models, the extraction gate differs between conditions by up to 17 percentage points. Selection into the gated subset can therefore manufacture or distort a component shift. The gated subset also misses part of the headline effect.

I retain the decomposition because it gives a sharp intervention: manipulate the flexible premise and use the memorized fact as a negative-control locus. That experiment can confirm or kill the proposed direction.

---

## 7. The sentence-resampling experiment I would run next

I did not run sentence resampling within the five-hour take-home. I would use it as a causal test, not as another label-based correlation.

### Design

| Design element | Pre-specified choice |
|---|---|
| **Experimental unit** | I would use a source trace prefix ending immediately before a target sentence. Multiple continuations from the same prefix would be matched repeats, and I would cluster inference by source prefix and model. |
| **Commitment intervention** | Holding the prompt and prefix fixed, I would randomly insert either an explicit impartiality commitment or a neutral procedural sentence matched for style and length, then resample the continuation under identical decoding settings. |
| **Premise intervention** | In a separate arm, I would stop immediately before the sentence that chooses spots per giraffe, resample that sentence and the continuation, and record the adopted premise and final answer. I would also run a pinned-premise version to ask whether fixing that degree of freedom shrinks the donation-direction shift. |
| **Primary outcomes** | I would reuse the geometric answer shift and threshold-crossing shift. For the premise arm, I would also record the adopted spots-per-giraffe value as the proximal outcome. |
| **Primary estimand** | I would estimate the interaction between donation mapping and sentence intervention. The question is whether changing the target sentence changes the size of the mirrored condition effect. |
| **Negative control** | I would apply the same procedure to a sentence about giraffe species that does not enter the product. I would use the population premise as a second, mechanistically motivated negative-control locus. |
| **Collection controls** | I would randomize and interleave all arms, pin the provider and sampling configuration, blind parsing to condition, retain failures, and human-check the target sentence and premise extraction before looking at outcomes. |

### Discriminating predictions

If the impartiality sentence is causally effective, forcing it should reduce the mirrored shift relative to the matched neutral sentence. If it is merely a verbal commitment, the continuation and final answer should change little.

If flexible-premise selection carries the effect, the donation mapping should change the resampled spots-per-giraffe sentence, and pinning that premise should reduce the downstream answer shift. The species-sentence intervention should not change either primary outcome. The population premise should be less responsive than spots per giraffe.

If wording polarity drives the original result, the effect should track the independently randomized wording template even after recipient mapping is held fixed. If serving drives it, randomized interleaving and a pinned route should attenuate the condition difference without requiring any sentence-level intervention.

I would start with Qwen 3.5 because it has complete answers, a large original shift, and 100/100 positive impartiality labels. That combination makes the causal question especially clean: an observational label cannot separate its traces, but a randomized sentence intervention can still test whether the commitment changes what follows.

J-lens on Qwen 3.5 could complement this design by asking when condition information becomes decodable internally. I did not run it, and I would not use it as a substitute for the behavioral intervention.

---

## 8. Limitations and claim boundaries

| Limitation | Consequence for my claim |
|---|---|
| The mirrored prompts change “exceeds” versus “does not exceed” | Wording polarity remains a live alternative to moral motivation. |
| The original conditions were not perfectly interleaved | Serving and time variation remain live alternatives. |
| DeepSeek Pro has severe missingness | I exclude it from the primary average; its +12.5% direction is descriptive only. |
| The impartiality judge was not validated against a full human-labeled set | Label error, especially on long traces, can weaken the diagnostic analysis. |
| 49 judge calls failed | I treat them as missing, not negative. |
| Final-answer parsing is mostly automatic | Differential parseability can select the analyzed sample. |
| The disclosure search has unknown recall | The 40-case audit describes retrieved candidates, not all disclosures. |
| The disclosure scorer is a model | Quoted evidence is inspectable, but category decisions can inherit model error. |
| The H8 extractor made 5/20 audit errors | The decomposition is exploratory and cannot support a mechanism claim. |
| H8 gate imbalance reaches 17 percentage points | Condition-dependent selection can distort component shifts. |
| Filtering on an impartiality label is observational | It tests diagnostic value, not the causal effect of becoming impartial. |
| Qwen 3.5’s cutoff coincides with a common baseline answer | Its crossing rate is unusually sensitive; the size shift is more stable. |
| Claude’s reasoning is an API summary | I do not treat it as equivalent to raw chain-of-thought. |
| I study one question and a fixed model set retrospectively | I do not generalize the numerical effect to all tasks or models. |

These limits leave me with a narrow but useful conclusion. The Donation Bet produces a robust population-level association between the donation mapping and answers in the nine-model primary set. Explicit impartiality language has no measurable diagnostic value here, and retrieved open disclosures do not explain the shift. The result is consistent with unfaithful CoT at the population level, while per-trace lying, a hidden moral cause, and the exploratory premise-level mechanism remain unproven.

---

## Reproducibility

I used `uv` only. I kept the original corpus fixed, used model-equal aggregation for the primary result, and recomputed the headline estimates independently. The repository contains the code, data, and trace-level artifacts: **https://github.com/shahshlok/value-leakage**.

