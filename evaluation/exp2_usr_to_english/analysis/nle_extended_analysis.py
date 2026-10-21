#!/usr/bin/env python3
"""Extended analysis for the NLE (TALLIP) paper. No LLM is used; only the released outputs are read.

  python nle_extended_analysis.py   ->  nle_extended_results.json, nle_examples.txt

All routes are checked with the same layer checks (layered_analysis.py of Experiment 2):
  E2a/E2b/E2c   generation from the USR (outputs/*.tsv)
  DT            direct translation of the Hindi sentence (../exp1/outputs)
  CP            content-plan route: the LLM orders rule-generated chunks (../exp3/outputs)
Computed: 95% bootstrap confidence intervals, paired bootstrap tests (chrF++) and exact McNemar tests (flagged
outputs), results without the USRs changed after the run, cross-model agreement of errors, error profiles per model,
transitions between conditions, error rate by USR size, and example candidates for the error analysis."""
import collections, json, math, os, random, re, sys
import numpy as np
from sacrebleu.metrics import CHRF, BLEU
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
REL = os.path.join(os.path.expanduser('~'), 'Desktop', 'USR_Hindi_English_corpus_release', 'corpus')
SRC = open(os.path.join(HERE, 'layered_analysis.py'), encoding='utf-8').read().split('# ---------------- run ----------------')[0]
DOMS = ['tourism', 'health', 'geography']
MODELS = [('groq_gpt-oss-120b', 'gpt-oss-120b'), ('mistral_ministral-14b', 'Ministral 14B'), ('ollama_gemma3-4b', 'Gemma 3 4B')]
CONDS = [('_raw', 'E2a'), ('_guide', 'E2b'), ('_gloss', 'E2c')]


def load(path):
    o = {}
    for l in open(path, encoding='utf-8'):
        c = l.rstrip('\n').split('\t', 2)
        if len(c) == 3:
            o[(c[0], c[1])] = c[2]
    return o


RUNS = {}                                     # run name -> {(d,i): output}
for m, mn in MODELS:
    for c, cn in CONDS:
        RUNS['%s|%s' % (mn, cn)] = load(os.path.join(HERE, 'outputs', m + c + '.tsv'))
    RUNS['%s|DT' % mn] = load(os.path.join(HERE, '..', 'exp1', 'outputs', m + '.tsv'))
    RUNS['%s|CP' % mn] = load(os.path.join(HERE, '..', 'exp3', 'outputs', m + '.tsv'))
RUNS['Google Translate|DT'] = load(os.path.join(HERE, '..', 'exp1', 'outputs', 'google_translate.tsv'))
RUNS['IndicTrans2|DT'] = load(os.path.join(HERE, '..', 'exp1', 'outputs', 'indictrans2_local.tsv'))

keys, ref, hin, usr, res, nrows = [], {}, {}, {}, collections.defaultdict(dict), {}
NS = None
for d in DOMS:
    sys.argv = ['x', '--domain', d]
    ns = {'__file__': os.path.join(HERE, 'layered_analysis.py'), '__name__': 'la', '__doc__': ''}
    exec(SRC, ns)
    NS = ns
    for it in ns['items']:
        k = (d, it['id'])
        keys.append(k); ref[k] = it['reference']; hin[k] = ns['hindi'].get(it['id'], it['hindi']); usr[k] = it['usr']
        nrows[k] = len(ns['parse_usr'](it['usr'])[0])
        for r, o in RUNS.items():
            res[r][k] = ns['analyse'](it, hin[k], ref[k], o.get(k, ''))
ERR = NS['ERROR_TABS']
LAY = ['L1a Lexical & NE', 'L1b Cultural concepts', 'L1d Other sense used', 'L2 Morphology', 'L3 Semantic relations', 'L4 Discourse',
       "L5 Speaker's view", 'L6 Sentence type', 'L7 Adequacy', 'L8 Output form']
LEX = {'L1a Lexical & NE', 'L1b Cultural concepts', 'L1d Other sense used'}


