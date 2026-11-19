"""Paper 3: LLM-as-judge (gpt-oss-120b and Qwen3.8 27B) against the 2,384 double-rated human judgements.
Writes judge_analysis.json. Run after run_judge.py has finished for both judges."""
import json, os, re, csv, sys, math, random, collections, statistics as st
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
SEG = json.load(open(os.path.join(HERE, '..', 'lre_metrics', 'segments.json'), encoding='utf-8'))
JUDGES = [j for j in ('gptoss', 'qwen', 'qwen_noref') if os.path.exists(os.path.join(HERE, 'judge_%s.jsonl' % j))]
if os.environ.get('JUDGES'): JUDGES = os.environ['JUDGES'].split(',')
J = {}
for j in JUDGES:
    J[j] = {}
    for l in open(os.path.join(HERE, 'judge_%s.jsonl' % j), encoding='utf-8'):
        d = json.loads(l); J[j][d['key']] = d
S2R = list(csv.DictReader(open(os.path.join(HERE, '..', 'lre_metrics', 'release', 'evaluation', 'human_evaluation_study2', 'ratings.tsv'), encoding='utf-8'), delimiter='\t'))
num = lambda v: min(3, int(re.match(r'\s*(\d+)', v).group(1))) if re.match(r'\s*(\d+)', v or '') else 0


def sysname(s):
    for k, v in (('google', 'Google Translate'), ('indictrans', 'IndicTrans2'), ('gpt-oss', 'gpt-oss-120b'), ('ollama', 'Gemma 3 4B'), ('gemma', 'Gemma 3 4B'), ('mistral', 'Ministral 14B')):
        if k in s: return v
    raise ValueError(s)
route = lambda s: 'Hindi' if s.startswith('exp1:') else 'USR'
TSVSYS = {'Google Translate': 'google_translate', 'IndicTrans2': 'indictrans2', 'gpt-oss-120b': 'gpt-oss-120b', 'Gemma 3 4B': 'gemma3-4b', 'Ministral 14B': 'ministral-14b'}
S2BY = {(r['domain'], r['id'], r['system'], 'Hindi' if r['input'] == 'Hindi sentence' else 'USR'): r for r in S2R}
rows = []
for r in SEG:
    k = '%s|%s|%s' % (r['sys'], r['dom'], r['sid'])
    d = dict(r); d['key'] = k; d['system'] = sysname(r['sys']); d['route'] = route(r['sys'])
    for j in JUDGES:
        if k in J[j]:
            d['j_' + j] = J[j][k]['adequacy']
            for f in ('added', 'omitted', 'changed'): d['j_%s_%s' % (j, f)] = J[j][k][f] == 'yes'
    if r['study'] == 'S2':
        t = S2BY[(r['dom'], r['sid'], TSVSYS[d['system']], d['route'])]
        for a in (1, 2):
            for kk, f in (('missing', 'omitted'), ('added', 'added'), ('wrong', 'changed')): d['h%d_%s' % (a, f)] = num(t['ann%d_%s_count' % (a, kk)]) > 0
    rows.append(d)
full = [r for r in rows if all('j_' + j in r for j in JUDGES)]
print('rows', len(rows), 'with all judges', len(full), 'judges', JUDGES)
TWO = 'gptoss' in JUDGES and 'qwen' in JUDGES
if TWO:
    for r in full: r['j_both'] = (r['j_gptoss'] + r['j_qwen']) / 2
JN = JUDGES + (['both'] if TWO else [])


# ------------------------------------------------------------ statistics helpers
def kendall_b(x, y):
    n = len(x); c = d = tx = ty = 0
    for i in range(n):
        for k in range(i + 1, n):
            a = (x[i] > x[k]) - (x[i] < x[k]); b = (y[i] > y[k]) - (y[i] < y[k])
            if a == 0 and b == 0: continue
            if a == 0: tx += 1
            elif b == 0: ty += 1
            elif a == b: c += 1
            else: d += 1
    return (c - d) / math.sqrt((c + d + tx) * (c + d + ty)) if (c + d + tx) and (c + d + ty) else 0.0


