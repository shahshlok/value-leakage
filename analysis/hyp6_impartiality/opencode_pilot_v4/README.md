# V4 calibration completed, not ready to scale

Shlok approved this pilot and it completed on 2026-08-30. See `results.md`:
29/30 complete four-field outputs and 11/15 impartiality agreement with Terra.
The revised low-effort configuration did not pass the audit.

This prompt revision follows the 30-trace OpenCode pilot. The judge model remains
`glm-5.3-flash`, requested reasoning effort `low`, temperature 0. Use direct
asynchronous curl requests with a concurrency ceiling of 50, reasoning-only
inputs, per-result checkpoints, full usage recording, and no explicit output
token cap. The pilot has only 30 traces, so at most 30 requests run simultaneously.

Use `response_format: {"type": "json_object"}` and validate the four fields
locally. The prior request's strict JSON-schema parameter did not prevent fenced
or escaped JSON, so server-enforced schema compliance is not established.
Z.AI documents JSON-object mode for its API; behavior through OpenCode still
requires testing.

The revision clarifies that explicit anti-bias commitments count and asks the
judge to inspect the full trace before a negative label. This matches the
intended presence-of-claim construct, including the handoff's "must remain
neutral" examples. It also distinguishes a bare threshold from incentive stakes
and requires a single unwrapped JSON object. It does not ask whether the answer
is biased, and it includes no source-model or condition metadata.

Small quote wording or whitespace differences are diagnostic warnings, not
automatic label failures, per Shlok's instruction. Unsupported evidence and
wrong labels remain substantive failures.

The existing 30 traces and the 15 Terra labels are now development data. A rerun
can diagnose improvement, but is not an independent validation. A fresh blinded
sample would strengthen any accuracy claim before scaling.

The 30-trace v4 generation is complete. No further pilot or 1,000-trace run is
authorized.

Sources: https://docs.z.ai/api-reference/llm/chat-completion and
https://opencode.ai/docs/go/#endpoints.