def layers(r, k):
    s = {t for t, _, _ in res[r][k] if t in ERR}
    return {('Lexical' if t in LEX else t) for t in s}


def flagged(r, k):
    return bool(layers(r, k))


N = len(keys)
print('sentences', N)

# ---------------- changed USRs ----------------
rel = {}
for d in DOMS:
    for l in open(os.path.join(REL, d + '.jsonl'), encoding='utf-8'):
        j = json.loads(l); rel[(d, j['id'])] = j
norm = lambda u: '\n'.join(' '.join(x.split()) for x in u.strip().splitlines() if x.strip())
changed = {k for k in keys if norm(rel[k]['usr']) != norm(usr[k])}
refchanged = {k for k in keys if rel[k]['reference'].strip() != ref[k].strip()}
print('changed USRs', len(changed), 'changed references', len(refchanged))

# ---------------- scores, CIs, tests ----------------
chrf, bleu = CHRF(word_order=2), BLEU()
STATS = {}
for r, o in RUNS.items():
    hyp = [o.get(k, '') for k in keys]
    STATS[r] = np.array(chrf._extract_corpus_statistics(hyp, [[ref[k] for k in keys]]), dtype=float)
random.seed(1); rng = np.random.default_rng(1)
B = 2000
IDX = rng.integers(0, N, size=(B, N))


def chrf_of(st, idx=None):
    s = st if idx is None else st[idx]
    return chrf._compute_score_from_stats(list(s.sum(axis=0))).score


FL = {r: np.array([flagged(r, k) for k in keys], dtype=float) for r in RUNS}
out = {'n': N, 'changed_usrs': len(changed), 'changed_refs': len(refchanged), 'runs': {}, 'tests': [], 'robust': {}}
for r in RUNS:
    boots = [chrf_of(STATS[r], IDX[b]) for b in range(0, B, 4)]          # 500 resamples for the CI
    p = FL[r].mean()
    fb = FL[r][IDX[::4]].mean(axis=1)
    out['runs'][r] = dict(chrf=round(chrf_of(STATS[r]), 1), chrf_ci=[round(float(np.percentile(boots, 2.5)), 1), round(float(np.percentile(boots, 97.5)), 1)],
                          bleu=round(bleu.corpus_score([RUNS[r].get(k, '') for k in keys], [[ref[k] for k in keys]]).score, 1),
                          flagged=round(100 * p, 1), flagged_ci=[round(100 * float(np.percentile(fb, 2.5)), 1), round(100 * float(np.percentile(fb, 97.5)), 1)])
    print('%-26s chrF %5.1f [%5.1f,%5.1f]  flagged %5.1f%% [%5.1f,%5.1f]' % (r, out['runs'][r]['chrf'], *out['runs'][r]['chrf_ci'], out['runs'][r]['flagged'], *out['runs'][r]['flagged_ci']))


def mcnemar(a, b):
    n01 = int(((a == 1) & (b == 0)).sum()); n10 = int(((a == 0) & (b == 1)).sum()); n = n01 + n10
    if n == 0:
        return n01, n10, 1.0
    k = min(n01, n10)
    p = 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return n01, n10, min(1.0, p)


def test(a, b):
    sa, sb = STATS[a], STATS[b]
    d0 = chrf_of(sb) - chrf_of(sa)
    diffs = np.array([chrf_of(sb, IDX[i]) - chrf_of(sa, IDX[i]) for i in range(B)])
    p = min(1.0, 2 * min((diffs <= 0).mean(), (diffs >= 0).mean()))      # two-sided paired bootstrap
    n01, n10, pm = mcnemar(FL[a], FL[b])
    row = dict(a=a, b=b, chrf_diff=round(d0, 1), chrf_p=round(float(p), 4), fixed=n01, broken=n10, mcnemar_p=float('%.2g' % pm),
               flagged_diff=round(100 * (FL[b].mean() - FL[a].mean()), 1))
    out['tests'].append(row)
    print('%-24s -> %-24s chrF %+5.1f p=%.4f | flagged %+5.1f (fixed %d, new %d) McNemar p=%.2g' % (a, b, d0, p, row['flagged_diff'], n01, n10, pm))