def qwk(a, b, k=5):
    a = [int(round(x)) for x in a]; b = [int(round(x)) for x in b]; n = len(a)
    O = [[0] * k for _ in range(k)]
    for x, y in zip(a, b): O[x - 1][y - 1] += 1
    ha = [sum(O[i]) for i in range(k)]; hb = [sum(O[i][j] for i in range(k)) for j in range(k)]
    num_ = sum(((i - j) ** 2 / (k - 1) ** 2) * O[i][j] for i in range(k) for j in range(k))
    den = sum(((i - j) ** 2 / (k - 1) ** 2) * ha[i] * hb[j] / n for i in range(k) for j in range(k))
    return 1 - num_ / den


def boot_ci(f, items, n=1000, seed=7):
    rnd = random.Random(seed); m = len(items); v = sorted(f([items[rnd.randrange(m)] for _ in range(m)]) for _ in range(n))
    return round(v[int(0.025 * n)], 3), round(v[int(0.975 * n)], 3)


def ac1(a, b):
    po = sum(x == y for x, y in zip(a, b)) / len(a); p = (sum(a) + sum(b)) / (2 * len(a)); pe = 2 * p * (1 - p)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def prf(pred, gold):
    tp = sum(p and g for p, g in zip(pred, gold)); fp = sum(p and not g for p, g in zip(pred, gold)); fn = sum(g and not p for p, g in zip(pred, gold))
    P = tp / (tp + fp) if tp + fp else 0; R = tp / (tp + fn) if tp + fn else 0
    return dict(precision=round(P, 3), recall=round(R, 3), f1=round(2 * P * R / (P + R), 3) if P + R else 0, flagged=sum(pred), gold=sum(gold))


OUT = {'n': len(full), 'judges': JUDGES}
# ------------------------------------------------------------ 1. segment-level agreement with humans
seg = {}
for st_ in ('S1', 'S2', 'all'):
    R = [r for r in full if st_ == 'all' or r['study'] == st_]
    hm = [r['ad'] for r in R]
    d = {'n': len(R), 'human_ann1_vs_ann2': dict(tau=round(kendall_b([r['ad1'] for r in R], [r['ad2'] for r in R]), 3), qwk=round(qwk([r['ad1'] for r in R], [r['ad2'] for r in R]), 3),
                                               exact=round(st.mean(r['ad1'] == r['ad2'] for r in R), 3), within1=round(st.mean(abs(r['ad1'] - r['ad2']) <= 1 for r in R), 3))}
    for j in JN:
        x = [r['j_' + j] for r in R]
        e = dict(tau_mean=round(kendall_b(x, hm), 3), tau_ann1=round(kendall_b(x, [r['ad1'] for r in R]), 3), tau_ann2=round(kendall_b(x, [r['ad2'] for r in R]), 3))
        if j != 'both':
            e.update(qwk_ann1=round(qwk(x, [r['ad1'] for r in R]), 3), qwk_ann2=round(qwk(x, [r['ad2'] for r in R]), 3),
                     exact_ann1=round(st.mean(a == r['ad1'] for a, r in zip(x, R)), 3), exact_ann2=round(st.mean(a == r['ad2'] for a, r in zip(x, R)), 3),
                     within1_any=round(st.mean(min(abs(a - r['ad1']), abs(a - r['ad2'])) <= 1 for a, r in zip(x, R)), 3),
                     mean_judge=round(st.mean(x), 3), mean_human=round(st.mean(hm), 3))
        d[j] = e
    for m in ('comet', 'metricx', 'chrf', 'bert'):
        d[m] = dict(tau_mean=round(kendall_b([r[m] for r in R], hm), 3))
    seg[st_] = d
