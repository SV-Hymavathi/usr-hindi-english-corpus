"""Study 2 of J2: the same design on 150 new sentences (Desktop/annotator_tasks/25_Human_evaluation_final), with the refined
prompt (v6b_few) and the final chunks. Same definitions as j2_stats.py. Output: study2_stats.json + printout."""
import os, re, json, math, random, collections, sys, openpyxl
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(os.path.expanduser('~'), 'Desktop', 'annotator_tasks', '25_Human_evaluation_final')
KEYF = os.path.join(HERE, '..', '..', 'experiments', 'human_eval', 'human_eval_final_KEY.tsv')
SURF = ('fluency', 'untranslated')
num = lambda v: int(re.match(r'\s*(\d)', str(v)).group(1)) if v is not None and re.match(r'\s*(\d)', str(v)) else None


def read(k):
    out = {}
    for r in list(openpyxl.load_workbook(os.path.join(D, {1: 'human_eval_final_annotator1 dai.xlsx', 2: 'human_eval_final_annotator2 dai.xlsx'}[k]), data_only=True)['Items'].iter_rows(values_only=True))[1:]:
        if not isinstance(r[0], (int, float)): continue
        e = str(r[8] or '').strip().lower()
        sev = str(r[9] or '').strip().lower()
        out[int(r[0])] = dict(comp=num(r[3]), ad=num(r[6]), fl=num(r[7]), err=e, sev=sev,
                              meaning=bool(e) and not e.startswith('none') and not e.startswith(SURF),
                              surface=e.startswith(SURF), halluc=e.startswith('addition'),
                              anyerr=bool(e) and not e.startswith('none'), serious=sev in ('major', 'critical'))
    return out


def binom_two_sided(b, c):
    n = b + c
    if n == 0: return 1.0
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)


def wilcoxon(d):
    d = [x for x in d if x != 0]; n = len(d)
    if n == 0: return 1.0
    a = sorted(range(n), key=lambda i: abs(d[i])); r = [0.0] * n; i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(d[a[j + 1]]) == abs(d[a[i]]): j += 1
        for k in range(i, j + 1): r[a[k]] = (i + j) / 2 + 1
        i = j + 1
    wp = sum(r[i] for i in range(n) if d[i] > 0); mu = n * (n + 1) / 4
    sd = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    return math.erfc(abs((wp - mu) / sd) / math.sqrt(2))


def qwk(x, y, q=5):
    n = len(x); O = collections.Counter(zip(x, y)); ra = collections.Counter(x); cb = collections.Counter(y)
    w = lambda i, j: (i - j) ** 2 / (q - 1) ** 2
    o = sum(w(i, j) * O[(i, j)] for i in range(1, 6) for j in range(1, 6)) / n
    e = sum(w(i, j) * ra[i] * cb[j] for i in range(1, 6) for j in range(1, 6)) / n / n
    return 1 - o / e


def ac2(x, y, q=5):
    pairs = list(zip(x, y)); n = len(pairs); w = lambda a, b: 1 - ((a - b) ** 2) / ((q - 1) ** 2)
    pa = sum(w(a, b) for a, b in pairs) / n
    pi = {k: (x.count(k) + y.count(k)) / (2 * n) for k in range(1, q + 1)}
    Tw = sum(w(k, l) for k in range(1, q + 1) for l in range(1, q + 1))
    pe = Tw / (q * (q - 1)) * sum(pi[k] * (1 - pi[k]) for k in pi)
    return (pa - pe) / (1 - pe)


def boot(diffs, n=10000, seed=1):
    rnd = random.Random(seed); m = len(diffs); s = []
    for _ in range(n):
        s.append(sum(diffs[rnd.randrange(m)] for _ in range(m)) / m)
    s.sort(); return s[int(0.025 * n)], s[int(0.975 * n)]


A, B = read(1), read(2)
KEY = {}
for l in open(KEYF, encoding='utf-8').read().splitlines()[1:]:
    i, d, sid, s = l.split('\t'); KEY[int(i)] = (d, sid, s)
