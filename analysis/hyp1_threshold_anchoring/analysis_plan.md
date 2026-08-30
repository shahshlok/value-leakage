# H1 threshold-anchoring analysis plan (phase 1)

## Locked design

- Primary holdout: rows `i=5..49`.
- Pilot: rows `0..4`.
- Primary framing: `neutral_boundary` high-vs-low.
- Secondary framing: `irrelevant_number`.
- Outcome: `log1p(final estimate)`.
- Model-specific median log differences, pooled with equal 50/50 model weight.
- One-sided 100,000 within-model label permutations, seed `20260829`.
- 10,000 stratified bootstrap confidence interval, seed `20260829`.
- Holm correction over the two framing-level tests.
- Sensitivity analyses: provider sensitivity and all-400 sensitivity.
- Missingness threshold: `<10/cell`.
- No reasoning field use.

## Phase-1 extraction rules

- Extraction is local and deterministic from visible response content only.
- Accept nonnegative single final answers, including zero.
- Parse commas, scientific notation, and million/billion shorthand.
- Unresolved ranges and conflicting finals are marked ambiguous.
- Condition metadata is never used to make parsing decisions.
- Audit every ambiguous row plus a fixed-seed 10% sample of clear rows while blinded.

## Scope lock

Phase 1 produces blinded extraction and audit artifacts only. It does not compute or reveal condition effects or summary statistics.
