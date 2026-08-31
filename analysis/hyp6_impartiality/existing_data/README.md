# Existing-data H6 artifacts

This directory contains the offline descriptive analysis of the original 1,000-trace H6 batch. It does not include H1 fresh generations, new model calls, or causal interventions.

Run:

```bash
python analysis/hyp6_impartiality/existing_data/analyze_existing.py
python analysis/hyp6_impartiality/existing_data/plot_existing.py
```

Key outputs are `direction_comparisons.csv`, `baseline_region_shares.csv`, `rounding_screen_counts.csv`, `summary.json`, and `commitments_and_behavior.png`. The report is `../hypothesis_6_report.md`. The prior report is preserved verbatim as `../numerical_consistency_report.md`.

The analysis uses 50 below-good and 50 above-good traces per model, excludes 30 calibration sources, and retains missing answers as missing. Nine corrections have source hashes, row-key joins, offsets, and numeric excerpt checks. The other parser-clear answers are not wholesale human-audited ground truth. Binary missingness bounds apply only to above-threshold rates and do not bound log means. Quartile regions are descriptive baseline bins; ties are assigned to the lower bin, and Qwen 3.5's baseline median equals its threshold.

`rounding_audit.json` is a bounded qualitative audit of 12 cases selected by a deterministic stratified recipe from 68 automated candidates. It is not a rounding prevalence estimate or validation sample.

