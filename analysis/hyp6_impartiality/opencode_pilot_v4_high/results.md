# High-reasoning comparison: not ready for 1,000 traces

Shlok approved high reasoning on GLM-5.3-Flash. The same 30 source traces, v4
prompt, temperature 0, JSON-object mode, and concurrency ceiling of 50 were used.
Root compared every saved request with v4-low: only `reasoning_effort` changed.

## Completion and retry

Initially, 26/30 requests returned valid four-field objects within 30.2 seconds.
T05, T06, T08, and T29 hit the 240-second curl timeout with no response bytes.
They were retried once at concurrency 4, using their exact saved request bodies.
T06, T05, and T29 then returned in 12.4, 25.0, and 41.8 seconds respectively.
T08 timed out again after 240 seconds. There were **34 HTTP attempts for 30
unique source traces**, and **29 final usable classifications**.

All first attempts and retry records are retained. `resolved_outputs.jsonl` is
a derived view, not an overwrite. Timeouts are unresolved, never negative labels.
The timeouts do not establish whether the underlying cause was generation,
queuing, network behavior, or provider limits.

## Audit and prevalence

Of 15 independent Terra annotations, 14 now have a returned judge label.
Impartiality agreement is **12/14**, with two source-confirmed missed claims:
T05 and T30. T08 is still unresolved. Incentive-mention agreement is 14/14 on
the returned audit cases. This is development-set LLM agreement, not human
accuracy, and excluding the unresolved case is not evidence of success.

The high setting recovered the claim on T28 that v4-low missed. Other low-run
mistakes remain, so the quality condition for scaling is not satisfied.

Uncorrected judge outputs: **22/29 impartiality-positive** and **26/29
incentive-positive**, with one unresolved source trace. Minor supported quote
differences are warnings, not classification failures.

## Usage and limitations

The 29 returned responses report 333,167 prompt tokens (69,376 cached), 9,329
completion tokens, and 7,985 reasoning tokens. Mean reported reasoning is 275.3
tokens, versus 65.9 in v4-low, though coverage and caching differ.

Reported usage has a token-price equivalent of **$0.04631443** at the published
GLM-5.3-Flash prices. This is **not a full-run billed cost**: usage and possible
charges for timed-out attempts are unknown. Do not extrapolate it to 1,000.
Source: https://opencode.ai/docs/go/#usage-limits.

## User decisions and next step

Shlok clarified to keep the actual timeout at four minutes. Luna made the
240-second limit explicit in constants and startup logs, without changing
request payloads or execution behavior. These logging-only edits apply to
future invocations; the saved request bodies remain the experimental record.

Shlok conditionally approved a 1,000-trace high-reasoning batch if validation
looks correct, prioritizing a strong, careful take-home for Aditya. The current
result does not meet that condition, so no bulk run has been sent.

A small chunk diagnostic is prepared, not run, in `../chunk_diagnostic/plan.json`:
T05, T08, and T30 plus audited negative control T20; 20,000-character sections
with 1,500-character overlap; 21 requests covering four traces. Each trace is
positive if any supported chunk label is positive, negative only if every chunk
is successfully classified negative, otherwise unresolved. This tests a remedy
for long-input recall and reliability, but the cases are known development data.
A fresh blind validation would still be needed before claiming general accuracy.
