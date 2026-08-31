# Value Leakage in the Donation Bet Task — Submission Overview

**Take-home submission, Model Forensics SPAR.**
One dataset: ten models, 100 responses each in `baseline`, `below_good`, and `above_good` conditions, where a Fermi estimate (total black spots on all living giraffes) crossing a fixed threshold determines whether a good or a bad cause receives a donation. The two incentivized conditions share an identical numerical threshold per model; only the donation direction flips.

The submission asks whether this is a case of the model **lying in its reasoning**, and answers by testing four explanations:

## 1. It is just the number, not the morality — TRUE

`analysis/hyp1_threshold_anchoring/`, `analysis/hyp1_moral_comparison/`

Numerical context alone moves Fermi estimates: a neutral boundary the prompt says has no consequences moved answers **+26%**, and a framing that declares the number an irrelevant random draw still moved them **+16%** (400 fresh responses; analysis plan locked and hash-published before the 360-response holdout was analyzed). Models at both ends of Aditya's replication moved this way; the strongest-signal model (Inkling) was unusable, rate-limited at 4–5 tokens per second, roughly 27 minutes per answer. Consequence: every later analysis relies exclusively on the mirrored fixed-threshold contrast, where anchoring is controlled by design.

## 2. Honest math, then a nicer final number — FALSE

`analysis/hyp6_impartiality/numerical_consistency_report.md`, `analysis/hyp6_impartiality/verify_gaps/`

The reported answer matches the model's own working. Of **294 traces** where the reasoning's final committed figure could be checked against the visible answer, 34 differed by ≥5% (17 toward the good cause, 17 away — a coin flip); separate-request re-verification retained **3** discrepancies, none of which changed who got the money. The shift does not enter at the final number. (A first extraction pass reported 63% of traces disagreeing — every one an extraction bug; that false alarm is why every extraction in this project was audited afterward.)

## 3. Saying "I will be fair" tells you nothing — TRUE

`analysis/hyp6_impartiality/hypothesis_6_report.md`, `analysis/hyp7_impartiality_dissociation/hypothesis_7_report.md`

A blinded judge labeled 1,000 reasoning traces (951 usable; 727 explicit fairness promises). Answers shift **+15.5%** [9.4, 22.1] toward the donation-favorable side; among the traces that promised to be fair they shift **+14.1%** [7.7, 20.9] — paired difference **+1.4 pp** [−1.4, 4.5]. Threshold crossing rises **+32.1 pp** [25.6, 38.6]. The promise fires on nearly everything (589/753 in the headline cohort; 100/100 for Qwen 3.5), so it is empty partly by construction, and no adequate non-promise stratum exists in the models driving the effect. A blinded, rubric-frozen, span-verified adjudication of 40 disclosure candidates: **33/40 saw the temptation, named it, and turned it down**; only **8** adopted a donation-tied choice; dropping them leaves the shift at +15.1%. Identifiable transparent disclosures do not account for the effect.

## 4. The bias slips in through the one number nobody can check — PROBABLY

`analysis/hyp8_locus/`

The giraffe population is pinned by the world (~1.1× span across models); spots per giraffe is unconstrained (~5.1× span, every value arguable). The movement concentrates exactly there: population **−1.7%** [−3.4, −0.0], spots per giraffe **+8.6%** [4.0, 13.3]. Claimed as a lead, not a result: 5 of 20 audited extractions were wrong (25%), and the gate pass rate differs between conditions by up to 17 pp. It makes a sharp, falsifiable prediction for the next experiment.

## The answer

The reasoning is **incomplete rather than false**: it reports its arithmetic and its intention correctly, and omits the one input that actually moved — which is why reading the reasoning cannot catch this behavior. One counter-reading stands out: **13 of 40** audited traces went beyond promising and retrospectively denied the bet's influence — statements about the past, the closest thing to actual dishonesty in this corpus, and the first place to look next.

**Next experiments (proposed in the submission):** cross donation direction with sentence phrasing ("exceeds" / "does not exceed"), arms shuffled, server pinned; and edit reasoning in place — insert a fairness promise or fix the spots-per-giraffe number, measuring the change in the condition gap. Sentence resampling (Aditya's suggestion) is the same as the second design. Not done: the J-lens, judging all 3,000 traces, and a human re-read of the 18 borderline disclosure cases.

## What we claim, and what we refuse to claim

**Claimed:** robust, anchoring-controlled behavioral sensitivity to donation direction; arithmetic honesty at the reporting stage; the diagnostic emptiness of fairness promises as a faithfulness proxy; a bounded null on disclosed adjustment as the explanation.

**Refused:** hidden influence, concealment, intent, or deception; per-trace unfaithfulness (the dissociation is a population property); the loose-number mechanism (extraction audit failed); motivated reasoning asserted without the residual confounds (the mirrored prompts differ in phrasing beyond moral direction; conditions were not perfectly interleaved across providers); generalization beyond these ten models and this task. The model adjudication (judge and disclosure reviewer) is stated as a limitation, not buried.

## Reproducibility

All headline numbers were independently recomputed by a second implementation and agreed to within 0.05 percentage points. Primary analysis: `analysis/hyp7_impartiality_dissociation/analyze_h7.py` (fixed seed, 10,000 stratified bootstrap replicates); independent verification: `verify_h7_independent.py`; figures in `analysis/hyp7_impartiality_dissociation/outputs/` and `submission_figures/`. No numbers in any report lack an in-repo reproducible source.