for _, mn in MODELS:
    test(mn + '|E2a', mn + '|E2b'); test(mn + '|E2b', mn + '|E2c'); test(mn + '|E2a', mn + '|E2c')
    test(mn + '|E2c', mn + '|DT'); test(mn + '|E2c', mn + '|CP')
test('gpt-oss-120b|E2c', 'Ministral 14B|E2c'); test('Gemma 3 4B|E2c', 'Ministral 14B|E2c'); test('Gemma 3 4B|E2c', 'gpt-oss-120b|E2c')

# ---------------- robustness: without changed USRs ----------------
keep = np.array([k not in changed for k in keys])
for r in RUNS:
    st = STATS[r][keep]
    out['robust'][r] = dict(chrf=round(chrf_of(st), 1), flagged=round(100 * FL[r][keep].mean(), 1))
print('without changed USRs:', {r: v for r, v in out['robust'].items() if '|E2' in r})
# without the inputs whose gloss gives the verbalizer kara_1 the English 'hand' (see nle_gloss_check.py)
NL = chr(92) + 'n'
hand = set()
for l in open(os.path.join(HERE, 'exp2_input_gloss.tsv'), encoding='utf-8'):
    c = l.rstrip('\n').split('\t', 2)
    if any(r.startswith('kara_1=hand') for r in c[2].split(NL)):
        hand.add((c[0], c[1]))
keep2 = np.array([k not in hand for k in keys])
out['gloss_hand_inputs'] = len(hand)
out['robust_no_hand'] = {r: dict(chrf=round(chrf_of(STATS[r][keep2]), 1), flagged=round(100 * FL[r][keep2].mean(), 1)) for r in RUNS}
print('without kara_1=hand inputs (%d):' % len(hand), {r: v for r, v in out['robust_no_hand'].items() if '|E2c' in r})

# ---------------- layer counts with the same checks for all routes ----------------
LAYN = ['Lexical'] + LAY[3:]
out['layers'] = {r: {t: sum(1 for k in keys if t in layers(r, k)) for t in LAYN} for r in RUNS}

# ---------------- cross-model agreement per condition ----------------
out['cross'] = {}
for cn in ['E2a', 'E2b', 'E2c', 'DT', 'CP']:
    rs = ['%s|%s' % (mn, cn) for _, mn in MODELS]
    nfl = collections.Counter(sum(flagged(r, k) for r in rs) for k in keys)
    lay = {}
    for t in LAYN:
        c = collections.Counter(sum(t in layers(r, k) for r in rs) for k in keys)
        lay[t] = {'all3': c[3], 'two': c[2], 'one': c[1]}
    # unique: errors made by exactly one model, which model
    uniq = collections.Counter()
    for k in keys:
        for t in LAYN:
            who = [r for r in rs if t in layers(r, k)]
            if len(who) == 1:
                uniq[(who[0].split('|')[0], t)] += 1
    out['cross'][cn] = dict(none_flagged=nfl[0], all3_flagged=nfl[3], one=nfl[1], two=nfl[2], layers=lay,
                            unique={'%s / %s' % x: v for x, v in uniq.items()})
    print(cn, 'all three error-free', nfl[0], '| all three flagged', nfl[3], '| one', nfl[1], '| two', nfl[2])
    for t in LAYN:
        print('   %-22s all3 %4d  two %4d  one %4d' % (t, lay[t]['all3'], lay[t]['two'], lay[t]['one']))
