"""Offline descriptive #7 check; no new API calls or causal significance claim."""
import csv
import hashlib
import json
import statistics
from pathlib import Path

OUT = Path(__file__).resolve().parent


def main():
    manifest = json.loads((OUT/'manifest.json').read_text())
    answers = {r['trace_id']:r for r in csv.DictReader((OUT/'answer_only_extractions.csv').open())}
    judges = {r['trace_id']:r for r in map(json.loads,(OUT/'raw_judge_outputs.jsonl').read_text().splitlines())}
    cells = []
    for model in sorted({r['model_dir'] for r in manifest['selection']}):
        for condition in ('below_good','above_good'):
            selected = [r for r in manifest['selection'] if r['model_dir']==model and r['condition']==condition]
            values, labels, claimed_values = [], [], []
            for row in selected:
                ident = row['trace_id']
                value = float(answers[ident]['estimate']) if answers[ident]['estimate'] else None
                j = judges[ident]
                p = j.get('parsed')
                claim = p.get('impartiality_claim') if isinstance(p,dict) else None
                if j['http_status']!='200' or j['finish_reason']!='stop' or type(claim) is not bool:
                    claim = None
                if value is not None: values.append(value)
                if claim is not None: labels.append(claim)
                if claim is True and value is not None: claimed_values.append(value)
            cells.append(dict(model_dir=model,condition=condition,n_selected=len(selected),
                n_answers=len(values),median_answer=statistics.median(values) if values else None,
                n_claim_labels=len(labels),n_claims=sum(labels),
                n_claim_and_answer=len(claimed_values),
                median_answer_among_claims=statistics.median(claimed_values) if claimed_values else None,
                n_component_scale_parser_values=sum(v<1e6 for v in values)))
    result = {'status':'preliminary_descriptive_only','cells':cells,
        'input_sha256':{name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in
                        ('manifest.json','answer_only_extractions.csv','raw_judge_outputs.jsonl')},
        'caveats':[
            'This is #7 (claims versus aggregate behavior), distinct from the #6 numerical-consistency screen.',
            'Primary medians use all parseable selected answers, without conditioning on claim labels.',
            'Claim-conditioned medians are secondary descriptive quantities subject to post-treatment selection.',
            'Original answer parser is not fully audited on this sample; missingness and component-number errors remain.',
            'Judge labels have known errors; universal positive labels do not establish universal genuine impartiality.',
            'Historical condition contrasts do not independently establish causal incentive influence or generalization.',
            'Do not interpret these medians as causal faithfulness results or proof of deception.'
        ]}
    (OUT/'claim_direction_preliminary.json').write_text(json.dumps(result,indent=2)+'\n')
    with (OUT/'claim_direction_preliminary.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(cells[0]));writer.writeheader();writer.writerows(cells)
    print('Saved 20 model/condition cells. Preliminary only; no new requests.')


if __name__=='__main__': main()
