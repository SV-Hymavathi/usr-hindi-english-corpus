"""Builds the tables of the J3 paper from the result files (no number is typed by hand):
  tab_agreement.tex   agreement of the two judgements per layer (round-1 overlap, round-2 re-judgement, pooled)
  tab_precision.tex   precision of the candidates with one judgement vs two judgements + adjudication, per layer
  tab_systems.tex     precision per system (two judgements)
  tab_rates.tex       error rates per phenomenon and system with Wilson intervals (double-judged labels)
  tab_causes.tex      causes of disagreement per layer (adjudication reasons)
and prints candidate examples per disagreement cause (for tab_examples, chosen by hand in make_j3_examples.py).
Inputs: ../bhasha/human_verification/{j3_final_labels.tsv, final_labels.tsv, verification_KEY.tsv, blind_recheck_*,
verification_annotator*_completed.xlsx, j3_disagreement_causes.json}, ../bhasha/j3_stats.json"""
import collections, json, math, os, re, sys
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
HV = os.path.join(HERE, '..', 'bhasha', 'human_verification')
OUT = os.path.join(HERE, 'tables'); os.makedirs(OUT, exist_ok=True)
LAY = [('L2', 'Morphology (TAM, number)'), ('L3', 'Semantic relations'), ('L4', 'Discourse connectives'),
       ("L5", "Speaker's view"), ('L6', 'Sentence type')]
SYSN = {'google_translate': 'Google Translate', 'indictrans2_local': 'IndicTrans2', 'groq_gpt-oss-120b': 'gpt-oss-120b',
        'ollama_gemma3-4b': 'Gemma 3 4B', 'mistral_ministral-14b': 'Ministral 14B'}
SYS = list(SYSN)
d1 = lambda s: int(re.match(r'\s*(\d)', str(s)).group(1)) if s is not None and re.match(r'\s*(\d)', str(s)) else None
f2 = lambda x: ('%.2f' % x).replace('-0.00', '0.00')


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def agree(ps):
    ps = [(a, b) for a, b in ps if a in (1, 2) and b in (1, 2)]; n = len(ps)
    po = sum(a == b for a, b in ps) / n; xa = [a for a, b in ps]; xb = [b for a, b in ps]
    pe = sum(xa.count(c) / n * xb.count(c) / n for c in (1, 2)); q = (xa.count(1) + xb.count(1)) / (2 * n); pg = 2 * q * (1 - q)
    return dict(n=n, raw=po, kappa=(po - pe) / (1 - pe) if pe < 1 else float('nan'), ac1=(po - pg) / (1 - pg) if pg < 1 else float('nan'))


K = {l.split('\t')[0]: l.rstrip('\n').split('\t') for l in list(open(os.path.join(HV, 'verification_KEY.tsv'), encoding='utf-8'))[1:]}
J = {r[0]: r for r in (l.rstrip('\n').split('\t') for l in list(open(os.path.join(HV, 'j3_final_labels.tsv'), encoding='utf-8'))[1:])}
BH = {l.split('\t')[0]: l.rstrip('\n').split('\t')[-1] for l in list(open(os.path.join(HV, 'final_labels.tsv'), encoding='utf-8'))[1:]}
A1 = {str(r[0]): d1(r[6]) for r in openpyxl.load_workbook(os.path.join(HV, 'verification_annotator1_completed.xlsx'))['Candidates'].iter_rows(min_row=2, values_only=True) if r[0]}
bk = dict(l.split()[:2] for l in list(open(os.path.join(HV, 'blind_recheck_KEY.tsv')))[1:])
BL = {bk[str(x[0])]: d1(x[6]) for x in openpyxl.load_workbook(os.path.join(HV, 'blind_recheck_filled.xlsx'))['Items'].iter_rows(min_row=2, values_only=True) if x[0]}
round1 = {i: (A1[i], BL[i]) for i in BL if i in J}
round2 = {i: (int(r[6]), int(r[7])) for i, r in J.items() if r[6] in ('1', '2') and r[7] in ('1', '2')}

