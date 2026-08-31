"""Existing-data #5/#7 and rounding diagnostics. No network or model calls.

Retrospective descriptive analysis: the original generation schedule and missing
answers limit causal interpretation. Baseline regions are not inferred modes.
"""
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parent
FULL = OUT.parent/'full_1000'
REPO = OUT.parents[2]
SEED = 46062030
BOOTSTRAPS = 10000


def numeric_value_from_excerpt(excerpt):
    """Parse the first ordinary integer token from a reviewed visible excerpt."""
    tokens = re.findall(r'(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w.])', excerpt or '')
    if not tokens:
        raise AssertionError('visible answer excerpt contains no numeric token')
    token = tokens[0]
    if ',' in token and not re.fullmatch(r'\d{1,3}(?:,\d{3})+', token):
        raise AssertionError(f'malformed comma-grouped numeric token: {token}')
    return float(token.replace(',', ''))


def source_row(payload, row_i):
    """Resolve the recorded row key, never the list position."""
    return next((row for row in payload['rows'] if row.get('i') == row_i), None)


def regression_checks():
    assert numeric_value_from_excerpt('Estimate: **40,800,000**') == 40800000
    try:
        assert numeric_value_from_excerpt('40,800,000') == 40500000
    except AssertionError:
        pass
    else:
        raise AssertionError('wrong corrected value was accepted')
    assert source_row({'rows':[{'i':9},{'i':2}]}, 2)['i'] == 2


def save_csv(name, rows):
    with (OUT/name).open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def bootstrap_difference(below, above, rng, log=True):
    below, above = np.asarray(below,float), np.asarray(above,float)
    if log: below,above=np.log(below),np.log(above)
    estimate=float(above.mean()-below.mean())
    draws=above[rng.integers(len(above),size=(BOOTSTRAPS,len(above)))].mean(axis=1)-below[rng.integers(len(below),size=(BOOTSTRAPS,len(below)))].mean(axis=1)
    return estimate,np.quantile(draws,[.025,.975]).tolist(),draws