OUT['segment'] = seg
# bootstrap CI for tau (all) for judges and comet / metricx
cis = {}
for j in JN + ['comet', 'metricx']:
    key = 'j_' + j if j in JN else j
    sub = full[:]
    cis[j] = boot_ci(lambda s: kendall_b([r[key] for r in s], [r['ad'] for r in s]), sub, n=200)
OUT['tau_ci_all'] = cis

# ------------------------------------------------------------ 2. error detection (added / omitted / changed)
det = {}
S2 = [r for r in full if r['study'] == 'S2']
for j in JUDGES:
    dj = {}
    for f in ('added', 'omitted', 'changed'):
        pred = [r['j_%s_%s' % (j, f)] for r in S2]
        both = [r['h1_' + f] and r['h2_' + f] for r in S2]
        either = [r['h1_' + f] or r['h2_' + f] for r in S2]
        dj[f] = dict(vs_both=prf(pred, both), vs_either=prf(pred, either), ac1_ann1=round(ac1(pred, [r['h1_' + f] for r in S2]), 3), ac1_ann2=round(ac1(pred, [r['h2_' + f] for r in S2]), 3))
    det[j] = dj
det['humans'] = {f: dict(ac1=round(ac1([r['h1_' + f] for r in S2], [r['h2_' + f] for r in S2]), 3), ann1=sum(r['h1_' + f] for r in S2), ann2=sum(r['h2_' + f] for r in S2)) for f in ('added', 'omitted', 'changed')}
OUT['detection_S2'] = det
# Study 1 has main error labels only: recall of the judge flags against them
lab = {'added': ('addition / hallucination',), 'omitted': ('omission',), 'changed': ('mistranslation', 'named entity', 'number', 'cultural concept')}
s1 = {}
S1 = [r for r in full if r['study'] == 'S1']
for j in JUDGES:
    s1[j] = {f: dict(recall_both=round(st.mean(r['j_%s_%s' % (j, f)] for r in S1 if r['err1'] in lab[f] and r['err2'] in lab[f]), 3),
                     n_both=sum(1 for r in S1 if r['err1'] in lab[f] and r['err2'] in lab[f]),
                     flag_rate_correct=round(st.mean(r['j_%s_%s' % (j, f)] for r in S1 if r['err1'] == 'none (correct)' and r['err2'] == 'none (correct)'), 3)) for f in lab}
OUT['detection_S1'] = s1

# ------------------------------------------------------------ 3. route: same model, same sentence
def pairs(R):
    by = {}
    for r in R:
        if r['system'] in ('Google Translate', 'IndicTrans2'): continue
        by.setdefault((r['study'], r['system'], r['dom'], r['sid']), {})[r['route']] = r
    return [(v['Hindi'], v['USR']) for v in by.values() if 'Hindi' in v and 'USR' in v]
rt = {}
for st_ in ('S1', 'S2'):
    P = pairs([r for r in full if r['study'] == st_])
    d = {'n_pairs': len(P)}
    for j in JN + ['comet', 'metricx']:
        key = 'j_' + j if j in JN else j
        sgn = lambda x: (x > 0) - (x < 0)
        res = {}
        for name, cond in (('usr_better', lambda h, u: u['ad'] > h['ad']), ('hindi_better', lambda h, u: h['ad'] > u['ad'])):
            sel = [(h, u) for h, u in P if cond(h, u)]
            agree = [sgn(u[key] - h[key]) == sgn(u['ad'] - h['ad']) for h, u in sel]
            ties = [u[key] == h[key] for h, u in sel]
            res[name] = dict(n=len(sel), agree=round(st.mean(agree), 3) if sel else None, ties=round(st.mean(ties), 3) if sel else None)
        res['human_equal_judge_prefers_hindi'] = round(st.mean(h[key] > u[key] for h, u in P if h['ad'] == u['ad']), 3)
        res['human_equal_judge_prefers_usr'] = round(st.mean(u[key] > h[key] for h, u in P if h['ad'] == u['ad']), 3)
        d[j] = res
    # mean difference USR - Hindi, human vs judge, per model
    per = {}
    for m in ('gpt-oss-120b', 'Gemma 3 4B', 'Ministral 14B'):
        Pm = [(h, u) for h, u in P if h['system'] == m]
        per[m] = {'human': round(st.mean(u['ad'] - h['ad'] for h, u in Pm), 3), **{j: round(st.mean(u['j_' + j] - h['j_' + j] for h, u in Pm), 3) for j in JN}}
    d['per_model_diff'] = per
    rt[st_] = d
