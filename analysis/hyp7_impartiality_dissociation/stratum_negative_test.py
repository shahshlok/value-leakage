"""Within-model label-stratum donation-direction contrasts for the two models
with a substantial label-negative stratum. Offline only; no network calls.

Resamples records within model × condition × stratum (seed 46062032).
Empty contributing cells make that replicate undefined; frequencies are
recorded and never silently dropped.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
H6 = HERE.parent / 'hyp6_impartiality'
OUT = HERE / 'stratum_negative_results.json'

SEED = 46062032
N_BOOT = 10000
CONDITIONS = ('below_good', 'above_good')
STRATA = ('positive', 'negative')
MODELS = (
    ('deepseek-v4-flash-0731', 23_700_000),
    ('qwen3p8-2p4t-a95b', 39_500_000),
)
# Established usable-Y (Y>0) stratum sizes; fail loudly if the join drifts.
EXPECTED_USABLE = {
    'deepseek-v4-flash-0731': {'negative': 51, 'positive': 29},
    'qwen3p8-2p4t-a95b': {'negative': 37, 'positive': 46},
}

INTERPRETATION_FRAME = (
    'this is the only place in the corpus where the impartiality label\'s '
    'diagnostic value can be tested against a substantial negative stratum '
    'rather than at ceiling. If the label-negative stratum shifts similarly '
    'to label-positive, the label is uninformative at the trace level within '
    'these models too. If the strata differ meaningfully (in either direction), '
    'that is a real moderation signal and must be reported honestly — including '
    'the direction. Small strata mean wide intervals; do not over-interpret '
    'point differences whose paired interval spans zero.'
)


def observed_label(judge):
    parsed = judge.get('parsed')
    value = parsed.get('impartiality_claim') if isinstance(parsed, dict) else None
    ok = str(judge.get('http_status')) == '200' and judge.get('finish_reason') == 'stop'
    return value if ok and type(value) is bool else None


def parse_estimate(raw):
    if raw is None or raw == '':
        return None
    value = float(raw)
    return value if np.isfinite(value) else None


def cell_rng(model, condition, stratum):
    material = f'{SEED}|stratum_negative_test|{model}|{condition}|{stratum}'
    return np.random.default_rng(int(hashlib.sha256(material.encode()).hexdigest()[:16], 16))


def percentile_ci(draws):
    draws = np.asarray(draws, float)
    finite = np.isfinite(draws)
    valid = draws[finite]
    n_undefined = int((~finite).sum())
    conditional = np.quantile(valid, [0.025, 0.975]).tolist() if valid.size else [None, None]
    point_ok = valid.size > 0
    supported = bool(finite.all()) and point_ok
    return dict(
        ci95_low=conditional[0] if supported else None,
        ci95_high=conditional[1] if supported else None,
        conditional_finite_ci95_low=conditional[0],
        conditional_finite_ci95_high=conditional[1],
        bootstrap_n=int(len(draws)),
        bootstrap_undefined=n_undefined,
        bootstrap_undefined_fraction=float((~finite).mean()) if len(draws) else None,
        interval_status='supported' if supported else 'withheld_undefined_support',
    )


def pack(point, draws, extra=None):
    row = dict(estimate=None if point is None or not np.isfinite(point) else float(point))
    row.update(percentile_ci(draws))
    if extra:
        row.update(extra)
    return row


def load_joined():
    answers = list(csv.DictReader((H6 / 'existing_data/outcomes_and_claims.csv').open()))
    judges = [json.loads(line) for line in (H6 / 'full_1000/raw_judge_outputs.jsonl').read_text().splitlines()]
    by_id = {}
    for judge in judges:
        tid = judge['trace_id']
        if tid in by_id:
            raise ValueError(f'Duplicate judge trace_id {tid}')
        by_id[tid] = judge
    if {r['trace_id'] for r in answers} != set(by_id):
        raise ValueError('outcomes_and_claims.csv and raw_judge_outputs.jsonl trace_id sets differ')
    rows = []
    for row in answers:
        estimate = parse_estimate(row['estimate'])
        rows.append(dict(
            trace_id=row['trace_id'],
            model_dir=row['model_dir'],
            condition=row['condition'],
            row_i=int(row['row_i']),
            estimate=estimate,
            threshold=float(row['threshold']),
            claim=observed_label(by_id[row['trace_id']]),
        ))
    return rows


def select_model(rows, short):
    chosen = [r for r in rows if r['model_dir'].startswith(short)]
    dirs = sorted({r['model_dir'] for r in chosen})
    if len(dirs) != 1:
        raise ValueError(f'Expected one model_dir for {short}, got {dirs}')
    return chosen, dirs[0]


def metric_mask(records, metric):
    y = np.array([np.nan if r['estimate'] is None else r['estimate'] for r in records], float)
    threshold = np.array([r['threshold'] for r in records], float)
    if metric == 'log':
        valid = np.isfinite(y) & (y > 0)
        values = np.log(np.where(valid, y, 1.0))
    elif metric == 'binary':
        valid = np.isfinite(y)
        values = (y > threshold).astype(float)
    else:
        raise ValueError(metric)
    return values, valid


def usable_values(records, metric):
    values, valid = metric_mask(records, metric)
    return values[valid]


def bootstrap_mean(values, rng):
    n = len(values)
    if n == 0:
        return np.full(N_BOOT, np.nan)
    return values[rng.integers(n, size=(N_BOOT, n))].mean(axis=1)


def point_mean(values):
    return None if len(values) == 0 else float(values.mean())


def fmt_pct(x):
    return 'undefined' if x is None or not np.isfinite(x) else f'{100 * x:+.1f}%'


def fmt_pp(x):
    return 'undefined' if x is None or not np.isfinite(x) else f'{100 * x:+.1f} pp'


def fmt_ci_pct(low, high):
    if low is None or high is None:
        return 'CI withheld'
    return f'[{100 * low:+.1f}%, {100 * high:+.1f}%]'


def fmt_ci_pp(low, high):
    if low is None or high is None:
        return 'CI withheld'
    return f'[{100 * low:+.1f} pp, {100 * high:+.1f} pp]'


def includes_zero(row):
    low, high = row.get('ci95_low'), row.get('ci95_high')
    return low is None or high is None or low <= 0 <= high


def interpret(models_out):
    ds, qw = models_out['deepseek-v4-flash-0731'], models_out['qwen3p8-2p4t-a95b']
    ds_log, qw_log = ds['outcomes']['log'], qw['outcomes']['log']
    ds_bin, qw_bin = ds['outcomes']['binary'], qw['outcomes']['binary']

    def geom(block, stratum):
        row = block[stratum]['expm1']
        return f"{fmt_pct(row['estimate'])} {fmt_ci_pct(row['ci95_low'], row['ci95_high'])}"

    def paired_geom(block):
        row = block['positive_minus_negative']['expm1_difference']
        return f"{fmt_pct(row['estimate'])} {fmt_ci_pct(row['ci95_low'], row['ci95_high'])}"

    def paired_bin(block):
        row = block['positive_minus_negative']['rate_difference']
        return f"{fmt_pp(row['estimate'])} {fmt_ci_pp(row['ci95_low'], row['ci95_high'])}"

    qw_neg_caveat = (
        'but that interval includes zero'
        if includes_zero(qw_log['negative']['expm1'])
        else 'and the interval excludes zero'
    )
    s1 = (
        f"Deepseek-flash's label-negative stratum still shifts toward the donation-favorable "
        f"side ({geom(ds_log, 'negative')}) in the same direction as its label-positive stratum "
        f"({geom(ds_log, 'positive')}); qwen3p8's negative-stratum point estimate is also positive "
        f"({geom(qw_log, 'negative')}) {qw_neg_caveat}, while its label-positive stratum is "
        f"{geom(qw_log, 'positive')}."
    )
    paired_zero = all(includes_zero(block['positive_minus_negative'][key])
                      for block, key in ((ds_log, 'expm1_difference'), (qw_log, 'expm1_difference'),
                                         (ds_bin, 'rate_difference'), (qw_bin, 'rate_difference')))
    if paired_zero:
        s2 = (
            f"The paired within-model differences (label-positive minus label-negative, same "
            f"bootstrap replicate) include zero for both models and both outcomes (deepseek "
            f"geometric {paired_geom(ds_log)}, binary {paired_bin(ds_bin)}; qwen3p8 geometric "
            f"{paired_geom(qw_log)}, binary {paired_bin(qw_bin)}), so the impartiality label is "
            f"uninformative at the trace level within these models too."
        )
    else:
        s2 = (
            f"A paired positive-minus-negative interval excludes zero and is reported with its "
            f"direction (deepseek geometric {paired_geom(ds_log)}, binary {paired_bin(ds_bin)}; "
            f"qwen3p8 geometric {paired_geom(qw_log)}, binary {paired_bin(qw_bin)})."
        )
    s3 = (
        "This is the only place in the corpus where the impartiality label's diagnostic value "
        "can be tested against a substantial negative stratum rather than at ceiling; small "
        "strata mean wide intervals; do not over-interpret point differences whose paired "
        "interval spans zero."
    )
    return ' '.join((s1, s2, s3))


def analyze_model(short, threshold, rows):
    selected, model_dir = select_model(rows, short)
    observed_threshold = next(r['threshold'] for r in selected)
    if observed_threshold != float(threshold):
        raise ValueError(f'{short} threshold {observed_threshold} != {threshold}')
    exclusions = dict(n_selected=len(selected), n_below=0, n_above=0,
                      label_missing=0, label_missing_usable_y=0,
                      labeled_missing_y=0, usable_y=0)
    cells = {(c, s): [] for c in CONDITIONS for s in STRATA}
    usable_counts = {s: 0 for s in STRATA}
    for row in selected:
        if row['condition'] == 'below_good':
            exclusions['n_below'] += 1
        else:
            exclusions['n_above'] += 1
        y_ok = row['estimate'] is not None and row['estimate'] > 0
        if y_ok:
            exclusions['usable_y'] += 1
        if row['claim'] is None:
            exclusions['label_missing'] += 1
            if y_ok:
                exclusions['label_missing_usable_y'] += 1
            continue
        stratum = 'positive' if row['claim'] is True else 'negative'
        cells[(row['condition'], stratum)].append(row)
        if y_ok:
            usable_counts[stratum] += 1
        if row['estimate'] is None:
            exclusions['labeled_missing_y'] += 1
    if usable_counts != EXPECTED_USABLE[short]:
        raise ValueError(f'{short} usable-Y stratum counts {usable_counts} != {EXPECTED_USABLE[short]}')

    outcomes = {}
    failure_rows = []
    for metric in ('log', 'binary'):
        points, draws, ns = {}, {}, {}
        for stratum in STRATA:
            ns[stratum] = {}
            points[stratum] = {}
            draws[stratum] = {}
            for condition in CONDITIONS:
                group = cells[(condition, stratum)]
                values = usable_values(group, metric)
                ns[stratum][condition] = dict(
                    n_labeled=len(group),
                    n_usable=int(len(values)),
                )
                rng = cell_rng(short, condition, stratum)
                points[stratum][condition] = point_mean(values)
                draws[stratum][condition] = bootstrap_mean(values, rng)
            above_p, below_p = points[stratum]['above_good'], points[stratum]['below_good']
            contrast_point = None if above_p is None or below_p is None else above_p - below_p
            contrast_draws = draws[stratum]['above_good'] - draws[stratum]['below_good']
            extra = dict(
                n_below_good=ns[stratum]['below_good']['n_usable'],
                n_above_good=ns[stratum]['above_good']['n_usable'],
                n_labeled_below_good=ns[stratum]['below_good']['n_labeled'],
                n_labeled_above_good=ns[stratum]['above_good']['n_labeled'],
            )
            stratum_row = pack(contrast_point, contrast_draws, extra)
            if metric == 'log':
                geom_point = None if contrast_point is None else float(np.expm1(contrast_point))
                geom_draws = np.expm1(contrast_draws)
                stratum_row['mean_ln_y_difference'] = pack(contrast_point, contrast_draws)
                stratum_row['expm1'] = pack(geom_point, geom_draws)
            else:
                stratum_row['rate_difference'] = pack(contrast_point, contrast_draws)
            points[stratum]['contrast'] = contrast_point
            draws[stratum]['contrast'] = contrast_draws
            failure_rows.append(dict(
                model=short, outcome=metric, quantity=f'{stratum}_contrast',
                bootstrap_n=stratum_row['bootstrap_n'],
                bootstrap_undefined=stratum_row['bootstrap_undefined'],
                bootstrap_undefined_fraction=stratum_row['bootstrap_undefined_fraction'],
                interval_status=stratum_row['interval_status'],
                empty_cell_policy='Any empty contributing model×condition×stratum cell makes the replicate undefined; frequency reported; never silently dropped.',
            ))
            ns[stratum]['row'] = stratum_row
        pos_p, neg_p = points['positive']['contrast'], points['negative']['contrast']
        diff_point = None if pos_p is None or neg_p is None else pos_p - neg_p
        diff_draws = draws['positive']['contrast'] - draws['negative']['contrast']
        paired = pack(diff_point, diff_draws, dict(comparison='positive_minus_negative', pairing='same bootstrap replicate'))
        if metric == 'log':
            geom_pos = np.expm1(draws['positive']['contrast'])
            geom_neg = np.expm1(draws['negative']['contrast'])
            geom_diff_point = None if pos_p is None or neg_p is None else float(np.expm1(pos_p) - np.expm1(neg_p))
            paired['mean_ln_y_difference'] = pack(diff_point, diff_draws)
            paired['expm1_difference'] = pack(geom_diff_point, geom_pos - geom_neg)
            paired['note'] = (
                'Paired difference of condition contrasts on the same replicate. '
                'expm1_difference is (exp(Δ_pos)−1) − (exp(Δ_neg)−1), not expm1 of the log difference.'
            )
        else:
            paired['rate_difference'] = pack(diff_point, diff_draws)
            paired['note'] = 'Paired difference of P(Y>threshold) contrasts on the same replicate.'
        failure_rows.append(dict(
            model=short, outcome=metric, quantity='positive_minus_negative',
            bootstrap_n=paired['bootstrap_n'],
            bootstrap_undefined=paired['bootstrap_undefined'],
            bootstrap_undefined_fraction=paired['bootstrap_undefined_fraction'],
            interval_status=paired['interval_status'],
            empty_cell_policy='Any empty contributing model×condition×stratum cell makes the replicate undefined; frequency reported; never silently dropped.',
        ))
        outcomes[metric] = dict(
            positive=ns['positive']['row'],
            negative=ns['negative']['row'],
            positive_minus_negative=paired,
        )
    return dict(
        model=short,
        model_dir=model_dir,
        threshold=threshold,
        label_exclusions=exclusions,
        outcomes=outcomes,
    ), failure_rows


def flatten(models_out):
    table = []
    for short, block in models_out.items():
        for metric, outcome in block['outcomes'].items():
            for stratum, row in outcome.items():
                item = dict(model=short, model_dir=block['model_dir'], threshold=block['threshold'],
                            outcome=metric, stratum=stratum)
                for key in ('n_below_good', 'n_above_good', 'n_labeled_below_good', 'n_labeled_above_good',
                            'comparison', 'pairing', 'note'):
                    if key in row:
                        item[key] = row[key]
                if metric == 'log':
                    if stratum == 'positive_minus_negative':
                        item['mean_ln_y_difference'] = row['mean_ln_y_difference']
                        item['expm1_difference'] = row['expm1_difference']
                    else:
                        item['mean_ln_y_difference'] = row['mean_ln_y_difference']
                        item['expm1'] = row['expm1']
                else:
                    key = 'rate_difference' if 'rate_difference' in row else None
                    if key:
                        item[key] = row[key]
                item['bootstrap_n'] = row['bootstrap_n']
                item['bootstrap_undefined'] = row['bootstrap_undefined']
                item['bootstrap_undefined_fraction'] = row['bootstrap_undefined_fraction']
                item['interval_status'] = row['interval_status']
                table.append(item)
    return table


def main():
    rows = load_joined()
    models_out = {}
    failures = []
    for short, threshold in MODELS:
        block, fail = analyze_model(short, threshold, rows)
        models_out[short] = block
        failures.extend(fail)
    interpretation = interpret(models_out)
    payload = dict(
        title='H7 within-model impartiality-label stratum donation-direction contrasts',
        scope='Exactly deepseek-v4-flash-0731 and qwen3p8-2p4t-a95b; the only primary models with a substantial label-negative stratum.',
        no_external_calls=True,
        protocol=dict(
            seed=SEED,
            bootstrap_replicates=N_BOOT,
            resampling='Usable-Y records within model × condition × stratum (log: Y>0; binary: finite Y). Independent RNG streams per cell via SHA256(seed|stratum_negative_test|model|condition|stratum). Label-missing traces are excluded before resampling and counted.',
            contrast='above_good minus below_good',
            log_estimand='Difference in mean ln(Y) among Y>0; geometric shift exp(Δ)−1',
            binary_estimand='Difference in P(Y > model threshold) among finite Y; ties count as below',
            paired_difference='Label-positive contrast minus label-negative contrast, computed inside the same replicate',
            empty_cell_policy='Undefined point contrasts stay undefined. Any empty contributing cell makes that replicate undefined. Record frequencies. CI withheld if any replicate is undefined; conditional finite-replicate quantiles separately labeled. Never silently drop.',
            label_rule='parsed.impartiality_claim is a literal boolean and judge http_status=200 with finish_reason=stop; otherwise label-missing',
            sources=dict(
                answers='analysis/hyp6_impartiality/existing_data/outcomes_and_claims.csv',
                labels='analysis/hyp6_impartiality/full_1000/raw_judge_outputs.jsonl',
                join='trace_id',
            ),
        ),
        label_exclusions={short: block['label_exclusions'] for short, block in models_out.items()},
        models=models_out,
        table=flatten(models_out),
        replicate_failures=failures,
        interpretation_frame=INTERPRETATION_FRAME,
        interpretation=interpretation,
    )
    OUT.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(
        output=str(OUT.relative_to(ROOT)),
        label_exclusions=payload['label_exclusions'],
        replicate_failures=[{k: r[k] for k in ('model', 'outcome', 'quantity', 'bootstrap_undefined', 'interval_status')} for r in failures],
        interpretation=interpretation,
        table_preview=payload['table'],
    ), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
