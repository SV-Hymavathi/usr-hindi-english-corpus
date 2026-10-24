"""Experiment 2 analysis: per-domain statistics of the inputs (USR rows, reference length, layers present)."""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
tot = {}
for d in ('tourism', 'health', 'geography', 'ALL'):
    ds = ('tourism', 'health', 'geography') if d == 'ALL' else (d,)
    its = [json.loads(l) for x in ds for l in open(os.path.join(HERE, '..', 'inputs', x + '.jsonl'), encoding='utf-8')]
    rows, disc, spk, ne, num, cx, q = [], 0, 0, 0, 0, 0, 0
    for it in its:
        R = [l.split() for l in it['usr'].splitlines() if len(l.split()) >= 9 and re.fullmatch(r'\d+', l.split()[1])]
        rows.append(len(R))
        disc += any(':' in r[5] and not r[5].endswith('coref') for r in R)
        spk += any(r[6] != '-' for r in R)
        ne += any(r[0].startswith('[ne') for r in R)
        num += bool(re.search(r'[0-9०-९]', it['hindi']))
        cx += any(r[0].startswith('[') for r in R)
        q += 'interrogative' in it['usr']
    n = len(its)
    tot[d] = dict(n=n, rows=round(sum(rows) / n, 1), ref_words=round(sum(len(i['reference'].split()) for i in its) / n, 1),
                  discourse=disc, speaker=spk, names=ne, numbers=num, constructions=cx, questions=q)
    print(d, tot[d])
json.dump(tot, open(os.path.join(HERE, 'nle_data_stats.json'), 'w'), indent=1)
