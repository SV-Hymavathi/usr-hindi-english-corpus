"""E2d (few-shot) against E2c (guide + gloss) on the same 250 USRs, for gpt-oss-120b and Ministral 14B, with the same
layer checks: chrF++, share of flagged outputs (paired bootstrap, McNemar), outputs flagged per layer, loss rate per
phenomenon. Output: nle_fewshot_results.json and a printed summary. No LLM is used."""
import collections, json, math, os, re, sys
import numpy as np
from sacrebleu.metrics import CHRF
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, 'layered_analysis.py'), encoding='utf-8').read().split('# ---------------- run ----------------')[0]
MODELS = [('groq_gpt-oss-120b', 'gpt-oss-120b'), ('mistral_ministral-14b', 'Ministral 14B')]
test = [tuple(l.rstrip('\n').split('\t')[:2]) for l in open(os.path.join(HERE, 'exp2_input_fewshot.tsv'), encoding='utf-8')]


def load(name):
    o = {}
    p = os.path.join(HERE, 'outputs', name + '.tsv')
    for l in open(p, encoding='utf-8'):
        c = l.rstrip('\n').split('\t', 2)
        if len(c) == 3:
            o[(c[0], c[1])] = c[2]
    return o


RUNS = {}
for f, m in MODELS:
    RUNS[m + '|E2c'] = load(f + '_gloss')
    RUNS[m + '|E2d'] = load(f + '_fewshot')
missing = {r: sum(1 for k in test if not RUNS[r].get(k, '').strip()) for r in RUNS}
print('missing or empty outputs on the 250:', missing)

res, opp, ref, keys = collections.defaultdict(dict), {}, {}, []
for d in ('tourism', 'health', 'geography'):
    sys.argv = ['x', '--domain', d]
    ns = {'__file__': os.path.join(HERE, 'layered_analysis.py'), '__name__': 'la', '__doc__': ''}
    exec(SRC, ns)
    ERR = ns['ERROR_TABS']
    for it in ns['items']:
        k = (d, it['id'])
        if k not in test:
            continue
        keys.append(k); ref[k] = it['reference']
        hin = ns['hindi'].get(it['id'], it['hindi'])
        opp[k] = ns['analyse'](it, hin, ref[k], 'zzz qqq')
        for r, o in RUNS.items():
            res[r][k] = ns['analyse'](it, hin, ref[k], o.get(k, ''))
LEX = {'L1a Lexical & NE', 'L1b Cultural concepts', 'L1d Other sense used'}
LAYN = ['Lexical', 'L2 Morphology', 'L3 Semantic relations', 'L4 Discourse', "L5 Speaker's view", 'L6 Sentence type', 'L7 Adequacy', 'L8 Output form']


def layers(r, k):
    return {('Lexical' if t in LEX else t) for t, _, _ in res[r][k] if t in ERR}


chrf = CHRF(word_order=2)
ST = {r: np.array(chrf._extract_corpus_statistics([RUNS[r].get(k, '') for k in keys], [[ref[k] for k in keys]]), dtype=float) for r in RUNS}
FL = {r: np.array([bool(layers(r, k)) for k in keys], dtype=float) for r in RUNS}
score = lambda st, idx=None: chrf._compute_score_from_stats(list((st if idx is None else st[idx]).sum(axis=0))).score
rng = np.random.default_rng(1); IDX = rng.integers(0, len(keys), size=(2000, len(keys)))

GROUPS = [('Names', r'^NE (dropped|replaced)'), ('Numbers', r'^number missing'), ('Modality', r'^modality'), ('Perfect aspect', r'^aspect \(perfect'),
          ('Passive voice', r'^voice \(passive'), ('Negation', r'^negation lost'), ('Purpose (rt)', r'relation rt '), ('Cause (rh)', r'relation rh '),
          ('Connectives', r'^connective missing'), ('Particles', r'^particle '), ('Deixis', r'^deixis'), ('Questions', r'^question -> statement')]
has = lambda R, pat: any(re.search(pat, s) for t, s, d in R)
out = {'n': len(keys), 'missing': missing, 'models': {}}
for _, m in MODELS:
    a, b = m + '|E2c', m + '|E2d'
    d0 = score(ST[b]) - score(ST[a])
    diffs = np.array([score(ST[b], IDX[i]) - score(ST[a], IDX[i]) for i in range(2000)])
    p_b = min(1.0, 2 * min((diffs <= 0).mean(), (diffs >= 0).mean()))
    n01 = int(((FL[a] == 1) & (FL[b] == 0)).sum()); n10 = int(((FL[a] == 0) & (FL[b] == 1)).sum())
    p_m = min(1.0, 2 * sum(math.comb(n01 + n10, i) for i in range(min(n01, n10) + 1)) / 2 ** (n01 + n10)) if n01 + n10 else 1.0
    lay = {r: {t: sum(1 for k in keys if t in layers(r, k)) for t in LAYN} for r in (a, b)}
    phen = {}
    for name, pat in GROUPS:
        ks = [k for k in keys if has(opp[k], pat)]
        if ks:
            phen[name] = dict(n=len(ks), E2c=round(100 * sum(has(res[a][k], pat) for k in ks) / len(ks), 1),
                              E2d=round(100 * sum(has(res[b][k], pat) for k in ks) / len(ks), 1))
    out['models'][m] = dict(chrf_E2c=round(score(ST[a]), 1), chrf_E2d=round(score(ST[b]), 1), chrf_diff=round(d0, 1), chrf_p=round(float(p_b), 4),
                            flagged_E2c=round(100 * FL[a].mean(), 1), flagged_E2d=round(100 * FL[b].mean(), 1), fixed=n01, new=n10,
                            mcnemar_p=float('%.2g' % p_m), layers=lay, phenomena=phen)
    print('\n== %s on %d USRs' % (m, len(keys)))
    print('chrF++ E2c %.1f -> E2d %.1f (%+.1f, p=%.4f) | flagged %.1f%% -> %.1f%% (fixed %d, new %d, McNemar p=%.2g)' % (
        score(ST[a]), score(ST[b]), d0, p_b, 100 * FL[a].mean(), 100 * FL[b].mean(), n01, n10, p_m))
    for t in LAYN:
        print('   %-22s %4d -> %4d' % (t, lay[a][t], lay[b][t]))
    for name, v in phen.items():
        print('   loss %-16s n=%3d  %5.1f%% -> %5.1f%%' % (name, v['n'], v['E2c'], v['E2d']))
json.dump(out, open(os.path.join(HERE, 'nle_fewshot_results.json'), 'w', encoding='utf-8'), indent=1)
print('\nwritten nle_fewshot_results.json')
