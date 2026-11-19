"""Further analyses on segments.json (written by meta_eval.py):
(1) pairwise accuracy: same sentence, two outputs with different human adequacy -> does the metric prefer the better one?
    split by which route humans prefer (Hindi-input LLM vs USR route, same model);
(2) route penalty at equal adequacy: metric of USR-route minus Hindi-route outputs within each adequacy level;
(3) form vs meaning weight: standardized regression of the metric on adequacy and fluency;
(4) form-only vs meaning errors of equal human adequacy (Study 1 error types)."""
import json, os, sys, math, random, collections, statistics as st
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
SEG = json.load(open(os.path.join(HERE, 'segments.json'), encoding='utf-8'))
NEURAL = os.path.join(HERE, 'study2_neural.json')          # COMET/BERTScore of the Study 2 USR outputs, once computed
if os.path.exists(NEURAL):
    N = json.load(open(NEURAL, encoding='utf-8'))
    for r in SEG:
        k = '%s|%s|%s' % (r['sys'], r['dom'], r['sid'])
        if r['comet'] is None and k in N: r['comet'], r['bert'] = N[k]['comet'], N[k]['bert']
M = ['chrf', 'bleu', 'bert', 'comet', 'metricx']
route = lambda s: 'mt' if ('google' in s or 'indictrans' in s) else ('hindi' if s.startswith('exp1') else 'usr')
model = lambda s: s.split(':')[1]
OUT = {}
for study in ('S1', 'S2'):
    rows = [r for r in SEG if r['study'] == study]
    by = collections.defaultdict(dict)
    for r in rows: by[(r['dom'], r['sid'])][r['sys']] = r
    res = {}
    # (1) pairwise accuracy
    pa = {}
    for m in M:
        allp = [0, 0]; usrbetter = [0, 0]; hinbetter = [0, 0]; mtvsusr = [0, 0]
        for sent, S in by.items():
            ss = list(S)
            for i in range(len(ss)):
                for j in range(i + 1, len(ss)):
                    a, b = S[ss[i]], S[ss[j]]
                    if a[m] is None or b[m] is None or a['ad'] == b['ad']: continue
                    hum = a['ad'] > b['ad']; met = a[m] > b[m]
                    ok = int(hum == met) if a[m] != b[m] else 0
                    allp[0] += ok; allp[1] += 1
                    ra, rb = route(a['sys']), route(b['sys'])
                    if {ra, rb} == {'hindi', 'usr'} and model(a['sys']) == model(b['sys']):
                        better_usr = (a['ad'] > b['ad']) == (ra == 'usr')
                        tgt = usrbetter if better_usr else hinbetter
                        tgt[0] += ok; tgt[1] += 1
                    if {ra, rb} == {'mt', 'usr'}:
                        mtvsusr[0] += ok; mtvsusr[1] += 1
        f = lambda p: [round(p[0] / p[1], 3) if p[1] else None, p[1]]
        pa[m] = dict(all=f(allp), same_model_usr_better=f(usrbetter), same_model_hindi_better=f(hinbetter), mt_vs_usr=f(mtvsusr))
    res['pairwise'] = pa
    # (2) route penalty at equal adequacy (both annotators give the same adequacy value v)
    pen = {}
    for m in M:
        d = {}
        for v in (5, 4, 3):
            H = [r[m] for r in rows if r['ad1'] == v and r['ad2'] == v and route(r['sys']) == 'hindi' and r[m] is not None]
            U = [r[m] for r in rows if r['ad1'] == v and r['ad2'] == v and route(r['sys']) == 'usr' and r[m] is not None]
            T = [r[m] for r in rows if r['ad1'] == v and r['ad2'] == v and route(r['sys']) == 'mt' and r[m] is not None]
            if len(H) >= 10 and len(U) >= 10:
                d[v] = dict(hindi=round(st.mean(H), 4), usr=round(st.mean(U), 4), mt=round(st.mean(T), 4) if T else None, nH=len(H), nU=len(U), nT=len(T))
        pen[m] = d
    res['equal_adequacy'] = pen
    # (3) standardized regression metric ~ adequacy + fluency
    reg = {}
    for m in M:
        v = [r for r in rows if r[m] is not None]
        if len(v) < 50: continue
        z = lambda xs: [(x - st.mean(xs)) / st.pstdev(xs) for x in xs]
        y = z([r[m] for r in v]); a = z([r['ad'] for r in v]); f_ = z([r['fl'] for r in v])
        saa = sum(x * x for x in a); sff = sum(x * x for x in f_); saf = sum(x * w for x, w in zip(a, f_))
        say = sum(x * w for x, w in zip(a, y)); sfy = sum(x * w for x, w in zip(f_, y))
        det = saa * sff - saf * saf
        ba = (say * sff - sfy * saf) / det; bf = (sfy * saa - say * saf) / det
        reg[m] = dict(beta_adequacy=round(ba, 3), beta_fluency=round(bf, 3), fluency_share=round(bf / (ba + bf), 3), n=len(v))
    res['regression'] = reg
    # (4) form-only vs meaning errors with matched human adequacy (both annotators agree on the type)
    grp = {'form only (fluency/grammar)': lambda e: e.startswith('fluency'),
           'discourse/connective': lambda e: e.startswith('discourse'),
           'particle/deixis': lambda e: e.startswith('particle'),
           'named entity': lambda e: e.startswith('named'),
           'addition/hallucination': lambda e: e.startswith('addition'),
           'omission': lambda e: e.startswith('omission'),
           'mistranslation': lambda e: e.startswith('mistranslation'),
           'none (correct)': lambda e: e.startswith('none')}
    ty = {}
    for g, fn in grp.items():
        v = [r for r in rows if fn(r['err1']) and fn(r['err2'])]
        if len(v) >= 8:
            ty[g] = dict(n=len(v), ad=round(st.mean(r['ad'] for r in v), 2), fl=round(st.mean(r['fl'] for r in v), 2),
                         **{m: round(st.mean(r[m] for r in v), 4) for m in M if all(r[m] is not None for r in v)})
    res['types'] = ty
    OUT[study] = res
json.dump(OUT, open(os.path.join(HERE, 'meta_eval2.json'), 'w', encoding='utf-8'), indent=1)
for s, res in OUT.items():
    print('=====', s)
    print(' pairwise accuracy [acc, n]:'); [print('   ', m, v) for m, v in res['pairwise'].items()]
    print(' equal adequacy (mean metric hindi / usr / mt):'); [print('   ', m, v) for m, v in res['equal_adequacy'].items()]
    print(' regression:'); [print('   ', m, v) for m, v in res['regression'].items()]
    print(' types:'); [print('   %-30s %s' % (g, v)) for g, v in res['types'].items()]
