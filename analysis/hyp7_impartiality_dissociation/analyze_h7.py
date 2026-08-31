"""Paired, fixed-model H7 bootstrap and coverage diagnostics. Offline only."""
from __future__ import annotations

import hashlib
import json
from collections import Counter

import numpy as np

from prepare_h7 import HERE, ROOT, OUT, H6, CONDITIONS, save_csv, save_json

STRATA = ('all', 'known_label', 'positive', 'negative')
PAIRS = (('positive', 'all'), ('positive', 'known_label'),
         ('known_label', 'all'), ('positive', 'negative'))


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def mean_masked(values, mask, axis=-1):
    count = np.sum(mask, axis=axis)
    total = np.sum(np.where(mask, values, 0), axis=axis)
    return np.divide(total, count, out=np.full(np.shape(total), np.nan), where=count > 0)


def cell_statistics(rows, indices=None):
    y = np.array([r['estimate'] if r['estimate'] is not None else np.nan for r in rows], float)
    labels = np.array([np.nan if r.get('claim') is None else float(r['claim']) for r in rows])
    threshold = np.array([r['threshold'] for r in rows])
    if indices is not None:
        y, labels, threshold = y[indices], labels[indices], threshold[indices]
    log_y = np.log(np.where(np.isfinite(y) & (y > 0), y, 1))
    masks = dict(all=np.ones(y.shape, bool), known_label=np.isfinite(labels),
                 positive=labels == 1, negative=labels == 0)
    result = {}
    for metric in ('log', 'binary'):
        valid = np.isfinite(y) & ((y > 0) if metric == 'log' else True)
        values = log_y if metric == 'log' else (y > threshold).astype(float)
        for stratum, mask in masks.items():
            result[(metric, stratum)] = mean_masked(values, valid & mask)
    return result


def summarize(point, draws):
    draws = np.asarray(draws, float)
    finite = np.isfinite(draws)
    valid = draws[finite]
    conditional = np.quantile(valid, [.025, .975]).tolist() if valid.size else [None, None]
    supported = bool(np.isfinite(point)) and bool(finite.all())
    return dict(estimate=float(point) if np.isfinite(point) else None,
                ci95_low=conditional[0] if supported else None,
                ci95_high=conditional[1] if supported else None,
                one_sided95_lower=float(np.quantile(valid, .05)) if supported else None,
                conditional_finite_ci95_low=conditional[0], conditional_finite_ci95_high=conditional[1],
                bootstrap_n=len(draws), bootstrap_undefined=int((~finite).sum()),
                bootstrap_undefined_fraction=float((~finite).mean()),
                interval_status='supported' if supported else 'withheld_undefined_support')


def add_transform(row):
    if row['metric'] == 'log':
        for source, dest in [('estimate', 'geometric_shift_pct'), ('ci95_low', 'geometric_ci95_low_pct'), ('ci95_high', 'geometric_ci95_high_pct')]:
            row[dest] = None if row[source] is None else float(100 * np.expm1(row[source]))
    else:
        row.update(geometric_shift_pct=None, geometric_ci95_low_pct=None, geometric_ci95_high_pct=None)
    return row


def paired_diff_base_minus_labelpos(rows, dataset, members, seed, n_boot):
    """Within-replicate difference of log contrasts: unconditional (all) minus label-positive."""
    models = [m for m in sorted({r['model_dir'] for r in rows}) if m in members]
    model_points, model_draws = {'all': [], 'positive': []}, {'all': [], 'positive': []}
    for model in models:
        cells = {c: [r for r in rows if r['model_dir'] == model and r['condition'] == c] for c in CONDITIONS}
        points, draws = {}, {}
        for condition, group in cells.items():
            stable_seed = int(hashlib.sha256(f'{seed}|{dataset}|{model}|{condition}'.encode()).hexdigest()[:16], 16)
            rng = np.random.default_rng(stable_seed)
            indices = rng.integers(len(group), size=(n_boot, len(group)))
            stats = cell_statistics(group, indices)
            pts = cell_statistics(group)
            points[condition] = {s: pts[('log', s)] for s in ('all', 'positive')}
            draws[condition] = {s: stats[('log', s)] for s in ('all', 'positive')}
        for stratum in ('all', 'positive'):
            model_points[stratum].append(points['above_good'][stratum] - points['below_good'][stratum])
            model_draws[stratum].append(draws['above_good'][stratum] - draws['below_good'][stratum])
    pooled_points = {s: np.mean(model_points[s]) for s in ('all', 'positive')}
    pooled_draws = {s: np.mean(model_draws[s], axis=0) for s in ('all', 'positive')}
    log_diff = pooled_draws['all'] - pooled_draws['positive']
    log_point = pooled_points['all'] - pooled_points['positive']
    pp_diff = 100 * (np.expm1(pooled_draws['all']) - np.expm1(pooled_draws['positive']))
    pp_point = float(100 * (np.expm1(pooled_points['all']) - np.expm1(pooled_points['positive'])))
    log_stats = summarize(log_point, log_diff)
    finite = np.isfinite(pp_diff)
    pp_ci = np.quantile(pp_diff[finite], [.025, .975]).tolist() if finite.any() else [None, None]
    return dict(dataset=dataset, tier='primary_9', comparison='base_minus_labelpos', n_models=len(models),
                log_scale=dict(estimate=log_stats['estimate'], ci95_low=log_stats['ci95_low'],
                               ci95_high=log_stats['ci95_high'], interval_status=log_stats['interval_status']),
                percentage_points=dict(estimate=pp_point, ci95_low=pp_ci[0], ci95_high=pp_ci[1]),
                n_replicates_used=int(finite.sum()), n_replicates_missing=int((~finite).sum()),
                bootstrap_n=n_boot, bootstrap_undefined=log_stats['bootstrap_undefined'],
                bootstrap_undefined_fraction=log_stats['bootstrap_undefined_fraction'],
                note='Paired within-replicate difference (unconditional minus label-positive log contrasts); '
                     'percentage points are back-transformed shift differences, not expm1 of the log difference.')


