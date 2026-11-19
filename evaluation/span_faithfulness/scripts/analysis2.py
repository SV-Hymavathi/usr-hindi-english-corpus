"""Paper 2, further analyses: cost of each span type on the scores, fluent-but-unfaithful outputs, annotators' error labels
and severity of outputs with spans, domains, sentence length, Holm correction of the paired tests. Writes analysis2.json."""
import csv, json, os, re, sys, random, collections, statistics as st, math
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
R = list(csv.DictReader(open(os.path.join(HERE, '..', '..', 'human_evaluation_study2', 'ratings.tsv'), encoding='utf-8'), delimiter='\t'))
SRC = {}
for l in open(os.path.join(HERE, '..', '..', '..', 'data', 'exp1_input.tsv'), encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) == 3: SRC[(p[0], p[1])] = p[2]
num = lambda v: min(3, int(re.match(r'\s*(\d+)', v).group(1))) if re.match(r'\s*(\d+)', v or '') else 0
K = ('missing', 'added', 'wrong')
GROUP = lambda r: 'MT' if r['system'] in ('google_translate', 'indictrans2') else ('LLM from USR' if r['input'] == 'USR chunks' else 'LLM from Hindi')
GROUPS = ['MT', 'LLM from Hindi', 'LLM from USR']
OUT = {}

# 1. cost of one marked item on each score: per-annotator least squares, score ~ missing + added + wrong (counts capped at 3)
def ols(X, y):
    n, k = len(X), len(X[0])
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(X[i][a] * y[i] for i in range(n)) for a in range(k)]
    M = [row[:] + [v] for row, v in zip(XtX, Xty)]
    for c in range(k):
        p = max(range(c, k), key=lambda r: abs(M[r][c])); M[c], M[p] = M[p], M[c]
        for r in range(k):
            if r != c:
                f = M[r][c] / M[c][c]; M[r] = [a - f * b for a, b in zip(M[r], M[c])]
    return [M[i][k] / M[i][i] for i in range(k)]
cost = {}
for score in ('adequacy', 'comprehensibility', 'fluency'):
    X, y = [], []
    for r in R:
        for a in (1, 2):
            X.append([1.0] + [num(r['ann%d_%s_count' % (a, k)]) for k in K]); y.append(float(r['ann%d_%s' % (a, score)]))
    b = ols(X, y)
    # bootstrap over outputs for intervals
    rnd = random.Random(5); bs = []
    idx = list(range(len(R)))
    for _ in range(300):
        s = [idx[rnd.randrange(len(idx))] for _ in idx]
        Xs = [X[2 * i + a] for i in s for a in (0, 1)]; ys = [y[2 * i + a] for i in s for a in (0, 1)]
        bs.append(ols(Xs, ys))
    ci = [sorted(v[j] for v in bs) for j in range(4)]
    cost[score] = {'intercept': round(b[0], 2), **{k: [round(b[j + 1], 2), round(ci[j + 1][7], 2), round(ci[j + 1][292], 2)] for j, k in enumerate(K)}}
OUT['cost_per_item'] = cost

# 2. fluent but unfaithful: both annotators fluency >= 4 and at least one span type marked by both
both = lambda r, k: num(r['ann1_%s_count' % k]) > 0 and num(r['ann2_%s_count' % k]) > 0
fbu = {}
for g in GROUPS:
    v = [r for r in R if GROUP(r) == g]
    sp = [r for r in v if any(both(r, k) for k in K)]
    fl = [r for r in sp if float(r['ann1_fluency']) >= 4 and float(r['ann2_fluency']) >= 4]
    fbu[g] = dict(n=len(v), with_span=len(sp), fluent_with_span=len(fl), pct_of_span=round(100 * len(fl) / max(1, len(sp)), 1), pct_of_all=round(100 * len(fl) / len(v), 1))
OUT['fluent_but_unfaithful'] = fbu

# 3. annotators' own error label and severity on outputs where a span type is marked by both
lab = {}
for k in K:
    C = collections.Counter(); S = collections.Counter()
    for r in R:
        if both(r, k):
            for a in (1, 2): C[r['ann%d_error_type' % a]] += 1; S[r['ann%d_severity' % a]] += 1
    lab[k] = dict(labels=dict(C.most_common()), severity=dict(S.most_common()))
OUT['labels_by_span'] = lab
sev = {}
for g in GROUPS:
    S = collections.Counter()
    for r in R:
        if GROUP(r) == g and any(both(r, k) for k in K):
            for a in (1, 2): S[r['ann%d_severity' % a]] += 1
    sev[g] = dict(S.most_common())
OUT['severity_by_group'] = sev

# 4. domains and sentence length, by group: span types marked by both, per 100 outputs
dom = {}
for d in ('geography', 'health', 'tourism'):
    dom[d] = {g: {k: round(100 * st.mean(both(r, k) for r in R if GROUP(r) == g and r['domain'] == d), 1) for k in K} | {'n': sum(1 for r in R if GROUP(r) == g and r['domain'] == d)} for g in GROUPS}
OUT['domains'] = dom
L = {(r['domain'], r['id']): len(SRC.get((r['domain'], r['id']), '').split()) for r in R}
qs = sorted(set(L.values())); vals = sorted(L.values())
t1, t2 = vals[len(vals) // 3], vals[2 * len(vals) // 3]
band = lambda n: 'short' if n <= t1 else ('medium' if n <= t2 else 'long')
ln = {}
for b in ('short', 'medium', 'long'):
    ln[b] = {g: {k: round(100 * st.mean(both(r, k) for r in R if GROUP(r) == g and band(L[(r['domain'], r['id'])]) == b), 1) for k in K} for g in GROUPS}
OUT['length'] = dict(cut=[t1, t2], bands=ln)

# 5. Holm over the nine paired tests in spans.json
sp = json.load(open(os.path.join(HERE, '..', 'results', 'spans.json'), encoding='utf-8'))['paired']
tests = sorted(((v['p'], m, k) for m, P in sp.items() for k, v in P.items()))
holm, run = {}, 0.0
for i, (p, m, k) in enumerate(tests):
    run = max(run, min(1.0, (len(tests) - i) * p)); holm['%s|%s' % (m, k)] = round(run, 4)
OUT['holm'] = holm

# 6. group-level rates (any span of each type, marked by both) for a figure
OUT['group_rates'] = {g: {k: round(100 * st.mean(both(r, k) for r in R if GROUP(r) == g), 1) for k in K} for g in GROUPS}
json.dump(OUT, open(os.path.join(HERE, '..', 'results', 'analysis2.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
for k, v in OUT.items(): print('\n==', k, '\n', json.dumps(v, ensure_ascii=False)[:1500])
