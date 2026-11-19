"""Do automatic metrics see what human raters see?  Segment- and system-level meta-evaluation of chrF++, BLEU, BERTScore
and COMET against the human judgements of the two paired evaluations (Study 1: 2_J2_human_evaluation; Study 2: folder 25).
Writes meta_eval.json and prints a report."""
import os, re, json, math, random, collections, sys, statistics as stt
import openpyxl
from sacrebleu.metrics import CHRF, BLEU
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
NLG = os.path.join(HERE, '..', '..')
EXP = os.path.join(NLG, 'experiments')
DESK = os.path.join(os.path.expanduser('~'), 'Desktop', 'annotator_tasks')
chrf = CHRF(word_order=2); bleu = BLEU(effective_order=True)
num = lambda v: int(re.match(r'\s*(\d)', str(v)).group(1)) if v is not None and re.match(r'\s*(\d)', str(v)) else None
SURF = ('fluency', 'untranslated')

# ------------------------------------------------------------------ references and cached neural metrics
ITEMS = []; REF = {}
for d in ['tourism', 'health', 'geography']:
    for l in open(os.path.join(EXP, 'inputs', d + '.jsonl'), encoding='utf-8'):
        r = json.loads(l)
        if r['reference']:
            ITEMS.append((d, r['id'])); REF[(d, r['id'])] = r['reference']
IDX = {k: i for i, k in enumerate(ITEMS)}
CACHE = os.path.join(EXP, 'stats', 'semantic_cache')
def cached(metric, sysname):
    f = os.path.join(CACHE, '%s__%s.json' % (metric, sysname.replace(':', '__')))
    return json.load(open(f)) if os.path.exists(f) else None


def read_sheet(path):
    out = {}
    for r in list(openpyxl.load_workbook(path, data_only=True)['Items'].iter_rows(values_only=True))[1:]:
        if not isinstance(r[0], (int, float)): continue
        e = str(r[8] or '').strip().lower()
        sev = str(r[9] or '').strip().lower() if len(r) > 9 else ''
        out[int(r[0])] = dict(out=r[2], comp=num(r[3]), ad=num(r[6]), fl=num(r[7]), err=e, sev=sev)
    return out


def load_study(name, sheets, keyfile, sysmap):
    A, B = read_sheet(sheets[0]), read_sheet(sheets[1])
    KEY = {}
    for l in open(keyfile, encoding='utf-8').read().splitlines()[1:]:
        i, d, sid, s = l.split('\t'); KEY[int(i)] = (d, sid, s)
    rows = []
    for i, (d, sid, s) in KEY.items():
        if i not in A or i not in B: continue
        a, b = A[i], B[i]
        if None in (a['ad'], b['ad'], a['fl'], b['fl']) or not a['err'] or not b['err']: continue
        out = str(a['out'] or ''); ref = REF[(d, sid)]
        cs = cached('comet', sysmap.get(s, s)); bs = cached('bertscore', sysmap.get(s, s))
        mean_err = lambda e: bool(e) and not e.startswith('none') and not e.startswith(SURF)
        rows.append(dict(study=name, item=i, dom=d, sid=sid, sys=s, out=out, ref=ref,
                         ad=(a['ad'] + b['ad']) / 2, fl=(a['fl'] + b['fl']) / 2, comp=((a['comp'] or 0) + (b['comp'] or 0)) / 2,
                         ad1=a['ad'], ad2=b['ad'], fl1=a['fl'], fl2=b['fl'], err1=a['err'], err2=b['err'],
                         mean1=mean_err(a['err']), mean2=mean_err(b['err']),
                         hal1=a['err'].startswith('addition'), hal2=b['err'].startswith('addition'),
                         sev1=a['sev'], sev2=b['sev'],
                         chrf=chrf.sentence_score(out, [ref]).score, bleu=bleu.sentence_score(out, [ref]).score,
                         comet=cs[IDX[(d, sid)]] if cs else NEU.get('%s|%s|%s' % (s, d, sid), {}).get('comet'),
                         bert=bs[IDX[(d, sid)]] if bs else NEU.get('%s|%s|%s' % (s, d, sid), {}).get('bert')))
    return rows