OUT['route'] = rt

# ------------------------------------------------------------ 4. self-preference: judge minus human, own outputs vs others
sp = {}
for j in JUDGES:
    res = {}
    for st_ in ('S1', 'S2', 'all'):
        R = [r for r in full if st_ == 'all' or r['study'] == st_]
        g = collections.defaultdict(list)
        for r in R: g[r['system'] + '|' + r['route']].append(r['j_' + j] - r['ad'])
        res[st_] = {k: dict(n=len(v), resid=round(st.mean(v), 3)) for k, v in sorted(g.items())}
    sp[j] = res
OUT['residual_by_config'] = sp
# difference-in-differences: gpt-oss judge residual minus qwen judge residual, own (gpt-oss) vs other systems
if TWO:
    dd = {}
    for st_ in ('S1', 'S2', 'all'):
        R = [r for r in full if st_ == 'all' or r['study'] == st_]
        own = [r['j_gptoss'] - r['j_qwen'] for r in R if r['system'] == 'gpt-oss-120b']
        oth = [r['j_gptoss'] - r['j_qwen'] for r in R if r['system'] != 'gpt-oss-120b']
        rnd = random.Random(3); bs = []
        for _ in range(1000):
            a = [own[rnd.randrange(len(own))] for _ in own]; b = [oth[rnd.randrange(len(oth))] for _ in oth]; bs.append(st.mean(a) - st.mean(b))
        bs.sort()
        dd[st_] = dict(own=round(st.mean(own), 3), other=round(st.mean(oth), 3), diff=round(st.mean(own) - st.mean(oth), 3), ci=[round(bs[25], 3), round(bs[974], 3)])
    OUT['self_preference_did'] = dd

# ------------------------------------------------------------ 5. fluency leakage: does judge adequacy follow human fluency once human adequacy is fixed?
leak = {}
for j in JN:
    res = {}
    for a in (5.0, 4.5, 4.0, 3.5, 3.0):
        R = [r for r in full if r['ad'] == a]
        hi = [r['j_' + j] for r in R if r['fl'] >= 4.5]; lo = [r['j_' + j] for r in R if r['fl'] <= 3.5]
        if len(hi) >= 10 and len(lo) >= 10: res[str(a)] = dict(fluent=round(st.mean(hi), 2), n_fluent=len(hi), disfluent=round(st.mean(lo), 2), n_disfluent=len(lo))
    leak[j] = res