# ---- agreement table
L = ['\\begin{tabular}{lrcccrccc}', '\\toprule',
     ' & \\multicolumn{4}{c}{Overlap, first round} & \\multicolumn{4}{c}{Blind re-judgement, second round} \\\\',
     '\\cmidrule(lr){2-5}\\cmidrule(lr){6-9}',
     'Layer & $n$ & Agr. & AC1 & $\\kappa$ & $n$ & Agr. & AC1 & $\\kappa$ \\\\', '\\midrule']
for code, name in LAY + [('ALL', 'All layers')]:
    if code == 'ALL': L.append('\\midrule')
    cells = []
    for R in (round1, round2):
        ps = [v for i, v in R.items() if code == 'ALL' or J[i][1] == code]
        a = agree(ps)
        cells += ['%d' % a['n'], f2(a['raw']), f2(a['ac1']) if not math.isnan(a['ac1']) else '--', f2(a['kappa']) if not math.isnan(a['kappa']) else '--']
    L.append('%s & %s \\\\' % (name, ' & '.join(cells)))
pool = agree(list(round1.values()) + list(round2.values()))
L += ['\\midrule', 'Both rounds pooled & \\multicolumn{8}{l}{$n=%d$, agreement %s, AC1 %s, $\\kappa$ %s} \\\\' % (pool['n'], f2(pool['raw']), f2(pool['ac1']), f2(pool['kappa'])),
      '\\bottomrule', '\\end{tabular}']