NEU = json.load(open(os.path.join(HERE, 'study2_neural.json'))) if os.path.exists(os.path.join(HERE, 'study2_neural.json')) else {}


S1 = load_study('S1', [os.path.join(DESK, '2_J2_human_evaluation', 'annotator%d' % k, 'human_eval_A_annotator%d.xlsx' % k) for k in (1, 2)],
                os.path.join(EXP, 'human_eval', 'human_eval_A_KEY.tsv'), {})
S2 = load_study('S2', [os.path.join(DESK, '25_Human_evaluation_final', f) for f in ('human_eval_final_annotator1 dai.xlsx', 'human_eval_final_annotator2 dai.xlsx')],
                os.path.join(EXP, 'human_eval', 'human_eval_final_KEY.tsv'), {})
# MetricX-24 (newmetrics/score_metricx.py): an error score (lower is better); stored NEGATED so that, like the other
# metrics, higher means better in every analysis.  Tables convert it back to the native scale.
MX = os.path.join(HERE, 'newmetrics', 'metricx.json')
MXD = json.load(open(MX)) if os.path.exists(MX) else {}
for r in S1 + S2:
    v = MXD.get('%s|%s|%s' % (r['sys'], r['dom'], r['sid']))
    r['metricx'] = -v if v is not None else None


# ------------------------------------------------------------------ statistics
def rank(v):
    o = sorted(range(len(v)), key=lambda i: v[i]); r = [0.0] * len(v); i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[o[j + 1]] == v[o[i]]: j += 1
        for k in range(i, j + 1): r[o[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(x, y):
    mx, my = stt.mean(x), stt.mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x)); sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx and sy else float('nan')


def spearman(x, y): return pearson(rank(x), rank(y))


def kendall_b(x, y):
    n = len(x); c = d = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            a = (x[i] > x[j]) - (x[i] < x[j]); b = (y[i] > y[j]) - (y[i] < y[j])
            if a == 0 and b == 0: continue
            if a == 0: tx += 1
            elif b == 0: ty += 1
            elif a == b: c += 1
            else: d += 1
    den = math.sqrt((c + d + tx) * (c + d + ty))
    return (c - d) / den if den else float('nan')


def auc(pos, neg):
    """probability that a positive (error) gets a LOWER metric score than a negative (correct)"""
    if not pos or not neg: return float('nan')
    s = 0.0
    for p in pos:
        for q in neg: s += 1.0 if p < q else 0.5 if p == q else 0.0
    return s / (len(pos) * len(neg))


def boot_ci(fn, rows, n=1000, seed=7):
    rnd = random.Random(seed); sids = sorted({(r['dom'], r['sid']) for r in rows}); by = collections.defaultdict(list)
    for r in rows: by[(r['dom'], r['sid'])].append(r)
    v = []
    for _ in range(n):
        smp = [x for _ in sids for x in by[sids[rnd.randrange(len(sids))]]]
        v.append(fn(smp))
    v.sort(); return v[int(0.025 * n)], v[int(0.975 * n)]