def main():
    regression_checks()
    correction_path=OUT/'answer_corrections.json'
    if not correction_path.exists():
        raise SystemExit('Wait for the source-grounded correction artifact before analysis.')
    corrections=json.loads(correction_path.read_text())
    # Artifact format is normalized by a small adapter once the audit is complete.
    if isinstance(corrections,dict): corrections=corrections['corrections']
    correction_map={r['trace_id']:r for r in corrections}
    selected=json.loads((FULL/'manifest.json').read_text())['selection']
    answers={r['trace_id']:r for r in csv.DictReader((FULL/'answer_only_extractions.csv').open())}
    judges={r['trace_id']:r for r in map(json.loads,(FULL/'raw_judge_outputs.jsonl').read_text().splitlines())}
    screen={r['trace_id']:r for r in map(json.loads,(FULL/'gap_screen.jsonl').read_text().splitlines())}
    sources, baselines, rows = {}, {}, []
    for item in selected:
        model=item['model_dir'];ident=item['trace_id'];condition=item['condition']
        path=REPO/'runs'/model/(condition+'.json')
        if path not in sources: sources[path]=json.loads(path.read_text())
        payload=sources[path]
        source=source_row(payload, item['row_i'])
        assert source is not None
        if model not in baselines:
            raw=json.loads((REPO/'runs'/model/'estimates.json').read_text())
            baseline=raw['baseline']
            values=[float(v) for v in baseline if type(v) in (int,float) and np.isfinite(v) and v>0]
            baselines[model]={'values':values,'n_total':len(baseline),'n_usable':len(values),'n_missing':len(baseline)-len(values),'quartiles':np.quantile(values,[.25,.5,.75]).tolist(),
                              'min':min(values),'max':max(values),
                              'exact_mode_count':max(Counter(values).values()),'n_unique':len(set(values))}
        value=float(answers[ident]['estimate']) if answers[ident]['estimate'] else None
        origin='existing_parser'
        if ident in correction_map:
            correction=correction_map[ident]
            assert item['row_i']==correction['row_i']
            assert hashlib.sha256(source['content'].encode()).hexdigest()==correction['source_content_sha256']
            excerpt=correction.get('visible_answer_excerpt', correction.get('exact_final_answer_quote'))
            assert excerpt and excerpt in source['content']
            parsed_value=numeric_value_from_excerpt(excerpt)
            assert parsed_value == float(correction['corrected_value']), (ident, parsed_value, correction['corrected_value'])
            value=correction['corrected_value']
            value=float(value) if value is not None else None
            origin='source_review_correction'
        if value is not None and (not np.isfinite(value) or value<=0): value=None
        judge=judges[ident];p=judge.get('parsed')
        claim=p.get('impartiality_claim') if isinstance(p,dict) else None
        if judge['http_status']!='200' or judge['finish_reason']!='stop' or type(claim) is not bool: claim=None
        b=baselines[model]
        region=None if value is None else ('below_baseline_range' if value<b['min'] else 'above_baseline_range' if value>b['max'] else f'region_{np.searchsorted(b["quartiles"],value,side="left")+1}')
        s=screen[ident];q=float(s['unique_visible_product']) if s['unique_visible_product'] else None
        wording=re.search(r'\bround(?:ed|ing)?\b',source.get('content') or '',re.I)
        rounding_gap=(value-q)/q if value is not None and q is not None and wording else None
        rows.append(dict(trace_id=ident,model_dir=model,condition=condition,row_i=item['row_i'],
            estimate=value,answer_source=origin,impartiality_commitment=claim,baseline_region=region,
            threshold=payload['threshold'],product=q,rounding_word_present=bool(wording),
            rounding_fractional_gap=rounding_gap,
            rounding_crosses_threshold=None if rounding_gap is None else ((value>payload['threshold'])!=(q>payload['threshold']))))
    rng=np.random.default_rng(SEED)
    comparisons, rounding, cells, bootstraps = [], [], [], []
    for model in sorted(baselines):
        groups={c:[r for r in rows if r['model_dir']==model and r['condition']==c] for c in ('below_good','above_good')}
        values={c:[r['estimate'] for r in group if r['estimate'] is not None] for c,group in groups.items()}
        d,ci,draws=bootstrap_difference(values['below_good'],values['above_good'],rng)
        bootstraps.append(draws)
        above_counts={c:sum(r['estimate'] is not None and r['estimate']>r['threshold'] for r in group) for c,group in groups.items()}
        missing={c:len(group)-len(values[c]) for c,group in groups.items()}
        comparisons.append(dict(model_dir=model,n_below=len(values['below_good']),n_above=len(values['above_good']),
            median_below=float(np.median(values['below_good'])),median_above=float(np.median(values['above_good'])),
            log_mean_difference=d,geometric_mean_shift_pct=100*np.expm1(d),ci_low_pct=100*np.expm1(ci[0]),ci_high_pct=100*np.expm1(ci[1]),
            commitments_below=sum(r['impartiality_commitment'] is True for r in groups['below_good']),
            commitments_above=sum(r['impartiality_commitment'] is True for r in groups['above_good']),
            claim_missing_below=sum(r['impartiality_commitment'] is None for r in groups['below_good']),
            claim_missing_above=sum(r['impartiality_commitment'] is None for r in groups['above_good']),
            above_threshold_below_good=above_counts['below_good'],above_threshold_above_good=above_counts['above_good'],
            above_threshold_rate_difference_lower_bound=(above_counts['above_good']-above_counts['below_good']-missing['below_good'])/50,
            above_threshold_rate_difference_upper_bound=(above_counts['above_good']+missing['above_good']-above_counts['below_good'])/50,
            quartile_threshold_dependence_note='Baseline q50 often equals the donation threshold; quartile-region composition is therefore not independent of threshold side.'))
        for c,group in groups.items():
            shares=Counter(r['baseline_region'] for r in group if r['baseline_region'] is not None)
            for region in ['below_baseline_range','region_1','region_2','region_3','region_4','above_baseline_range']:
                n_usable=len(values[c]); n_missing=len(group)-n_usable
                cells.append(dict(model_dir=model,condition=c,region=region,n=shares[region],share=(shares[region]/n_usable if n_usable else None),n_usable=n_usable,n_missing=n_missing))
            rounding_rows=[r for r in group if r['rounding_fractional_gap'] is not None]
            rounding.append(dict(model_dir=model,condition=c,n=len(rounding_rows),
                upward=sum(r['rounding_fractional_gap']>1e-12 for r in rounding_rows),
                downward=sum(r['rounding_fractional_gap']< -1e-12 for r in rounding_rows),
                unchanged=sum(abs(r['rounding_fractional_gap'])<=1e-12 for r in rounding_rows),
                crossing=sum(r['rounding_crosses_threshold'] for r in rounding_rows)))
    save_csv('outcomes_and_claims.csv',rows)
    save_csv('direction_comparisons.csv',comparisons)
    save_csv('baseline_region_shares.csv',cells)
    save_csv('rounding_screen_counts.csv',rounding)
    pooled=np.mean(bootstraps,axis=0)
    summary={'status':'exploratory_existing_data_analysis','seed':SEED,'bootstrap_resamples':BOOTSTRAPS,
        'n_selected':len(rows),'n_answers':sum(r['estimate'] is not None for r in rows),'n_corrections':len(correction_map),
        'equal_model_log_mean_difference':float(np.mean([r['log_mean_difference'] for r in comparisons])),
        'equal_model_ci_log':np.quantile(pooled,[.025,.975]).tolist(),
        'baseline_regions':{k:{a:v for a,v in b.items() if a!='values'} for k,b in baselines.items()},
        'limitations':[
            'Retrospective, not preregistered; bootstrap assumes independent exchangeable responses within each observed cell.',
            'Unresolved answers are excluded, not random by assumption. Original answer parsing is only partially source-audited.',
            'Per-model 95% intervals are marginal, not multiplicity-adjusted confirmatory tests.',
            'Compare all parseable responses without conditioning on post-treatment claim labels.',
            'The judge includes normative impartiality commitments, not only retrospective denials of actual influence.',
            'Baseline quartile regions describe familiar answer ranges, not verified modes or discrete internal choices; ties enter the lower region. Baseline q50 often equals the donation threshold, so quartile composition is not independent of threshold side.',
            'Missingness intervals are bounds on above-threshold answer rates only; they do not bound the log mean or geometric mean.',
            'Baseline estimates use existing original extraction, not a newly audited ground truth.',
            'Rounding counts are automated candidates requiring source review: one explicit product plus rounding wording does not establish final adoption.',
            'Upward and downward rounding are neither inherently faithful nor biased; omitted precision and starting-value composition can explain direction.',
            'No new generations, external API calls, or intervention; cannot uniquely identify moral intent or causal CoT unfaithfulness.'
        ]}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ('n_selected','n_answers','n_corrections','equal_model_log_mean_difference','equal_model_ci_log')},indent=2))


if __name__=='__main__': main()
