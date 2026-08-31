"""User-approved bounded retrieval amendment; freeze sample before adjudication."""
import json
import re

from prepare_h7 import OUT, LEXICON, PATTERNS, sha, save_json, write_jsonl


def main():
    h6 = [json.loads(s) for s in (OUT / 'h7_outcomes.jsonl').read_text().splitlines()]
    eligible = [r for r in h6 if r['claim'] is True and r['value_status'] == 'positive']
    broad = {r['source_id']: r for r in map(json.loads, (OUT / 'disclosure_hits.jsonl').read_text().splitlines())}
    hits = []
    for row in eligible:
        ident = row['source_id']
        if ident not in broad:
            continue
        text = (OUT / 'audit_texts' / f'{ident}.txt').read_text()
        assert sha(text) == row['reasoning_sha256']
        terms = list(re.finditer(LEXICON, text, re.I))
        pairs = []
        for hit in broad[ident]['hits']:
            near = [m for m in terms if m.end() > max(0, hit['start'] - 300) and m.start() < hit['end'] + 300]
            if near:
                pairs.append(dict(adjustment=hit, donation_terms=[dict(start=m.start(), end=m.end(), quote=m.group()) for m in near]))
        if pairs:
            hits.append(dict(source_id=ident, trace_id=row['trace_id'], model_dir=row['model_dir'],
                condition=row['condition'], row_i=row['row_i'], source_file=row['source_file'],
                reasoning_sha256=row['reasoning_sha256'], reasoning_characters=row['reasoning_characters'], pairs=pairs))
    ranked = sorted(hits, key=lambda r: sha('h7-bounded-disclosure-v1|' + r['trace_id']))
    sample = ranked[:40]
    packet = OUT / 'disclosure_blind'
    packet.mkdir(exist_ok=True)
    keys = []
    for i, row in enumerate(sample, 1):
        blind_id = f'D{i:02d}'
        text = (OUT / 'audit_texts' / f'{row["source_id"]}.txt').read_text()
        (packet / f'{blind_id}.txt').write_text(text)
        # Provide exact retrieval spans, but no source/condition/outcome metadata.
        save_json(packet / f'{blind_id}_hits.json', row['pairs'])
        keys.append(dict(blind_id=blind_id, **row))
    info = dict(amendment='User-approved bounded disclosure sample; replaces exhaustive-hit adjudication.',
        eligible_definition='H6 selected AND literal true impartiality label AND finite positive observed Y; all10models, primary9 reported separately.',
        n_eligible=len(eligible), n_broad_hits_in_eligible=sum(r['source_id'] in broad for r in eligible),
        n_cooccurrence_hits=len(hits), hit_rate=len(hits) / len(eligible), n_sampled=len(sample),
        sampled_characters=sum(r['reasoning_characters'] for r in sample),
        cooccurrence_window_characters=300, lexicon=LEXICON, patterns=PATTERNS,
        sample_rule='Lowest SHA256(h7-bounded-disclosure-v1|trace_id), cap40, no outcome/rationale-based prioritization.',
        intervals='Wilson approximate binomial95 for sampled hit-trace disclosure fraction; ignores finite population correction. If census, no sampling CI. Uncertain cases remain in denominator, confirmed+uncertain sensitivity separate.',
        limits='Nonhits and unsampled hits unadjudicated. No claim of exhaustive disclosure removal or population nondisclosure.',
        key_sha256=sha(json.dumps(keys, sort_keys=True)))
    protocol_path = OUT / 'bounded_disclosure_protocol.json'
    if protocol_path.exists():
        assert json.loads(protocol_path.read_text()) == info
    else:
        save_json(protocol_path, info)
    write_jsonl(OUT / 'bounded_disclosure_hits.jsonl', hits)
    save_json(OUT / 'disclosure_sample_key.json', keys)
    print(json.dumps({k: v for k, v in info.items() if k.startswith('n_') or k in ('hit_rate', 'sampled_characters')}, indent=2))


if __name__ == '__main__':
    main()