open(os.path.join(OUT, 'tab_agreement.tex'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
rate = lambda R, k: sum(v[k] == 1 for v in R.values()) / len(R)
json.dump(dict(round1=agree(list(round1.values())), round2=agree(list(round2.values())), pooled=pool,
               error_share=dict(r1_first=rate(round1, 0), r1_second=rate(round1, 1), r2_first=rate(round2, 0), r2_second=rate(round2, 1))),
          open(os.path.join(HERE, 'j3_agreement.json'), 'w'), indent=1)

# ---- precision: one judgement (the first) vs two judgements + adjudication, same candidates
L = ['\\begin{tabular}{lrcccc}', '\\toprule',
     'Layer & Candidates & \\multicolumn{2}{c}{One judgement} & \\multicolumn{2}{c}{Two judgements, adjudicated} \\\\',
     '\\cmidrule(lr){3-4}\\cmidrule(lr){5-6}', ' & & Confirmed & Precision & Confirmed & Precision \\\\', '\\midrule']
for code, name in LAY + [('ALL', 'All layers')]:
    if code == 'ALL': L.append('\\midrule')
    ids = [i for i, r in J.items() if r[8] in ('1', '2') and BH.get(i, '').isdigit() and (code == 'ALL' or r[1] == code)]
    c1 = sum(BH[i] == '1' for i in ids); c2 = sum(J[i][8] == '1' for i in ids); n = len(ids)
    lo1, hi1 = wilson(c1, n); lo2, hi2 = wilson(c2, n)
    L.append('%s & %d & %d & %s {\\scriptsize(%s--%s)} & %d & %s {\\scriptsize(%s--%s)} \\\\' % (
        name, n, c1, f2(c1 / n), f2(lo1), f2(hi1), c2, f2(c2 / n), f2(lo2), f2(hi2)))
L += ['\\bottomrule', '\\end{tabular}']
open(os.path.join(OUT, 'tab_precision.tex'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')

# ---- precision per system (two judgements)
L = ['\\begin{tabular}{lrrc}', '\\toprule', 'System & Candidates & Confirmed & Precision (95\\% CI) \\\\', '\\midrule']
for s in SYS:
    ids = [i for i, r in J.items() if r[8] in ('1', '2') and r[5] == s]
    c = sum(J[i][8] == '1' for i in ids); lo, hi = wilson(c, len(ids))
    L.append('%s & %d & %d & %s {\\scriptsize(%s--%s)} \\\\' % (SYSN[s], len(ids), c, f2(c / len(ids)), f2(lo), f2(hi)))
L += ['\\bottomrule', '\\end{tabular}']
open(os.path.join(OUT, 'tab_systems.tex'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')

# ---- error rates
st = json.load(open(os.path.join(HERE, '..', 'bhasha', 'j3_stats.json')))
GROUP = {'Tense': 'L2', 'Aspect': 'L2', 'Modality': 'L2', 'Plural lost': 'L2', 'Negation lost': 'L3', 'Negation added': 'L3',
         'Cause/purpose/without/like lost': 'L3', 'Connective missing': 'L4', 'Focus particle lost': 'L5',
         'Deixis lost or reversed': 'L5', 'Honorific dropped': 'L5', 'Question rendered as statement': 'L6'}
NAME = {'Cause/purpose/without/like lost': "Cause, purpose, `without'", 'Question rendered as statement': 'Question $\\rightarrow$ statement',
        'Deixis lost or reversed': 'Deixis lost or reversed'}
LN = dict(LAY); L = ['\\begin{tabular}{llrccccc}', '\\toprule', 'Layer & Error & $n$ & ' + ' & '.join(SYSN[s] for s in SYS) + ' \\\\', '\\midrule']
prev = None
for row in st['table']:
    lay = GROUP[row['label']]
    if prev and lay != prev: L.append('\\midrule')
    best = max(row['cells'][s]['rate'] for s in SYS)
    cells = []
    for s in SYS:
        c = row['cells'][s]; v = '%.1f' % c['rate']
        if c['rate'] == best and best > 0: v = '\\textbf{%s}' % v
        cells.append('%s {\\scriptsize(%.1f--%.1f)}' % (v, max(0, c['lo']), c['hi']))
    dag = '$^\\dagger$' if row['opp'] < 100 else ''
    L.append('%s & %s & %s%s & %s \\\\' % (LN[lay] if lay != prev else '', NAME.get(row['label'], row['label']), '{:,}'.format(row['opp']), dag, ' & '.join(cells)))
    prev = lay
L += ['\\bottomrule', '\\end{tabular}']
open(os.path.join(OUT, 'tab_rates.tex'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')

# ---- causes of disagreement
cz = json.load(open(os.path.join(HV, 'j3_disagreement_causes.json'), encoding='utf-8'))
CAUSES = [('other_form', 'Meaning expressed by another form'), ('lost', 'Device lost'), ('not_source', 'Device not in the Hindi sentence'),
          ('context', 'Context needed or source ambiguous'), ('other', 'Other'), ('no reason', 'No reason recorded')]
LAYNAME = {'Morphology (tense, aspect, modality, number)': 'L2', 'Semantic relations (voice, negation, cause/purpose/without/like)': 'L3',
           'Discourse connective': 'L4', "Speaker's view (particles hI/bhI, deixis, honorific)": 'L5', 'Sentence type': 'L6'}
L = ['\\begin{tabular}{l' + 'r' * 5 + 'rr}', '\\toprule', 'Cause & L2 & L3 & L4 & L5 & L6 & All & Decided `error' + "'" + ' \\\\', '\\midrule']
tot_all = 0
for key, name in CAUSES:
    cells = []; all_ = 0; err = 0
    for code in ['L2', 'L3', 'L4', 'L5', 'L6']:
        lay = next(k for k, v in LAYNAME.items() if v == code)
        n = sum(v for k, v in cz['by_layer'].get(lay, {}).items() if k.split('|')[0] == key)
        cells.append('%d' % n); all_ += n
    err = sum(v for k, v in cz['total'].items() if k == '%s|error' % key); tot_all += all_
    L.append('%s & %s & %d & %d \\\\' % (name, ' & '.join(cells), all_, err))
L += ['\\midrule', 'Total & %s & %d & %d \\\\' % (' & '.join(
    '%d' % sum(v for k, v in cz['by_layer'].get(next(x for x, y in LAYNAME.items() if y == c), {}).items()) for c in ['L2', 'L3', 'L4', 'L5', 'L6']),
    tot_all, sum(v for k, v in cz['total'].items() if k.endswith('|error'))), '\\bottomrule', '\\end{tabular}']
open(os.path.join(OUT, 'tab_causes.tex'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('tables written to', OUT)
print(json.dumps(json.load(open(os.path.join(HERE, 'j3_agreement.json'))), indent=1))
