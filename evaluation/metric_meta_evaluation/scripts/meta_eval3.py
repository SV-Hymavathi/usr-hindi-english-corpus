"""Confidence intervals and tests for the key contrasts, metric-vs-single-annotator agreement, and example candidates."""
import json, os, sys, math, random, collections, statistics as st
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
SEG = json.load(open(os.path.join(HERE, 'segments.json'), encoding='utf-8'))
M = ['chrf', 'bleu', 'bert', 'comet', 'metricx']
M = [m for m in M if all(r.get(m) is not None for r in SEG)]          # only metrics scored for every output
route =lambda s: 'mt' if ('google' in s or 'indictrans' in s) else ('hindi' if s.startswith('exp1') else 'usr')
model = lambda s: s.split(':')[1]


def kendall_b(x, y):
    c = d = tx = ty = 0; n = len(x)
    for i in range(n):
        for j in range(i + 1, n):
            a = (x[i] > x[j]) - (x[i] < x[j]); b = (y[i] > y[j]) - (y[i] < y[j])
            if a == 0 and b == 0: continue
            if a == 0: tx += 1
            elif b == 0: ty += 1
            elif a == b: c += 1
            else: d += 1
    den = math.sqrt((c + d + tx) * (c + d + ty)); return (c - d) / den if den else float('nan')


OUT = {}
rnd = random.Random(11)
for study in ('S1', 'S2'):
    rows = [r for r in SEG if r['study'] == study]
    by = collections.defaultdict(dict)
    for r in rows: by[(r['dom'], r['sid'])][r['sys']] = r
    sents = sorted(by)
    res = {}
    # metric vs each single annotator (comparable with the annotator-annotator ceiling)
    res['vs_single'] = {m: round((kendall_b([r[m] for r in rows], [r['ad1'] for r in rows]) + kendall_b([r[m] for r in rows], [r['ad2'] for r in rows])) / 2, 3) for m in M}
    res['ceiling'] = round(kendall_b([r['ad1'] for r in rows], [r['ad2'] for r in rows]), 3)

    # pairwise asymmetry with bootstrap over sentences: acc(USR better) - acc(Hindi better), same model
    def pair_list(S, m):
        L = []
        for mdl in {model(s) for s in S if route(s) != 'mt'}:
            h = [s for s in S if route(s) == 'hindi' and model(s) == mdl]; u = [s for s in S if route(s) == 'usr' and model(s) == mdl]
            if not h or not u: continue
            a, b = S[h[0]], S[u[0]]
            if a['ad'] == b['ad'] or a[m] == b[m]: continue
            usr_better = b['ad'] > a['ad']
            L.append((usr_better, (b[m] > a[m]) == usr_better))
        return L
    asym = {}
    for m in M:
        per = {s: pair_list(by[s], m) for s in sents}
        def stat(sample):
            ub = [ok for s in sample for (u, ok) in per[s] if u]; hb = [ok for s in sample for (u, ok) in per[s] if not u]
            return (sum(ub) / len(ub) if ub else float('nan')), (sum(hb) / len(hb) if hb else float('nan'))
        a_u, a_h = stat(sents); diffs = []
        for _ in range(2000):
            smp = [sents[rnd.randrange(len(sents))] for _ in sents]; x, y = stat(smp); diffs.append(y - x)
        diffs.sort()
        asym[m] = dict(acc_usr_better=round(a_u, 3), acc_hindi_better=round(a_h, 3), gap=round(a_h - a_u, 3),
                       ci=[round(diffs[50], 3), round(diffs[1949], 3)], p_one_sided=round(sum(d <= 0 for d in diffs) / len(diffs), 4))
    res['asymmetry'] = asym

    # paired route penalty at equal adequacy: same sentence, same model, both outputs rated identically by both annotators
    pen = {}
    for m in M:
        d = []
        for s in sents:
            S = by[s]
            for mdl in {model(x) for x in S if route(x) != 'mt'}:
                h = [x for x in S if route(x) == 'hindi' and model(x) == mdl]; u = [x for x in S if route(x) == 'usr' and model(x) == mdl]
                if h and u:
                    a, b = S[h[0]], S[u[0]]
                    if a['ad1'] == b['ad1'] and a['ad2'] == b['ad2'] and a['ad1'] == a['ad2']:
                        d.append((s, b[m] - a[m]))
        vals = [x for _, x in d]; bs = []
        for _ in range(2000):
            smp = [vals[rnd.randrange(len(vals))] for _ in vals]; bs.append(st.mean(smp))
        bs.sort()
        pen[m] = dict(n=len(vals), mean_usr_minus_hindi=round(st.mean(vals), 4), ci=[round(bs[50], 4), round(bs[1949], 4)],
                      share_usr_lower=round(sum(v < 0 for v in vals) / len(vals), 3))
    res['paired_equal_adequacy'] = pen
    res['_per'] = {m: {('%s|%s' % s): pair_list(by[s], m) for s in sents} for m in M}   # kept for the pooled test
    OUT[study] = res