METRICS = ['chrf', 'bleu', 'bert', 'comet', 'metricx']
R = {}
for name, rows in (('S1', S1), ('S2', S2)):
    res = dict(n=len(rows))
    have = {m: [r for r in rows if r[m] is not None] for m in METRICS}
    res['coverage'] = {m: len(v) for m, v in have.items()}
    # human ceiling: agreement of annotator 1 with annotator 2 on adequacy
    res['human_ceiling_kendall'] = round(kendall_b([r['ad1'] for r in rows], [r['ad2'] for r in rows]), 3)
    res['seg'] = {}
    for m in METRICS:
        v = have[m]
        if len(v) < 50: continue
        x = [r[m] for r in v]
        res['seg'][m] = dict(n=len(v), kendall_ad=round(kendall_b(x, [r['ad'] for r in v]), 3), spearman_ad=round(spearman(x, [r['ad'] for r in v]), 3),
                             kendall_fl=round(kendall_b(x, [r['fl'] for r in v]), 3),
                             auc_meaning_both=round(auc([r[m] for r in v if r['mean1'] and r['mean2']], [r[m] for r in v if r['err1'].startswith('none') and r['err2'].startswith('none')]), 3),
                             auc_halluc_both=round(auc([r[m] for r in v if r['hal1'] and r['hal2']], [r[m] for r in v if r['err1'].startswith('none') and r['err2'].startswith('none')]), 3),
                             auc_hidden=round(auc([r[m] for r in v if r['ad'] <= 3 and r['fl'] >= 4], [r[m] for r in v if r['ad'] >= 4.5 and r['fl'] >= 4]), 3),
                             ci_kendall_ad=[round(z, 3) for z in boot_ci(lambda s: kendall_b([r[m] for r in s], [r['ad'] for r in s]), v, n=200)])
    # system level
    syss = sorted({r['sys'] for r in rows})
    sysrow = {}
    for s in syss:
        v = [r for r in rows if r['sys'] == s]
        sysrow[s] = dict(n=len(v), ad=round(stt.mean(r['ad'] for r in v), 3), fl=round(stt.mean(r['fl'] for r in v), 3),
                         **{m: round(stt.mean(r[m] for r in v), 4) for m in METRICS if all(r[m] is not None for r in v)})
    res['systems'] = sysrow
    # faithful-and-correct outputs (both annotators adequacy 5): what do metrics give by input route?
    full = [r for r in rows if r['ad1'] == 5 and r['ad2'] == 5]
    res['perfect_by_route'] = {}
    for route in ('exp1', 'exp3', 'final'):
        v = [r for r in full if r['sys'].startswith(route) and 'google' not in r['sys'] and 'indictrans' not in r['sys']]
        if v: res['perfect_by_route'][route] = dict(n=len(v), **{m: round(stt.mean(r[m] for r in v), 4) for m in METRICS if all(r[m] is not None for r in v)})
    v = [r for r in full if 'google' in r['sys'] or 'indictrans' in r['sys']]
    res['perfect_by_route']['mt'] = dict(n=len(v), **{m: round(stt.mean(r[m] for r in v), 4) for m in METRICS if all(r[m] is not None for r in v)})
    # error types: mean metric of outputs whose main error (both annotators) is a given type, vs both-correct
    types = collections.Counter(r['err1'] for r in rows if r['err1'] == r['err2'])
    res['by_type'] = {}
    for t, c in types.most_common():
        if c < 8: continue
        v = [r for r in rows if r['err1'] == t and r['err2'] == t]
        res['by_type'][t] = dict(n=len(v), ad=round(stt.mean(r['ad'] for r in v), 2), **{m: round(stt.mean(r[m] for r in v), 4) for m in METRICS if all(r[m] is not None for r in v)})
    R[name] = res
json.dump(R, open(os.path.join(HERE, 'meta_eval.json'), 'w', encoding='utf-8'), indent=1)
json.dump([{k: v for k, v in r.items()} for r in S1 + S2], open(os.path.join(HERE, 'segments.json'), 'w', encoding='utf-8'), ensure_ascii=False)
for name in R:
    r = R[name]; print('=====', name, 'n', r['n'], 'coverage', r['coverage'], 'human ceiling tau', r['human_ceiling_kendall'])
    for m, v in r['seg'].items(): print('  ', m, v)
    print('  systems:'); [print('    %-30s %s' % (s, v)) for s, v in r['systems'].items()]
    print('  perfect (both ad=5) by route:', json.dumps(r['perfect_by_route']))
    print('  by error type:'); [print('    %-28s %s' % (t, v)) for t, v in r['by_type'].items()]
