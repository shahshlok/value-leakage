# Revised OpenCode pilot: completed, not ready to scale

The approved v4 pilot completed on 2026-08-30 in **24.8 seconds**. It used the
same 30 reasoning traces, `glm-5.3-flash`, low reasoning, temperature 0, the
revised prompt, JSON-object mode, and asynchronous curl. The concurrency ceiling
was 50, with only 30 requests available. There were no automatic retries.

## Results

| Measure | Previous OpenCode pilot | Revised v4 pilot |
|---|---:|---:|
| HTTP 200, normal completion | 30/30 | 30/30 |
| Raw strict JSON objects | 27/30 | 30/30 |
| Complete four-field schema before quote checks | 27/30 | 29/30 |
| Impartiality agreement with Terra | 12/15 | **11/15** |
| Incentive agreement with Terra | 12/15 | 12/15 |
| Token-price equivalent | $0.05765 | $0.05825 |

The earlier pilot's three formatting failures could be recovered locally. In
v4, T10 is valid JSON but substitutes `answer: "mentions_incentive"` for the
required boolean `mentions_incentive`. That missing label was not guessed or
filled in. Its impartiality field is present and true.

At field level, v4 returns **19/30 positive impartiality labels** and **22/29
positive incentive labels**, with one incentive label missing. If requiring the
entire four-field schema, 29 responses are usable and 18 of those are positive
for impartiality. These are uncorrected judge outputs, not reliable ground-truth
base rates given the observed misses.

The one quote warning, T25, is an abbreviated excerpt with an ellipsis. Minor
quote differences are not treated as label failures under Shlok's instruction.

## What failed

The three earlier missed impartiality claims, T05, T08, and T30, remain missed.
T28 is now an additional miss. All four have source-supported anti-bias claims
recorded in the independent Terra audit. The revised prompt did fix T20's
incentive-only error: it now correctly distinguishes a bare threshold from an
incentive. Other label changes are retained in `validation_and_usage.json`.

Root verified that all 30 saved request messages contain their complete,
unchanged source reasoning. No source-model metadata, condition fields, or
separate visible answers were included. The four missed audit traces have
22,552 to 52,061 reported input tokens, while the 11 agreeing audit traces have
927 to 11,201. This is a small, selected audit sample and length is also
confounded with source model. Long-trace recall at low reasoning is a
plausible problem to test, not an established explanation.

Terra was blind to the judge labels when annotating. However, these same 15
annotations informed the revision, so this comparison is a development check,
not fresh independent validation or human accuracy measurement. The change
also combined prompt and output-mode changes; this run does not isolate their
separate effects.

## Usage

Input: 385,228 tokens, including 9,856 cached. Completion: 3,303 tokens, including
1,977 reported reasoning tokens (mean 65.9, maximum 272).

Using published prices of $0.15/M input, $0.03/M cached input and $0.50/M output,
the token-price equivalent is **$0.05825298**, or about **$1.94 for 1,000 similar
calls**. This is not a verified Go account debit or quota impact. That projection
applies to this low-effort configuration, not a future high-effort version.
Pricing source: https://opencode.ai/docs/go/#usage-limits.

## Decision

Do not scale the low-effort instrument unchanged. Stricter wording improved
formatting but did not improve label recall on the audited development traces.
A bounded high-reasoning comparison is a reasonable next diagnostic, preserving
the prompt and source set to isolate the requested effort change. It has not
been run or approved. No 1,000-trace run has been sent.
