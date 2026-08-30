# Hypothesis 1: threshold anchoring

## Question

Does a model change its Fermi estimate merely because the prompt displays a numerical cutoff, even when crossing that cutoff has no moral consequence?

## Design

We tested two models from opposite ends of Aditya's original value-leakage results:

- Qwen 3.5, which previously showed relatively high value leakage.
- Qwen 3.8, which previously showed almost none.

Each model received two neutral prompt framings and two anchors. The primary framing described the number as a consequence-free bookkeeping boundary. The secondary framing described it as an irrelevant random number. There were 50 responses in each of eight cells, for 400 responses total.

The first five responses per cell were inspected as a pilot. The analysis below uses only the remaining 45 responses per cell, giving a 360-response holdout dataset. Final numerical answers were extracted from visible answer text and audited blind to model, framing, anchor, and provider.

## Results

### Primary: neutral bookkeeping boundary

| Model | Low anchor | Median estimate | High anchor | Median estimate | Change |
|---|---:|---:|---:|---:|---:|
| Qwen 3.5 | 41M | 39.6M | 85M | 52M | +31% |
| Qwen 3.8 | 40M | 24M | 80M | 29M | +21% |

The equal-weight pooled shift was approximately **+26%**. A simple stratified bootstrap placed the 95% interval at approximately **+3% to +37%**.

### Secondary: irrelevant random number

| Model | Low number | Median estimate | High number | Median estimate | Change |
|---|---:|---:|---:|---:|---:|
| Qwen 3.5 | 41M | 40.5M | 85M | 52M | +28% |
| Qwen 3.8 | 40M | 28M | 80M | 29.25M | +4% |

The equal-weight pooled shift was approximately **+16%**, with a bootstrap interval of approximately **+2% to +35%**.

## Interpretation

The holdout data support threshold anchoring. Raising a morally neutral displayed number raised the median estimate for both models under the primary bookkeeping framing. The same direction appeared under the irrelevant-number framing, although it was much weaker for Qwen 3.8.

This means that some movement seen in the original Donation Bet experiment could come from ordinary numerical anchoring rather than moral motivation. It does **not** show that threshold anchoring explains the entire value-leakage effect. A direct comparison with matched moral prompts would be needed to estimate how much additional movement is caused by the good-versus-bad consequence.

## Limitations

- OpenRouter selected several providers, so provider or serving differences may add noise.
- The original Qwen 3.8 data used Fireworks, whereas this follow-up used OpenRouter.
- The low and high anchors were deliberately far apart. This identifies whether estimates respond to the displayed number, but it does not map the full dose-response curve.
- The two neutral framings are not psychologically identical: explicitly calling a number irrelevant may encourage the model to resist it.

## Bottom line

**Yes: in this experiment, merely changing a neutral displayed cutoff moved model estimates toward the higher number. Threshold anchoring is therefore a real control that should be separated from moral value leakage.**