full = [i for i in KEY if i in A and i in B and all(A[i][f] and B[i][f] for f in ('comp', 'ad', 'fl')) and A[i]['err'] and B[i]['err']]
R = dict(n_items=len(KEY), n_complete=len(full))
x = lambda f: [A[i][f] for i in full]; y = lambda f: [B[i][f] for i in full]
R['agreement'] = {f: dict(qwk=round(qwk(x(f), y(f)), 2), ac2=round(ac2(x(f), y(f)), 2),
                          exact=round(sum(a == b for a, b in zip(x(f), y(f))) / len(full), 2),
                          within1=round(sum(abs(a - b) <= 1 for a, b in zip(x(f), y(f))) / len(full), 2)) for f in ('comp', 'ad', 'fl')}
ORDER = ['exp1:google_translate', 'exp1:indictrans2_local', 'exp1:groq_gpt-oss-120b', 'final:groq_gpt-oss-120b',
         'exp1:ollama_gemma3-4b', 'final:ollama_gemma3-4b', 'exp1:mistral_ministral-14b', 'final:mistral_ministral-14b']
SYS = {}
for s in ORDER:
    its = [i for i in full if KEY[i][2] == s]; J = [A[i] for i in its] + [B[i] for i in its]; n = len(J)
    wrong = [j for j in J if j['ad'] <= 3]
    SYS[s] = dict(outputs=len(its), comp=round(sum(j['comp'] for j in J) / n, 2), ad=round(sum(j['ad'] for j in J) / n, 2),
                  fl=round(sum(j['fl'] for j in J) / n, 2), meaning=round(100 * sum(j['meaning'] for j in J) / n, 1),
                  halluc=round(100 * sum(j['halluc'] for j in J) / n, 1), surface=round(100 * sum(j['surface'] for j in J) / n, 1),
                  serious=round(100 * sum(j['serious'] for j in J) / n, 1),
                  visible=round(100 * sum(j['fl'] <= 3 for j in wrong) / len(wrong), 1) if wrong else None,
                  ad_a1=round(sum(A[i]['ad'] for i in its) / len(its), 2), ad_a2=round(sum(B[i]['ad'] for i in its) / len(its), 2))
R['systems'] = SYS
bys = {(KEY[i][0], KEY[i][1], KEY[i][2]): i for i in full}


def paired(s1, s2):
    sents = sorted({(d, sid) for (d, sid, s) in bys if s == s1} & {(d, sid) for (d, sid, s) in bys if s == s2})
    P = dict(n=len(sents))
    for lab, ann in (('ann1', [A]), ('ann2', [B])):
        X = ann[0]
        dif = [X[bys[(d, sid, s2)]]['ad'] - X[bys[(d, sid, s1)]]['ad'] for d, sid in sents]
        P['ad_' + lab] = dict(diff=round(sum(dif) / len(dif), 2), p=round(wilcoxon(dif), 4))
        for f in ('meaning', 'halluc', 'surface', 'serious'):
            b = sum(X[bys[(d, sid, s1)]][f] and not X[bys[(d, sid, s2)]][f] for d, sid in sents)
            c = sum(X[bys[(d, sid, s2)]][f] and not X[bys[(d, sid, s1)]][f] for d, sid in sents)
            P[f + '_' + lab] = dict(first_only=b, second_only=c, p=round(binom_two_sided(b, c), 4))
    mean2 = [((A[bys[(d, sid, s2)]]['ad'] + B[bys[(d, sid, s2)]]['ad']) - (A[bys[(d, sid, s1)]]['ad'] + B[bys[(d, sid, s1)]]['ad'])) / 2 for d, sid in sents]
    P['ad_mean_diff'] = round(sum(mean2) / len(mean2), 2); P['ad_ci'] = [round(v, 2) for v in boot(mean2)]
    return P


R['paired'] = {m: paired('exp1:' + m, 'final:' + m) for m in ('groq_gpt-oss-120b', 'ollama_gemma3-4b', 'mistral_ministral-14b')}
R['vs_google'] = {m: paired('exp1:google_translate', 'final:' + m) for m in ('groq_gpt-oss-120b',)}
R['vs_indictrans'] = {m: paired('exp1:indictrans2_local', 'final:' + m) for m in ('groq_gpt-oss-120b',)}
json.dump(R, open(os.path.join(HERE, 'study2_stats.json'), 'w', encoding='utf-8'), indent=1)
print('items', R['n_items'], 'complete', R['n_complete']); print(R['agreement'])
for s, v in SYS.items(): print('%-30s' % s, v)
for k, v in list(R['paired'].items()) + [('vsGT', R['vs_google']), ('vsIT2', R['vs_indictrans'])]: print(k, json.dumps(v))