def analyze_dataset(rows, dataset, tiers, seed, n_boot):
    models = sorted({r['model_dir'] for r in rows})
    model_points, model_draws, estimates, differences, rates, bounds = {}, {}, [], [], [], []
    for model in models:
        cells = {c: [r for r in rows if r['model_dir'] == model and r['condition'] == c] for c in CONDITIONS}
        points, draws = {}, {}
        for condition, group in cells.items():
            stable_seed = int(hashlib.sha256(f'{seed}|{dataset}|{model}|{condition}'.encode()).hexdigest()[:16], 16)
            rng = np.random.default_rng(stable_seed)
            indices = rng.integers(len(group), size=(n_boot, len(group)))
            points[condition] = cell_statistics(group)
            draws[condition] = cell_statistics(group, indices)
            for stratum in STRATA:
                subset = [r for r in group if stratum == 'all' or
                          stratum == 'known_label' and r.get('claim') is not None or
                          stratum == 'positive' and r.get('claim') is True or
                          stratum == 'negative' and r.get('claim') is False]
                numeric = [r for r in subset if r['estimate'] is not None and np.isfinite(r['estimate'])]
                above = sum(r['estimate'] > r['threshold'] for r in numeric)
                rates.append(dict(dataset=dataset, model_dir=model, condition=condition, stratum=stratum,
                    n_selected=len(subset), n_finite_y=len(numeric), n_log_y=sum(r['estimate'] > 0 for r in numeric),
                    above_threshold=above, at_threshold=sum(r['estimate'] == r['threshold'] for r in numeric),
                    above_threshold_rate=above / len(numeric) if numeric else None,
                    donation_favorable_rate=(above if condition == 'above_good' else len(numeric) - above) / len(numeric) if numeric else None,
                    # These bounds cover missing Y within the observed label subset only.
                    threshold_rate_lower=above / len(subset) if subset else None,
                    threshold_rate_upper=(above + len(subset) - len(numeric)) / len(subset) if subset else None))
        for key in points['above_good']:
            p = points['above_good'][key] - points['below_good'][key]
            d = draws['above_good'][key] - draws['below_good'][key]
            model_points[(model, *key)], model_draws[(model, *key)] = p, d
            row = dict(dataset=dataset, tier='per_model', model_dir=model, n_models=1,
                       metric=key[0], stratum=key[1], **summarize(p, d))
            estimates.append(add_transform(row))
        for stratum in STRATA:
            rs = {r['condition']: r for r in rates if r['model_dir'] == model and r['stratum'] == stratum}
            a, b = rs['above_good'], rs['below_good']
            valid = a['threshold_rate_lower'] is not None and b['threshold_rate_lower'] is not None
            bounds.append(dict(dataset=dataset, tier='per_model', model_dir=model, stratum=stratum,
                lower=a['threshold_rate_lower'] - b['threshold_rate_upper'] if valid else None,
                upper=a['threshold_rate_upper'] - b['threshold_rate_lower'] if valid else None,
                interpretation='Finite-sample missing-Y identification bounds; not CI; labels treated as observed subsets; no log-effect bound.'))
    effective_tiers = {**{f'model:{m}': [m] for m in models}, **tiers}
    for tier, members in effective_tiers.items():
        if not members:
            continue
        for metric in ('log', 'binary'):
            pooled_p, pooled_d = {}, {}
            for stratum in STRATA:
                # np.mean intentionally propagates NaN; never nanmean/reweight.
                p = np.mean([model_points[(m, metric, stratum)] for m in members])
                d = np.mean([model_draws[(m, metric, stratum)] for m in members], axis=0)
                pooled_p[stratum], pooled_d[stratum] = p, d
                if not tier.startswith('model:'):
                    estimates.append(add_transform(dict(dataset=dataset, tier=tier, model_dir='',
                        n_models=len(members), metric=metric, stratum=stratum, **summarize(p, d))))
            for left, right in PAIRS:
                p, d = pooled_p[left] - pooled_p[right], pooled_d[left] - pooled_d[right]
                stats = summarize(p, d)
                differences.append(dict(dataset=dataset, tier=tier, n_models=len(members), metric=metric,
                    comparison=f'{left}_minus_{right}', **stats,
                    attenuation_compatible_95_upper=None if stats['ci95_low'] is None else max(0., -stats['ci95_low']),
                    note='Paired difference of condition contrasts, not an intervention effect; a non-significant difference is not equivalence.'))
            if np.isfinite(pooled_p['positive']) and np.isfinite(pooled_p['known_label']):
                assert np.isclose(pooled_p['positive'] - pooled_p['all'],
                    (pooled_p['positive'] - pooled_p['known_label']) + (pooled_p['known_label'] - pooled_p['all']))
        if not tier.startswith('model:'):
            for stratum in STRATA:
                b = [r for r in bounds if r['tier'] == 'per_model' and r['model_dir'] in members and r['stratum'] == stratum]
                complete = len(b) == len(members) and all(r['lower'] is not None for r in b)
                bounds.append(dict(dataset=dataset, tier=tier, model_dir='', stratum=stratum,
                    lower=float(np.mean([r['lower'] for r in b])) if complete else None,
                    upper=float(np.mean([r['upper'] for r in b])) if complete else None,
                    interpretation='Equal fixed-model mean of finite-sample missing-Y bounds; not CI or log-effect bounds.'))
    return estimates, differences, rates, bounds


