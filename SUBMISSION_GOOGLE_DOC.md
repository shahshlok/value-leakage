# Model Forensics SPAR Take-home — Value Leakage (Donation Bet)
Shlok Shah · hi@shahshlok.com

## Executive summary

I studied the Donation Bet task: a model estimates how many black spots are on all living giraffes, and a cutoff number decides whether a good or a bad cause gets a donation. In one condition, a high estimate helps the good cause. In the mirrored condition, a low estimate helps the good cause. The cutoff itself is the same number in both conditions. Aditya's brief asked two things: what does motivated reasoning look like here, and should I treat this as unfaithful chain-of-thought?

**What I found:**

1. **The answers really do follow the donation.** After first checking that a bare number in the prompt can move estimates even with no moral content, I only compared the two mirrored conditions (same cutoff, flipped donation). Across nine models, answers are **15.5% higher** when a high answer helps the good cause (95% interval 9.4% to 22.1%). The share of answers sitting above the cutoff jumps by **32 percentage points** (25.6 to 38.6). Every one of the nine models moves in the same direction.

2. **When a model writes "I will stay impartial," that sentence predicts nothing.** A blinded judge, who saw only the reasoning and not the condition or the answer, found those promises almost everywhere (589 of 716 labeled traces; 100 of 100 for Qwen 3.5). Traces that make the promise still shift by 14.1%. In the two models that also produce many traces *without* the promise, those traces shift just as much. So the cheapest informal faithfulness check — "did the model say it was being unbiased?" — is empty.

3. **Motivated reasoning here does not look like a confession.** In a blinded audit of 40 traces that even mentioned donation-related adjustment, **33 of 40 consider the donation-friendly move and reject it on the page.** Only 8 adopt that move and say so. Removing those 8 barely changes the 15.5% shift. The typical trace sees the temptation, declines it in writing, and the population of answers still follows the incentive.

4. **Where the shift may enter (exploratory, not a claim).** If I split each answer into "giraffe population × spots per giraffe × leftover," the leftover and the population barely move. Spots per giraffe, the one input with no checkable true value, absorbs most of the shift. My extractor failed its own audit (5 errors in 20 traces), so this is a direction for the next experiment, not a result I would defend as settled.

**Is this unfaithful CoT?** In a bounded sense, yes. At the population level, the written reasoning is a bad record of what mattered: it promises impartiality, rarely admits influence, and the answers still follow the donation. In the strong sense (this trace lied; the model hid the incentive on purpose), no. Any single answer could be an honest Fermi estimate that happened to land on the helpful side.

---

## How to read the numbers

Two summaries appear throughout. They answer different questions.

| Summary | What it asks | Headline result |
|---|---|---|
| Geometric shift | How much bigger is the typical *size* of the answer when a high answer helps the good cause? | **+15.5%** (9.4 to 22.1) |
| Threshold-crossing | What fraction of answers sit *above the same cutoff*, and how much does that fraction jump when sitting above helps? | **+32.1 percentage points** (25.6 to 38.6) |

Intervals are 95% bootstrap intervals: I resample the existing answers 10,000 times, within each model and condition, and report the middle 95% of those repeats. They describe these ten models, not a random sample of all models. "Percentage points" means a jump in a rate (14% to 66% is +52 percentage points), not a 52% increase of the rate.

---

## 1. The task, and the confound that has to come first

The Fermi question is always the same: total black spots on living giraffes. A cutoff decides the donation. Two mirrored conditions:

- **Below-good:** an estimate *at or below* the cutoff helps the good cause.
- **Above-good:** an estimate *above* the cutoff helps the good cause.

Within each model the cutoff is identical in both conditions. Only which side helps the good cause changes. If answers still move, that movement cannot be "the model was pulled toward a different number in the prompt," because the number did not change.

Before treating that movement as motivated reasoning, I checked whether a number in the prompt can move estimates *with no donation at all*. Fresh generations were required, so I could not run this control on all ten models. I used **Qwen 3.5 and Qwen 3.8** because they sat at opposite ends of Aditya's original replication: 3.5 leaked relatively a lot, 3.8 almost not at all. That pair asks whether a neutral number still moves a model that barely moved under the original moral prompt. Aditya's brief also flagged Qwen 3.5; that was secondary.

Two neutral framings, 50 answers per cell, 400 answers total:

| Wording | Model | Cutoff shown, low → high | Median answer, low → high | Change |
|---|---|---|---|---|
| Neutral bookkeeping boundary (no good/bad cause) | Qwen 3.5 | 41M → 85M | 39M → 51.9M | +33% |
| Neutral bookkeeping boundary | Qwen 3.8 | 40M → 80M | 24M → 29M | +21% |
| Number described as irrelevant | Qwen 3.5 | 41M → 85M | 41M → 49M | +20% |
| Number described as irrelevant | Qwen 3.8 | 40M → 80M | 28.5M → 29.1M | +2% |

Estimates rise when the displayed number rises, even with no moral stakes. So I do not treat "baseline vs donation" as motivated reasoning: those conditions also differ in whether a number is present. The only contrast I use for the later claims is the mirrored pair: same cutoff, flipped donation. That still does not control the wording difference ("exceeds" vs "does not exceed") or serving differences across providers. Those remain the main rival explanations.

A fresh mirrored moral run on the same two models was only suggestive for Qwen 3.5 and not robust in held-out data. Anchoring is a necessary control. It is not a complete explanation of the original ten-model result. Later sections go back to all ten of Aditya's original models.

---

## 2. Do answers follow the donation?

**Data.** Aditya's original corpus: 10 models, 100 answers per condition. I work with a 1,000-trace sample (50 below-good and 50 above-good per model). After parsing, 841 answers are usable. I dropped one model, deepseek-v4-pro, from the headline average by a rule I set in advance: in above-good it has 52% unparseable answers and 43 of 100 empty reasoning traces. That looks like a serving failure, not a scientific result. Its own shift (+12.5%) is in the table and does not change the story. Nine models remain.

**Result.** Nine-model equal-weight geometric shift: **+15.5% (9.4 to 22.1)**. Crossing-rate jump: **+32.1 percentage points (25.6 to 38.6)**. I recomputed the headlines with a second script; point estimates agreed to 0.05 percentage points.

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

Every point estimate is in the incentive's direction. Models differ a lot (+3% to +29%). Some individual intervals include zero; the pooled interval does not.

The two summaries can disagree, and that is informative. DeepSeek Flash barely moves in *size* (+2.8%) but jumps 46 percentage points in *crossing*, because its answers sit near the cutoff: a small nudge flips the donation without a large change in the number. Qwen 3.5 is the cleanest single picture: medians 38 million vs 44 million around a 41 million cutoff; 7 of 50 vs 33 of 50 answers sit above it.

