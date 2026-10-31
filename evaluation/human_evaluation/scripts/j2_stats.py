"""J2 statistics from the double-rated Format A sheets (1,200 outputs = 8 systems x the same 150 Hindi sentences, 50 per
domain).  usage: python j2_stats.py  -> j2_stats.json + printed tables
Per judgement each annotator gives comprehensibility (output alone, 1-5), adequacy (1-5), fluency (1-5) and one main error
type. Error types are grouped into meaning errors and surface errors (fluency/grammar only, untranslated/format).
Paired comparisons (same LLM, Hindi input vs USR-chunk input, same 150 sentences): exact McNemar per annotator and on the
pooled judgements (300 pairs); Wilcoxon signed-rank on the mean adequacy/fluency of the two annotators."""
import collections, json, math, os, re
import openpyxl
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.expanduser('~'), 'Desktop', 'annotator_tasks', '2_J2_human_evaluation')
KEYF = os.path.join(HERE, '..', '..', 'experiments', 'human_eval', 'human_eval_A_KEY.tsv')
num = lambda v: int(re.match(r'\s*(\d)', str(v)).group(1)) if v is not None and re.match(r'\s*(\d)', str(v)) else None
SURF = ('fluency', 'untranslated')
LLMS = [('groq_gpt-oss-120b', 'gpt-oss-120b'), ('ollama_gemma3-4b', 'Gemma 3 4B'), ('mistral_ministral-14b', 'Ministral 14B')]
NAME = {'exp1:google_translate': 'Google Translate', 'exp1:indictrans2_local': 'IndicTrans2'}
for k, n in LLMS: NAME['exp1:' + k] = n + ' (Hindi)'; NAME['exp3:' + k] = n + ' (USR)'


def read(k):
    f = os.path.join(SRC, 'annotator%d' % k, 'human_eval_A_annotator%d.xlsx' % k)
    out = {}
    for r in list(openpyxl.load_workbook(f, data_only=True)['Items'].iter_rows(values_only=True))[1:]:
        if r[0] is None: continue
        e = str(r[8] or '').strip().lower()
        out[int(r[0])] = dict(comp=num(r[3]), ad=num(r[6]), fl=num(r[7]), err=e,
                              meaning=bool(e) and not e.startswith('none') and not e.startswith(SURF),
                              surface=e.startswith(SURF), halluc=e.startswith('addition'), anyerr=bool(e) and not e.startswith('none'))
    return out