def baseline_and_crosstabs(h6):
    baselines, cross, balance = [], [], []
    for model in sorted({r['model_dir'] for r in h6}):
        raw = json.loads((ROOT / 'runs' / model / 'estimates.json').read_text())['baseline']
        values = [float(v) for v in raw if type(v) in (int, float) and np.isfinite(v) and v > 0]
        q = np.quantile(values, [.25, .5, .75])
        threshold = next(r['threshold'] for r in h6 if r['model_dir'] == model)
        def region(value):
            return 'below_range' if value < min(values) else 'above_range' if value > max(values) else f'Q{np.searchsorted(q, value, side="left") + 1}'
        for condition in ('baseline', *CONDITIONS):
            nums = values if condition == 'baseline' else [r['estimate'] for r in h6 if r['model_dir'] == model and r['condition'] == condition and r['value_status'] == 'positive']
            counts = Counter(map(region, nums))
            for name in ('below_range', 'Q1', 'Q2', 'Q3', 'Q4', 'above_range'):
                baselines.append(dict(model_dir=model, condition=condition, region=name, n=counts[name],
                    n_usable=len(nums), fraction=counts[name] / len(nums) if nums else None,
                    baseline_n_total=len(raw), baseline_n_usable=len(values),
                    q25=q[0], q50=q[1], q75=q[2], threshold=threshold,
                    median_equals_threshold=bool(q[1] == threshold),
                    caveat='Existing baseline extraction; actual tied bin masses; descriptive regions, not discovered modes.'))
        for condition in CONDITIONS:
            group = [r for r in h6 if r['model_dir'] == model and r['condition'] == condition]
            n_obs = sum(r['claim'] is not None for r in group)
            n_pos = sum(r['claim'] is True for r in group)
            balance.append(dict(model_dir=model, condition=condition, selected=len(group), observed=n_obs,
                positive=n_pos, positive_rate=n_pos / n_obs if n_obs else None,
                caveat='Descriptive balance cannot remove post-treatment selection.'))
            for claim in (True, False, None):
                for mention in (True, False, None):
                    cross.append(dict(model_dir=model, condition=condition, claim=claim, mentions_incentive=mention,
                        n=sum(r['claim'] is claim and r['mentions_incentive'] is mention for r in group)))
    save_csv(OUT / 'baseline_overlap.csv', baselines)
    save_csv(OUT / 'mentions_cross_tab.csv', cross)
    save_csv(OUT / 'label_balance.csv', balance)


