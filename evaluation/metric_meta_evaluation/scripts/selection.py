"""What does a developer get by choosing with a metric?  For every sentence and model, two outputs exist (from the Hindi and
from the USR).  Choosing per sentence the output that a metric scores higher gives a set of outputs; its mean human adequacy,
share of meaning errors and of serious errors are compared with choosing always one route and with choosing by the annotators.
Writes selection.json."""
import json, os, sys, random, statistics as st
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
SEG = json.load(open(os.path.join(HERE, 'segments.json'), encoding='utf-8'))
M = ['chrf', 'bleu', 'bert', 'comet', 'metricx']
route = lambda s: 'mt' if ('google' in s or 'indictrans' in s) else ('hindi' if s.startswith('exp1') else 'usr')
OUT = {}
for study in ('S1', 'S2'):
    by = {}
    for r in SEG:
        if r['study'] != study or route(r['sys']) == 'mt': continue
        by.setdefault((r['dom'], r['sid'], r['sys'].split(':')[1]), {})[route(r['sys'])] = r
    pairs = [v for v in by.values() if 'hindi' in v and 'usr' in v]
    def summary(chosen):
        return dict(adequacy=round(st.mean(r['ad'] for r in chosen), 3),
                    meaning_error=round(100 * st.mean(r['mean1'] and r['mean2'] for r in chosen), 1),
                    any_meaning=round(100 * st.mean(r['mean1'] or r['mean2'] for r in chosen), 1),
                    serious=round(100 * st.mean(r['sev1'] in ('major', 'critical') and r['sev2'] in ('major', 'critical') for r in chosen), 1) if study == 'S2' else None,
                    usr_share=round(100 * st.mean(route(r['sys']) == 'usr' for r in chosen), 1))
    res = {'n_pairs': len(pairs), 'always_hindi': summary([p['hindi'] for p in pairs]), 'always_usr': summary([p['usr'] for p in pairs]),
           'humans': summary([p['usr'] if p['usr']['ad'] > p['hindi']['ad'] else p['hindi'] for p in pairs])}
    for m in M:
        res['by_' + m] = summary([p['usr'] if p['usr'][m] > p['hindi'][m] else p['hindi'] for p in pairs])
    OUT[study] = res
json.dump(OUT, open(os.path.join(HERE, 'selection.json'), 'w'), indent=1)
for s, r in OUT.items():
    print('=====', s, 'pairs', r['n_pairs'])
    for k, v in r.items():
        if k != 'n_pairs': print('  %-14s %s' % (k, v))