def binom_two_sided(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


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
    z = (wp - mu) / sd
    return math.erfc(abs(z) / math.sqrt(2))


def qwk(x, y, cats=(1, 2, 3, 4, 5)):
    m = len(cats); ix = {c: i for i, c in enumerate(cats)}; n = len(x)
    O = [[0] * m for _ in range(m)]
    for a, b in zip(x, y): O[ix[a]][ix[b]] += 1
    ra = [sum(O[i]) for i in range(m)]; cb = [sum(O[i][j] for i in range(m)) for j in range(m)]
    w = lambda i, j: (i - j) ** 2 / (m - 1) ** 2
    o = sum(w(i, j) * O[i][j] for i in range(m) for j in range(m)) / n
    e = sum(w(i, j) * ra[i] * cb[j] for i in range(m) for j in range(m)) / n / n
    return 1 - o / e


def kappa(x, y):
    n = len(x); cats = sorted(set(x) | set(y)); po = sum(a == b for a, b in zip(x, y)) / n
    pe = sum((x.count(c) / n) * (y.count(c) / n) for c in cats)
    return (po - pe) / (1 - pe)


def ac1(x, y):
    n = len(x); cats = sorted(set(x) | set(y)); q = len(cats); po = sum(a == b for a, b in zip(x, y)) / n
    pi = {c: (x.count(c) + y.count(c)) / (2 * n) for c in cats}
    pe = sum(p * (1 - p) for p in pi.values()) / (q - 1)
    return (po - pe) / (1 - pe)


def main():
    A, B = read(1), read(2)
    KEY = {}
    for l in list(open(KEYF, encoding='utf-8'))[1:]:
        i, d, sid, s = l.rstrip('\n').split('\t'); KEY[int(i)] = (d, sid, s)
    full = [i for i in KEY if all(A[i][f] is not None and B[i][f] is not None for f in ('comp', 'ad', 'fl')) and A[i]['err'] and B[i]['err']]
    R = dict(n_outputs=len(KEY), n_complete=len(full), n_sentences=len({KEY[i][1:2] + (KEY[i][0],) for i in KEY}))
    # agreement
    ag = {}
    for f in ('comp', 'ad', 'fl'):
        x, y = [A[i][f] for i in full], [B[i][f] for i in full]
        ag[f] = dict(qwk=round(qwk(x, y), 3), exact=round(sum(a == b for a, b in zip(x, y)) / len(full), 3),
                     within1=round(sum(abs(a - b) <= 1 for a, b in zip(x, y)) / len(full), 3))
    for f in ('anyerr', 'meaning'):
        x, y = [A[i][f] for i in full], [B[i][f] for i in full]
        ag[f] = dict(kappa=round(kappa(x, y), 3), ac1=round(ac1(x, y), 3), raw=round(sum(a == b for a, b in zip(x, y)) / len(full), 3))
    x, y = [A[i]['err'] for i in full], [B[i]['err'] for i in full]
    ag['type'] = dict(kappa=round(kappa(x, y), 3), raw=round(sum(a == b for a, b in zip(x, y)) / len(full), 3))
    R['agreement'] = ag
    # per system (judgements of both annotators pooled)
    sysrows = {}
    for scope in ('all', 'geography', 'health', 'tourism'):
        for s in NAME:
            its = [i for i in full if KEY[i][2] == s and (scope == 'all' or KEY[i][0] == scope)]
            J = [A[i] for i in its] + [B[i] for i in its]; n = len(J)
            wrong = [j for j in J if j['ad'] <= 3]
            types = collections.Counter(j['err'] for j in J if j['anyerr'])
            sysrows.setdefault(scope, {})[s] = dict(
                name=NAME[s], outputs=len(its), comp=round(sum(j['comp'] for j in J) / n, 2), ad=round(sum(j['ad'] for j in J) / n, 2),
                fl=round(sum(j['fl'] for j in J) / n, 2), anyerr=round(100 * sum(j['anyerr'] for j in J) / n, 1),
                meaning=round(100 * sum(j['meaning'] for j in J) / n, 1), surface=round(100 * sum(j['surface'] for j in J) / n, 1),
                halluc=round(100 * sum(j['halluc'] for j in J) / n, 1),
                fluent_wrong=round(100 * sum(j['fl'] >= 4 and j['ad'] <= 3 for j in J) / n, 1),
                visible=round(100 * sum(j['fl'] <= 3 for j in wrong) / len(wrong), 1) if wrong else None,
                n_wrong=len(wrong), top=types.most_common(4))
    R['systems'] = sysrows
    # paired comparisons: same LLM, Hindi vs USR, same sentence
    bysent = {(KEY[i][0], KEY[i][1], KEY[i][2]): i for i in full}
    pairs = {}
    for k, n in LLMS:
        sents = sorted({(d, sid) for (d, sid, s) in bysent if s == 'exp1:' + k} & {(d, sid) for (d, sid, s) in bysent if s == 'exp3:' + k})
        P = dict(n=len(sents))
        for f in ('meaning', 'halluc', 'surface', 'anyerr'):
            res = {}
            for lab, ann in (('ann1', [A]), ('ann2', [B]), ('pooled', [A, B])):
                b = c = 0
                for X in ann:
                    for d, sid in sents:
                        h, u = X[bysent[(d, sid, 'exp1:' + k)]][f], X[bysent[(d, sid, 'exp3:' + k)]][f]
                        b += h and not u; c += u and not h
                res[lab] = dict(hindi_only=b, usr_only=c, p=round(binom_two_sided(b, c), 4))
            P[f] = res
        # fluent-but-wrong: fluency >= 4 and adequacy <= 3 in the same judgement
        res = {}
        for lab, ann in (('ann1', [A]), ('ann2', [B]), ('pooled', [A, B])):
            b = c = 0
            for X in ann:
                for d, sid in sents:
                    h, u = X[bysent[(d, sid, 'exp1:' + k)]], X[bysent[(d, sid, 'exp3:' + k)]]
                    fh, fu = h['fl'] >= 4 and h['ad'] <= 3, u['fl'] >= 4 and u['ad'] <= 3
                    b += fh and not fu; c += fu and not fh
            res[lab] = dict(hindi_only=b, usr_only=c, p=round(binom_two_sided(b, c), 4))
        P['fluent_wrong'] = res
        for f in ('ad', 'fl', 'comp'):
            dd = [(A[bysent[(d, sid, 'exp3:' + k)]][f] + B[bysent[(d, sid, 'exp3:' + k)]][f]) / 2 -
                  (A[bysent[(d, sid, 'exp1:' + k)]][f] + B[bysent[(d, sid, 'exp1:' + k)]][f]) / 2 for d, sid in sents]
            P[f] = dict(mean_diff=round(sum(dd) / len(dd), 2), p=round(wilcoxon(dd), 4))
        pairs[n] = P
    R['paired'] = pairs
    json.dump(R, open(os.path.join(HERE, 'j2_stats.json'), 'w'), indent=1)
    print('outputs', R['n_outputs'], 'complete', R['n_complete'])
    print('agreement', json.dumps(ag))
    for s, v in R['systems']['all'].items():
        print('%-24s comp %.2f ad %.2f fl %.2f any %.1f mean %.1f surf %.1f hall %.1f flWrong %.1f visible %s' % (
            v['name'], v['comp'], v['ad'], v['fl'], v['anyerr'], v['meaning'], v['surface'], v['halluc'], v['fluent_wrong'], v['visible']))
    for n, P in pairs.items():
        print('==', n, 'n=%d' % P['n'])
        for f in ('meaning', 'halluc', 'surface', 'anyerr', 'fluent_wrong'): print('   ', f, P[f])
        for f in ('ad', 'fl', 'comp'): print('   ', f, P[f])
    for dom in ('geography', 'health', 'tourism'):
        print('--', dom)
        for s, v in R['systems'][dom].items():
            print('   %-24s ad %.2f fl %.2f mean %.1f surf %.1f hall %.1f' % (v['name'], v['ad'], v['fl'], v['meaning'], v['surface'], v['halluc']))


main()