def main():
    protocol = json.loads((OUT / 'protocol.json').read_text())
    h6, full = read_jsonl(OUT / 'h7_outcomes.jsonl'), read_jsonl(OUT / 'full_corpus_answers.jsonl')
    primary, all_models = protocol['primary_models'], protocol['sensitivity_models']
    informative = [m for m in primary if all(any(r['model_dir'] == m and r['condition'] == c and r['claim'] is label and r['value_status'] == 'positive' for r in h6) for c in CONDITIONS for label in (True, False))]
    tiers = dict(primary_9=primary, all_10=all_models,
        raw_reasoning_8=protocol['raw_reasoning_primary_models'],
        claude_summary_only=[m for m in all_models if m.startswith('claude')],
        both_labels_supported=informative)
    save_json(OUT / 'cohort_membership.json', {k: dict(models=v, weight_per_model=1 / len(v) if v else None) for k, v in tiers.items()})
    estimates, differences, rates, bounds = [], [], [], []
    datasets = [('h6_corrected', h6), ('full_fresh_parse', full)]
    # Preserve pure fresh parsing, while exposing known parser errors as a sensitivity.
    corrected = {r['source_id']: r for r in h6 if r['answer_source'] == 'reviewed_correction'}
    harmonized = [dict(r, estimate=corrected[r['source_id']]['estimate'], value_status=corrected[r['source_id']]['value_status']) if r['source_id'] in corrected else dict(r) for r in full]
    datasets.append(('full_fresh_plus_reviewed_corrections', harmonized))
    disclosure_path = OUT / 'disclosure_exclusions.json'
    if disclosure_path.exists():
        exclusions = json.loads(disclosure_path.read_text())
        for name in ('confirmed', 'confirmed_or_uncertain'):
            excluded = set(exclusions[name])
            assert excluded <= {r['source_id'] for r in full}
            datasets.append((f'h6_excluding_{name}_audited_disclosures', [r for r in h6 if r['source_id'] not in excluded]))
    for name, rows in datasets:
        e, d, r, b = analyze_dataset(rows, name, tiers, protocol['seed'], protocol['bootstrap_replicates'])
        estimates.extend(e)
        differences.extend(d)
        rates.extend(r)
        bounds.extend(b)
    save_csv(OUT / 'contrasts.csv', estimates)
    save_csv(OUT / 'paired_differences.csv', differences)
    save_csv(OUT / 'threshold_rates.csv', rates)
    save_csv(OUT / 'missing_y_bounds.csv', bounds)
    baseline_and_crosstabs(h6)
    headline = [r for r in estimates if r['dataset'] == 'h6_corrected' and r['tier'] == 'primary_9']
    paired = [r for r in differences if r['dataset'] == 'h6_corrected' and r['tier'] == 'primary_9']
    paired_diff = paired_diff_base_minus_labelpos(h6, 'h6_corrected', primary, protocol['seed'],
                                                  protocol['bootstrap_replicates'])
    summary = dict(design='Retrospective offline proxy diagnostic; fixed original models, not causal mediation.',
        n_h6=len(h6), n_y=841, n_label=951, n_joint=796, tiers=tiers,
        bootstrap_seed=protocol['seed'], bootstrap_replicates=protocol['bootstrap_replicates'],
        primary_contrasts=headline, primary_paired_differences=paired,
        paired_diff_base_minus_labelpos=paired_diff,
        equivalence_margin=None,
        limitations=['Impartiality labels include normative aspirations and may be noisy.',
            'Conditioning on observed claims is post-treatment; contrast differences do not identify causal moderation.',
            'Parser and judge missingness are distinct; log contrasts are not missingness bounded.',
            'Bootstrap assumes exchangeable independent responses within observed model-condition cells; no model-population generalization.',
            'No equivalence margin was specified: a CI containing zero does not prove an empty proxy.',
            'Disclosure retrieval has unknown recall; nonhits are not confirmed nondisclosures.',
            'Claude contains API summaries rather than raw CoT; primary excludes DS Pro for severe original-source attrition.',
            'Full fresh parser is only partly audited; a separate sensitivity applies the nine existing source-reviewed corrections.'])
    save_json(OUT / 'bootstrap_summary.json', summary)
    print(json.dumps(dict(primary_log=[r for r in headline if r['metric'] == 'log'],
                         paired_log=[r for r in paired if r['metric'] == 'log'],
                         paired_diff_base_minus_labelpos=paired_diff,
                         both_labels_supported=informative), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