# pairwise Jaccard of flagged sentence sets in E2c
out['jaccard_E2c'] = {}
for a in range(3):
    for b in range(a + 1, 3):
        ra, rb = '%s|E2c' % MODELS[a][1], '%s|E2c' % MODELS[b][1]
        A, Bs = {k for k in keys if flagged(ra, k)}, {k for k in keys if flagged(rb, k)}
        out['jaccard_E2c']['%s vs %s' % (MODELS[a][1], MODELS[b][1])] = round(len(A & Bs) / len(A | Bs), 3)
print('jaccard E2c', out['jaccard_E2c'])

# ---------------- error profiles: sub-types per run ----------------
prof = {}
for r in RUNS:
    c = collections.Counter()
    for k in keys:
        for sub in {(t, s) for t, s, _ in res[r][k] if t in ERR}:
            c[sub] += 1
    prof[r] = c
SUBS = sorted({s for r in prof for s in prof[r]})
out['subtypes'] = {r: {'%s :: %s' % s: prof[r][s] for s in SUBS if prof[r][s]} for r in RUNS}
print('\nSUB-TYPES (outputs) E2a/E2b/E2c per model')
for s in SUBS:
    vals = [prof['%s|%s' % (mn, cn)][s] for _, mn in MODELS for cn in ('E2a', 'E2b', 'E2c')]
    if max(vals) >= 15:
        print('%-60s' % ('%s :: %s' % s)[:60], ' '.join('%5d' % v for v in vals))

# ---------------- by USR size ----------------
bins = [(1, 5), (6, 8), (9, 11), (12, 15), (16, 99)]
out['by_size'] = {}
for lo, hi in bins:
    ks = [i for i, k in enumerate(keys) if lo <= nrows[k] <= hi]
    out['by_size']['%d-%d' % (lo, hi)] = dict(n=len(ks), **{r: round(100 * FL[r][ks].mean(), 1) for r in RUNS if '|E2c' in r or '|DT' in r or '|CP' in r})
print('by size', json.dumps(out['by_size']))

# ---------------- by domain (E2c) ----------------
out['by_domain'] = {}
for d in DOMS:
    ix = np.array([k[0] == d for k in keys])
    out['by_domain'][d] = {r: dict(chrf=round(chrf_of(STATS[r][ix]), 1), flagged=round(100 * FL[r][ix].mean(), 1)) for r in RUNS}

json.dump(out, open(os.path.join(HERE, 'nle_extended_results.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

# ---------------- example candidates ----------------
with open(os.path.join(HERE, 'nle_examples.txt'), 'w', encoding='utf-8') as f:
    def show(k, rs, tag):
        f.write('\n[%s] %s %s  (USR rows %d)\nHI : %s\nREF: %s\n' % (tag, k[0], k[1], nrows[k], hin[k], ref[k]))
        for r in rs:
            f.write('  %-22s %s\n      -> %s\n' % (r, RUNS[r].get(k, ''), '; '.join('%s: %s %s' % (t.split()[0], s, d) for t, s, d in res[r][k] if t in ERR)))
    short = [k for k in keys if len(ref[k].split()) <= 14 and k not in changed]
    for cn in ['E2c', 'E2a', 'E2b']:
        rs = ['%s|%s' % (mn, cn) for _, mn in MODELS]
        f.write('\n\n######## %s: all three error-free\n' % cn)
        for k in [k for k in short if not any(flagged(r, k) for r in rs)][:25]:
            show(k, rs, 'ALL OK')
        for t in LAYN:
            subs_all = [k for k in short if all(t in layers(r, k) for r in rs)]
            f.write('\n\n######## %s: all three fail layer %s (%d short)\n' % (cn, t, len(subs_all)))
            for k in subs_all[:12]:
                show(k, rs, 'ALL3 ' + t)
            for r in rs:
                only = [k for k in short if t in layers(r, k) and not any(t in layers(x, k) for x in rs if x != r)]
                f.write('\n######## %s: only %s fails layer %s (%d short)\n' % (cn, r, t, len(only)))
                for k in only[:6]:
                    show(k, rs, 'ONLY ' + r + ' ' + t)
print('written nle_extended_results.json, nle_examples.txt')