# pooled test over both studies: bootstrap resamples sentences within each study (stratified)
pooled = {}
for m in M:
    P1, P2 = OUT['S1']['_per'][m], OUT['S2']['_per'][m]
    k1, k2 = list(P1), list(P2)
    def stat(s1, s2):
        L = [x for k in s1 for x in P1[k]] + [x for k in s2 for x in P2[k]]
        ub = [ok for u, ok in L if u]; hb = [ok for u, ok in L if not u]
        return sum(ub) / len(ub), sum(hb) / len(hb), len(ub), len(hb)
    a_u, a_h, nu, nh = stat(k1, k2); diffs = []
    for _ in range(4000):
        s1 = [k1[rnd.randrange(len(k1))] for _ in k1]; s2 = [k2[rnd.randrange(len(k2))] for _ in k2]
        x, y, _, _ = stat(s1, s2); diffs.append(y - x)
    diffs.sort()
    pooled[m] = dict(acc_usr_better=round(a_u, 3), acc_hindi_better=round(a_h, 3), gap=round(a_h - a_u, 3), n_usr_better=nu, n_hindi_better=nh,
                     ci=[round(diffs[100], 3), round(diffs[3899], 3)], p_one_sided=round(sum(d <= 0 for d in diffs) / len(diffs), 4))
for s in OUT: OUT[s].pop('_per')
OUT['pooled_asymmetry'] = pooled
json.dump(OUT, open(os.path.join(HERE, 'meta_eval3.json'), 'w', encoding='utf-8'), indent=1)
print('POOLED asymmetry:'); [print('  ', m, v) for m, v in pooled.items()]
for s, r in [(k, v) for k, v in OUT.items() if k in ('S1', 'S2')]:
    print('=====', s, 'ceiling', r['ceiling'], 'metric vs single annotator', r['vs_single'])
    for m, v in r['asymmetry'].items(): print('  asym', m, v)
    for m, v in r['paired_equal_adequacy'].items(): print('  equal-ad pairs', m, v)

# ---------------- example candidates
print('\n### fluent but wrong, high COMET (both annotators: meaning error, adequacy <= 3, fluency >= 4)')
c = [r for r in SEG if r['mean1'] and r['mean2'] and r['ad1'] <= 3 and r['ad2'] <= 3 and r['fl1'] >= 4 and r['fl2'] >= 4]
for r in sorted(c, key=lambda r: -r['comet'])[:14]:
    print('%s %s %s %s | ad %s/%s | comet %.3f bert %.3f chrf %.1f | %s / %s\n   REF %s\n   OUT %s' % (r['study'], r['dom'], r['sid'], r['sys'], r['ad1'], r['ad2'], r['comet'], r['bert'], r['chrf'], r['err1'], r['err2'], r['ref'], r['out']))
print('\n### faithful but underrated: USR route, both annotators adequacy 5 and no error, lowest COMET')
c = [r for r in SEG if route(r['sys']) == 'usr' and r['ad1'] == 5 and r['ad2'] == 5 and r['err1'].startswith('none') and r['err2'].startswith('none')]
for r in sorted(c, key=lambda r: r['comet'])[:14]:
    print('%s %s %s %s | comet %.3f bert %.3f chrf %.1f\n   REF %s\n   OUT %s' % (r['study'], r['dom'], r['sid'], r['sys'], r['comet'], r['bert'], r['chrf'], r['ref'], r['out']))