def holm(ps):
    o = sorted(range(len(ps)), key=lambda i: ps[i]); m = len(ps); adj = [0] * m; run = 0
    for r, i in enumerate(o):
        run = max(run, min(1, (m - r) * ps[i])); adj[i] = run
    return adj


M = ('groq_gpt-oss-120b', 'ollama_gemma3-4b', 'mistral_ministral-14b')
X = {}
for m in M:
    s1, s2 = 'exp1:' + m, 'final:' + m
    sents = sorted({(d, sid) for (d, sid, s) in bys if s == s1} & {(d, sid) for (d, sid, s) in bys if s == s2})
    for f in ('ad', 'fl', 'comp'):
        dif = [((A[bys[(d, sid, s2)]][f] + B[bys[(d, sid, s2)]][f]) - (A[bys[(d, sid, s1)]][f] + B[bys[(d, sid, s1)]][f])) / 2 for d, sid in sents]
        X.setdefault(f, {})[m] = (round(sum(dif) / len(dif), 2), wilcoxon(dif))
    for lab, Y in (('a1', A), ('a2', B)):
        hid = lambda j: j['ad'] <= 3 and j['fl'] >= 4
        b = sum(hid(Y[bys[(d, sid, s1)]]) and not hid(Y[bys[(d, sid, s2)]]) for d, sid in sents)
        c = sum(hid(Y[bys[(d, sid, s2)]]) and not hid(Y[bys[(d, sid, s1)]]) for d, sid in sents)
        X.setdefault('hidden_' + lab, {})[m] = (b, c, binom_two_sided(b, c))
        for g in ('meaning', 'halluc', 'surface', 'serious'):
            v = R['paired'][m][g + '_ann' + lab[1]]
            X.setdefault(g + '_' + lab, {})[m] = (v['first_only'], v['second_only'], v['p'])
print('\nHOLM-corrected (3 models)')
for k, d in X.items():
    ps = [d[m][-1] for m in M]; adj = holm(ps)
    print('%-12s' % k, '  '.join('%s %s p=%.4f%s' % (m.split('_')[1][:8], d[m][:-1], a, '*' if a < 0.05 else '') for m, a in zip(M, adj)))
print('\nHIDDEN (% of judgements: adequacy<=3, fluency>=4)')
for s in ORDER:
    its = [i for i in full if KEY[i][2] == s]; J = [A[i] for i in its] + [B[i] for i in its]
    print('%-30s %.1f' % (s, 100 * sum(j['ad'] <= 3 and j['fl'] >= 4 for j in J) / len(J)))
def kap(x, y):
    n = len(x); po = sum(a == b for a, b in zip(x, y)) / n; ca = collections.Counter(x); cb = collections.Counter(y)
    pe = sum(ca[k] * cb[k] for k in set(x) | set(y)) / n / n; return (po - pe) / (1 - pe), po
def ac1(x, y):
    n = len(x); po = sum(a == b for a, b in zip(x, y)) / n; p = (sum(x) + sum(y)) / (2 * n); pe = 2 * p * (1 - p); return (po - pe) / (1 - pe)
for f in ('anyerr', 'meaning'):
    xa = [int(A[i][f]) for i in full]; xb = [int(B[i][f]) for i in full]; k, po = kap(xa, xb)
    print(f, 'kappa %.2f raw %.2f AC1 %.2f' % (k, po, ac1(xa, xb)))
k, po = kap([A[i]['err'] for i in full], [B[i]['err'] for i in full]); print('type kappa %.2f raw %.2f' % (k, po))
S1 = set((l.split('\t')[1], l.split('\t')[2]) for l in open(os.path.join(HERE, '..', '..', 'experiments', 'human_eval', 'human_eval_A_KEY.tsv'), encoding='utf-8').read().splitlines()[1:])
S2 = set((d, sid) for d, sid, s in KEY.values()); print('overlap with study 1:', len(S1 & S2), collections.Counter(d for d, s in S2))