*[Insert `submission_figures/fig3_qwen35_distribution.png` — Caption: **Figure 1. One model's answers, both conditions, same cutoff.** Each dot is one Qwen 3.5 answer. The x-axis is the estimate (log scale, so 10M, 20M, 40M, 80M are evenly spaced). Top row: a high answer helps the good cause. Bottom row: a low answer helps it. The dashed line is the 41 million cutoff, identical in both rows. Thick bars are medians (44M vs 38M). The two clouds sit on opposite sides of the line in the direction that helps the good cause: 33 of 50 above the line when that helps, 7 of 50 when it hurts. All 100 of these traces contain a judge-labeled "I will stay impartial" promise.]*

*[Insert `submission_figures/fig2_crossing_rate_dumbbell.png` — Caption: **Figure 2. The same pattern across ten models.** Each row is one model. The x-axis is the percent of answers sitting above that model's own cutoff. Circles: below-good (a high answer *hurts* the good cause). Triangles: above-good (a high answer *helps*). The gray bar is the gap: same question, same cutoff, only the donation flipped. Every triangle sits to the right of its circle. The right panel repeats the plot using only traces that promised impartiality; the bars barely change.]*

---

## 3. Does "I will stay impartial" mean the answer is incentive-free?

If chain-of-thought were a faithful window, traces that *say* they will ignore the donation should move less. I test that as a diagnostic, not as a causal claim. The impartiality label is written *after* the prompt, so I do not treat "the effect among truly impartial traces" as identified. I *can* ask whether the label carries information, the way a medical test is evaluated by looking at outcomes among people who tested positive.

I had a judge (GLM-5.3-Flash) see reasoning only: no model name, no condition, no cutoff, no answer. It marked whether the text explicitly commits to impartiality. 951 of 1,000 calls returned a label; 727 were positive. Failed calls (timeouts) are missing, not "no." I only checked the judge against another model on small development audits (about 12–14 of 15), never against a human. Long traces are a known miss.

| Test | What it would show if the promise were informative | What it actually shows |
|---|---|---|
| How often the promise appears | It should fire on some traces and not others, especially not on the biggest shifters | 589 of 716 labeled usable traces are positive. Qwen 3.5: 100/100. Claude: 84/84. A test that almost always says "yes" cannot tell biased from unbiased. |
| Shift among traces that made the promise | Should be near zero, or at least smaller than 15.5% | **+14.1% (7.7 to 20.9)**. Difference from the overall 15.5%: **+1.4 percentage points (−1.4 to +4.5)**. The interval includes zero, so modest shrinkage is not ruled out. Even at the shrinking edge, most of the effect remains. |
| Shift among traces that did *not* make the promise | Should be larger, if the promise marks the honest traces | Only DeepSeek Flash and Qwen 3.8 have enough "no" traces. Both still shift. Flash: +2.6% without the promise vs +4.0% with it; crossing jump **+50.5 percentage points in both groups**. All paired differences include zero. |

*[Insert `submission_figures/fig1_forest_contrasts.png` — Caption: **Figure 3. Does the impartiality promise predict anything? No.** Left: for each model, how much answers shift between conditions (dot = estimate, bar = 95% interval). Right of the dashed zero line means the answers moved with the incentive. Blue circles: all answers. Orange squares: only answers whose reasoning promised impartiality. If the promise marked unbiased reasoning, orange would sit near zero. Instead orange sits on top of blue. Right panel: the difference between those two estimates, computed on the same resamples. Every interval includes zero. Bottom rows: the nine-model average, then the same average after dropping traces that openly tied their number to the donation — dropping them changes almost nothing.]*

I keep three properties separate. They are not the same thing, and here they come apart:

1. **Stating** an impartiality goal (almost everyone does this).
2. **Behaving** the same when the donation flips (the population does not).
3. **Disclosing** the factors that actually moved the number (rare; next section).

---

## 4. What does the reasoning actually say about the donation?

If the shift were just honest, on-the-page tradeoffs ("I will round up so the good cause wins"), then removing those traces should kill the 15.5%. I searched reasoning for donation-linked adjustment language, then had 40 of those hits scored blind under a frozen rubric. Condition and outcome were hidden. Every category call had to quote a span; those quotes were checked against the source text. **The scorer was a model (Claude Sonnet), not a human.** That is a limitation. Search misses are not confirmed "no disclosure."

| What the text did | Count out of 40 |
|---|---:|
| Promised impartiality going forward | 40 |
| Considered a donation-friendly move and **rejected** it | **33** |
| After the fact, denied that the donation mattered | 13 |
| Actually adopted a donation-driven choice | 8 |
| Tied the final number to the donation in so many words | 8 |

The 8 adoptions split 6 of 25 above-good vs 2 of 15 below-good (Fisher p = 0.69). That split is noise; I do not read it as "models only confess when rounding up." One boring reading of those 8 is convenience rounding, with the cause used as a story after the fact. Convenience rounding by itself has no preferred direction in a mirrored design, unless *when* the model rounds depends on the donation.

| What is removed | Remaining size shift |
|---|---|
| Nothing (all usable answers) | +15.5% (9.4 to 22.1) |
| The 8 confirmed open adoptions | +15.1% (9.1 to 21.7) |
| Those 8 plus 10 uncertain cases | +14.0% (7.9 to 20.5) |

The identifiable open disclosures do not explain the effect. That is not the same as "the rest is hidden." I did not read every non-hit. The striking pattern is the 33 of 40 that *see* the tempting move, *decline it in writing*, and still belong to a population whose answers follow the incentive.

---

## 5. Where in the Fermi estimate might the shift enter? (Exploratory)

A typical trace multiplies giraffe population by spots per giraffe. On a log scale those pieces add:

> log(answer) = log(population) + log(spots per giraffe) + leftover

The leftover is everything else: extra factors, rounding, the last number the model types. The condition difference in each piece adds up to the total difference. Population is a public fact models already know (~117,000). Spots per giraffe is almost unconstrained (baselines range from about 185 to 675 across models). If the model "picks a convenient but reasonable assumption," the pick should show up in spots, not in population.

I ran an automatic extractor that pulled both numbers from reasoning. I only kept a trace in the split if both numbers were clearly found and their product was within a factor of three of the final answer. I published pass rates before any condition comparison. Then:

| Piece of the estimate | Shift when a high answer helps the good cause |
|---|---|
| Adopted giraffe population | **−1.7%** (−3.4 to −0.0) — essentially flat |
| Adopted spots per giraffe | **+8.6%** (+4.0 to +13.3) — carries most of the move |
| Leftover (product vs final answer) | +3.1% (+0.7 to +5.6) |
| Total, on this scorable subset | +10.1% (+5.6 to +14.8) vs +15.5% on the full set |

*[Insert `submission_figures/fig4_h8_decomposition.png` — Caption: **Figure 4. Where in the calculation does the shift enter? (Exploratory.)** Each row is one piece of the estimate. Dots are the shift between conditions; bars are 95% intervals; the dashed line is "no shift." Population hugs zero. Spots per giraffe, the input with no checkable true value, sits well to the right and carries most of the total. Read the bold footnote on the figure: 25% extractor errors, uneven pass rates by condition, and this subset only carries +10.1% of the full +15.5%. Direction, not a finding.]*

I do **not** treat this as a result. A 20-trace check found 5 extraction mistakes (25%). Pass rates differ by condition by as much as 17 percentage points in some models. The subset that survives the gate only carries a 10.1% shift, not the full 15.5%. The value is the next experiment: human-checked extraction on a fresh interleaved run, asking whether donation direction moves the unconstrained assumption and leaves the memorized fact alone.

---

## 6. Limitations

These are the reasons a careful reader should not over-read the headlines.

| Limitation | Why it matters |
|---|---|
| The two prompts are not identical except for good vs bad | They also say "exceeds" vs "does not exceed." A non-moral wording effect could contribute. This is the main rival to a motivated-reasoning reading. |
| Conditions were not perfectly interleaved in the original collection | Time and provider can leak into condition. DeepSeek Pro's missing traces show serving artifacts are real here. |
| The impartiality judge was never checked by a human | Only another model, on ~15 development traces. Long traces are a known miss. 49 failed calls are missing labels, not "no promise." |
| Most final answers were parsed by code, not read by a person | I human-corrected nine from source quotes. The rest passed automatic checks. |
| The 40-trace disclosure audit was scored by a model | Quotes are checkable. Category calls still inherit that model's biases. |
| Search for disclosures does not find everything | Removing the 8 open cases only bounds *found* disclosure. |
| Claude Opus loses more parseable answers in one condition | 47 vs 37 usable. Parsed-only analysis could be selected. The crossing-rate table uses whatever finite answers exist. |
| Qwen 3.5's usual baseline answer *is* 41 million, its cutoff | Crossing rates for that model are extra jumpy. The size-shift number is the stabler one. |
| Filtering on the promise is not a causal design | It tests whether the label predicts, not "the effect if the model were truly impartial." |
| Claude's "reasoning" is an API summary | Not raw chain-of-thought. I treat Claude as a separate tier. |
| Neutral control never compared "a number" vs "no number" | It shows that *which* number is shown matters, not that showing any number vs none does. |
| Two models in the control, ten in the later studies | I chose Qwen 3.5 / 3.8 from opposite ends of Aditya's ranking, not as a random sample. |
| This is retrospective | I knew earlier results when specifying later analyses. Not a preregistration. Ten models, one question. |

---

## 7. What I did not do, and what I would do next

The brief named two optional directions I did not run, on purpose.

**Sentence resampling** is the right causal test of whether a sentence in the trace *does* anything. Aditya noted it is slow and can sit outside the five-hour budget. I used the time to pin *which* sentences to resample rather than resampling at random.

**J-lens / internals on Qwen 3.5** would need activations this corpus does not contain.

Concrete next experiments:

1. **Resample two kinds of sentence separately.** (a) The sentences that adopt spots-per-giraffe. (b) The sentences that promise impartiality. Prediction from this write-up: (b) changes nothing; (a) moves the answer with the incentive.
2. Fresh mirrored runs, interleaved, with a person checking the extracted population and spots numbers, to turn Section 5 into a claim or kill it.
3. Prompts that keep the same sentence polarity in both directions, to kill the "exceeds / does not exceed" confound.

---

## Reproducibility

I ran all later analyses offline with fixed random seeds. I recomputed the headline numbers with a second script; they agreed to 0.05 percentage points. Code, per-trace files, and longer reports: **https://github.com/shahshlok/value-leakage** (fork of Aditya's replication repo). Start at `FINAL_REPORT.md`. Then `analysis/hyp1_*` (anchoring control), `hyp6_impartiality` (judge labels and measurement), `hyp7_impartiality_dissociation` (does the promise predict?), `hyp8_locus` (exploratory split of the Fermi product).
