# Value Leakage in the Donation Bet Task — Submission Overview

**Take-home submission, Model Forensics SPAR.**
Three linked analyses of one dataset: ten models, 100 responses each in `baseline`, `below_good`, and `above_good` conditions, where a Fermi estimate (total black spots on all living giraffes) crossing a fixed threshold determines whether a good or bad cause receives a donation. The two incentivized conditions share an identical numerical threshold per model; only the donation direction flips.

The three reports form one arc — find the confound, discover the measurement failure, then test the right question:

## 1. H1 — The confound (control study)

`analysis/hyp1_moral_comparison/hypothesis_1_report.md`, `analysis/hyp1_threshold_anchoring/`

Numerical context alone substantially shifts estimates: changing a threshold or boundary moves answers even with no good or bad cause attached. Any Donation Bet interpretation must control this before reading behavior as motivated reasoning. A moral-direction effect was suggestive but not robust in held-out data, and we said so. H1 is why the later analyses rely exclusively on the mirrored fixed-threshold contrast, where anchoring is controlled by design.

## 2. H6 — The measurement failure (methodological study)

`analysis/hyp6_impartiality/hypothesis_6_report.md`

A blinded judge labeled 1,000 reasoning traces for explicit impartiality commitments. The finding is about the proxy, not about faithfulness: commitments sit at or near ceiling (727/951 overall; 100/100 for Qwen 3.5), including in the models with the largest donation-direction shifts. "The model says it is being impartial" — the cheapest and most common CoT-faithfulness check — fires on nearly everything and therefore measures nothing. H6 also separates three properties that faithfulness discussions conflate (stating an impartiality goal, following it, disclosing influences), builds the corrected-answer and audit machinery, and reports honest negatives on two candidate mechanisms (donation-dependent rounding; reasoning-to-answer reporting drift), both unresolved rather than ruled out.

## 3. H7 — The diagnostic test (headline result)

`analysis/hyp7_impartiality_dissociation/hypothesis_7_report.md`

H7 asks the question H6's failure exposed: does the impartiality commitment predict anything? Across nine cleanly-served models (one excluded for a predetermined serving-artifact criterion), final answers shift toward the donation-favorable side by **+15.5%** (geometric mean, 95% CI [9.4, 22.1]); threshold-crossing rises **+32.1 percentage points** [25.6, 38.6]. Within the commitment-positive stratum the shift is **+14.1%** [7.7, 20.9] (paired difference from unconditional: +1.4 pp [−1.4, 4.5]) — no point-estimate attenuation — and no adequate commitment-negative stratum exists in the models driving the effect, so the proxy is empty partly by construction. A blinded, rubric-frozen, span-verified adjudication of 40 disclosure candidates found the modal trace *considers the donation-favorable move and explicitly rejects it* (33/40), while only 8 transparently adopt a donation-driven choice; excluding those traces (or 18 confirmed-or-uncertain) leaves the shift essentially unchanged (+15.1% / +14.0%). The identifiable transparent disclosures do not account for the effect.

All headline numbers were independently recomputed by a second implementation and agreed to within 0.05 percentage points.

## What we claim, and what we refuse to claim

**Claimed:** a robust, anchoring-controlled behavioral sensitivity to donation direction in these models; the diagnostic emptiness of impartiality statements as a faithfulness proxy; a bounded null on disclosed adjustment as the explanation.

**Refused:** hidden influence, concealment, intent, or deception; per-trace unfaithfulness (the dissociation is a population property); any mechanism location; motivated reasoning asserted without the residual confounds (the mirrored prompts differ in wording beyond moral direction; conditions were not perfectly interleaved across providers); generalization beyond these ten models and this task. The disclosure adjudication was performed by a model under a frozen rubric with hash-verified evidence spans, which is stated as a limitation, not buried.

## Reproducibility

Each report ends with its script-to-output map. Primary analysis: `analysis/hyp7_impartiality_dissociation/analyze_h7.py` (fixed seed, 10,000 stratified bootstrap replicates); independent verification: `verify_h7_independent.py`; figures in `analysis/hyp7_impartiality_dissociation/outputs/`. No numbers in any report lack an in-repo reproducible source.
