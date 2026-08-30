# Moral-direction follow-up

Initial decision recorded on 2026-08-29, before fresh generations. Shlok first requested a 40-response pilot, then approved the full-run extension described below after reviewing that pilot.

## Full-run extension approved after the pilot

After inspecting the 40-response pilot, Shlok requested the same sample count as the neutral-boundary cells: 50 per moral direction per model. Generate 40 additional requests per cell, or 160 new requests. Preserve the existing 10 per cell, bringing the combined dataset to 200 moral responses.

Use the unchanged original moral prompts, thresholds, API model IDs, high reasoning, 64,000 output-token maximum, temperature 1, top-p 1, unpinned OpenRouter routing, and concurrency 10 per model. Use local scheduling seed 20260830 for the extension; do not send a model seed. Expected additional cost is about $3.34 based on the pilot's recorded cost, not a guaranteed price.

Save new responses separately in `runs/moral_extension_qwen_pair`. Do not overwrite or refill the pilot. A combined dataset must retain the source file, original row index, and pilot/extension label. Errors count as attempts and are not automatically retried or replaced.

Primary follow-up evidence comes from the 160 new responses, since the pilot has already been inspected. Report the combined 200-response result as a secondary full-dataset summary. Keep the same per-model above-good versus below-good median comparison and independent bootstrap interval. Neutral references remain descriptive, cross-run comparisons. Do not tune the analysis or stop early based on emerging estimates.

Collection completed on 2026-08-29: all 160 extension requests succeeded, with no empty or truncated answers. Additional recorded cost was $3.507974; pilot plus extension cost was $4.343449. `runs/moral_full_qwen_pair` now contains four 50-response cells. Every row retains its source file, source index, and pilot/extension label. All 200 request IDs are unique; copied rows and source hashes were verified. All 200 responses contain both visible answers and reasoning.

Analysis completed on 2026-08-29: all 200 final estimates are now audited and usable. The full-run report is `hypothesis_1_report.md`, with audited values in `full_estimates.csv` and calculations in `full_results.json`. At Shlok's request, the main report presents the full 400 neutral and 200 moral responses without a separate pilot-results section. This is a presentation change, not a retrospective change to the locked analysis: the previously specified unseen-response checks remain in the methods and saved results. Full moral changes are +9.1% for Qwen3.5 and +6.9% for Qwen3.8; the unseen 160-response check gives smaller changes (+4.5% and +3.0%), both with intervals including zero. The full-run signal is suggestive, not a robust moral-direction replication. The original plan below is retained as collection history.

## Question

With the same numerical threshold, does changing which side benefits the good cause change the final estimate?

This tests sensitivity to the direction of the moral consequence. It does not, by itself, isolate the effect of words such as "charity" or "good".

## Data

- Quick check: Aditya's existing above-good and below-good responses for the two Qwen models. Report exact historical thresholds, model IDs, usable counts, and medians. Do not treat historical and fresh runs as interchangeable.
- Immediate pilot: 10 above-good and 10 below-good responses for each of the same two models used in the neutral study, for 40 total requests. The previously selected 200-request design is deferred. Verified thresholds are 41 million for Qwen 3.5 and 40 million for Qwen 3.8, matching the low-anchor neutral cells.
- Reference: the existing neutral-boundary responses at those same low thresholds, using the original 45-response-per-cell holdout. Do not generate another neutral batch.

## Generation

Use Aditya's original moral prompt wording verbatim, as requested by Shlok. Reuse the original prompt builder rather than rewriting it. Insert the agreed threshold and swap only the charity assignment between the two moral conditions. Verify the saved historical prompt against that builder before launch. The Qwen 3.8 historical threshold was 39.5 million, whereas the new neutral and moral threshold is 40 million; record this numerical difference explicitly after source verification.

Use the same saved sampling settings as the neutral run. Randomize/interleave conditions, use OpenRouter without pinning a provider, and record the actual provider and complete request settings with raw responses. This is a fresh moral-direction replication, not an exactly wording-matched neutral/moral intervention.

Keep the code minimal. Save errors without automatic retries. Count failed and truncated responses separately rather than silently replacing or discarding them. Any unchanged-protocol smoke requests count toward the 40; changed-protocol requests must be separate. Do not change the protocol after inspecting the apparent effect. Pilot outcomes are exploratory; if used to change a later design, they must not be described as unseen confirmatory data.

## Analysis

Primary: compare the median final estimate in above-good against below-good, separately for each model. Report usable counts, medians, their ratio, and a bootstrap interval for that ratio. Samples are independent, not paired. Use final answers, not intermediate reasoning estimates, and audit ambiguous extraction without condition labels where feasible.

Secondary: place the existing neutral medians alongside the fresh moral medians. This is a cross-run comparison, not a fully concurrent three-arm randomized experiment. Historical moral results are an exploratory check, not extra fresh samples.

## Interpretation

If above-good produces higher estimates than below-good, despite an identical threshold, that difference is inconsistent with a direction-insensitive numerical anchor alone. It supports sensitivity to the stated consequence, not a particular hidden reasoning mechanism or human-like motivation.

Provider routing, serving changes, separate generation batches, and prompt wording limit historical/neutral comparisons. A null result is inconclusive rather than proof that the moral consequence has no effect.