OUT['fluency_leak'] = leak
# fluent outputs with a meaning error (both annotators adequacy <= 3, fluency >= 4): what does the judge give?
fe = {}
R = [r for r in full if r['ad1'] <= 3 and r['ad2'] <= 3 and r['fl1'] >= 4 and r['fl2'] >= 4]
fe['n'] = len(R)
for j in JUDGES: fe[j] = dict(mean=round(st.mean(r['j_' + j] for r in R), 2), pct_ge4=round(100 * st.mean(r['j_' + j] >= 4 for r in R), 1))
for m in ('comet', 'metricx'):
    allv = sorted(r[m] for r in full); med = allv[len(allv) // 2]
    fe[m] = dict(pct_above_median=round(100 * st.mean(r[m] > med for r in R), 1))
OUT['fluent_errors'] = fe

# ------------------------------------------------------------ 6. system level
sysl = {}
for st_ in ('S1', 'S2'):
    R = [r for r in full if r['study'] == st_]
    g = collections.defaultdict(list)
    for r in R: g[r['system'] + '|' + r['route']].append(r)
    tab = {k: {'human': round(st.mean(r['ad'] for r in v), 3), **{j: round(st.mean(r['j_' + j] for r in v), 3) for j in JN}, 'comet': round(st.mean(r['comet'] for r in v), 4), 'metricx': round(st.mean(r['metricx'] for r in v), 3), 'n': len(v)} for k, v in g.items()}
    keys = sorted(tab)
    sysl[st_] = dict(table=tab, tau={j: round(kendall_b([tab[k][j] for k in keys], [tab[k]['human'] for k in keys]), 3) for j in JN + ['comet', 'metricx']})
OUT['system'] = sysl

# ------------------------------------------------------------ 7. selection: keep the output the judge prefers (same model, same sentence)
sel = {}
for st_ in ('S1', 'S2'):
    P = pairs([r for r in full if r['study'] == st_])
    d = {}
    def pick(key):
        ch = [(u if u[key] > h[key] else h) if u[key] != h[key] else h for h, u in P]   # ties: keep the Hindi output (default route)
        return dict(adequacy=round(st.mean(r['ad'] for r in ch), 3), meaning_error=round(100 * st.mean(r['ad1'] <= 3 or r['ad2'] <= 3 for r in ch), 1))
    d['always_hindi'] = dict(adequacy=round(st.mean(h['ad'] for h, u in P), 3), meaning_error=round(100 * st.mean(h['ad1'] <= 3 or h['ad2'] <= 3 for h, u in P), 1))
    d['always_usr'] = dict(adequacy=round(st.mean(u['ad'] for h, u in P), 3), meaning_error=round(100 * st.mean(u['ad1'] <= 3 or u['ad2'] <= 3 for h, u in P), 1))
    for j in JN + ['comet', 'metricx']: d['by_' + j] = pick('j_' + j if j in JN else j)
    d['by_humans'] = pick('ad')
    sel[st_] = d
OUT['selection'] = sel

# ------------------------------------------------------------ 8. reference anchoring: outputs that both annotators rate 5
low = lambda s: set(w.lower() for w in re.findall(r"[A-Za-z]+", s))
def name_off(r):   # a capitalised word (after the first) that the reference does not contain: typically a name spelled differently
    return any(w.lower() not in low(r['ref']) for w in re.findall(r"\b[A-Z][a-z]+\b", r['out'])[1:])
def novel(r):
    o = re.findall(r"[A-Za-z]+", r['out'].lower()); ref = low(r['ref']); return sum(w not in ref for w in o) / max(1, len(o))
anc = {}
P5 = [r for r in full if r['ad1'] == 5 and r['ad2'] == 5]
anc['n'] = len(P5)
for j in JUDGES:
    d = {}
    for rt_ in ('Hindi', 'USR'):
        for m in (False, True):
            v = [r['j_' + j] for r in P5 if r['route'] == rt_ and name_off(r) == m]
            d['%s|name_off=%s' % (rt_, m)] = dict(n=len(v), mean=round(st.mean(v), 2), le3=round(100 * st.mean(x <= 3 for x in v), 1))
        for lo, hi, nm in ((0, .2, 'low'), (.2, .4, 'mid'), (.4, 1.01, 'high')):
            v = [r['j_' + j] for r in P5 if r['route'] == rt_ and lo <= novel(r) < hi]
            d['%s|novel=%s' % (rt_, nm)] = dict(n=len(v), mean=round(st.mean(v), 2))
    anc[j] = d
OUT['anchoring'] = anc
json.dump(OUT, open(os.path.join(HERE, 'judge_analysis.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
for k, v in OUT.items():
    print('\n==', k); print(json.dumps(v, ensure_ascii=False)[:2500])
