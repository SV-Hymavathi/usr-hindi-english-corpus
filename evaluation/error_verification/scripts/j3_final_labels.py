"""J3 final labels: every candidate error judged twice.
  shared (337)        BHASHA labels (annotator 1 vs annotator 2's blind re-check, disagreements decided by the expert)
  not shared          first judgement (one annotator) vs blind second judgement (the other annotator, J3 second round);
                      agreement -> that label; disagreement or 'unsure' -> the agreed decision of the joint adjudication
                      (adjudication_disagreements.xlsx); candidates already decided by the expert negation check keep that
                      decision; the 'relation rsm' type stays excluded
  voice               reported separately, as in BHASHA
Outputs: j3_final_labels.tsv, j3_results.json (precision by layer, sub-type and system with Wilson intervals; agreement of
the two judgements per layer: raw, Cohen's kappa, Gwet's AC1; effect of the second judgement on the precision)."""
import collections, json, math, os, re, sys
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(os.path.expanduser('~'), 'Desktop', 'annotator_tasks', '3_J3_second_annotation')
K = {l.split('\t')[0]: l.rstrip('\n').split('\t') for l in list(open(os.path.join(HERE, 'verification_KEY.tsv'), encoding='utf-8'))[1:]}
d1 = lambda s: int(re.match(r'\s*(\d)', str(s)).group(1)) if s is not None and re.match(r'\s*(\d)', str(s)) else None


def wilson(k, n, z=1.96):
    if not n: return (float('nan'),) * 2
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - h) / d, (c + h) / d)


# BHASHA final labels (shared items decided there; single labels for the rest)
BH = {l.split('\t')[0]: l.rstrip('\n').split('\t')[-1] for l in list(open(os.path.join(HERE, 'final_labels.tsv'), encoding='utf-8'))[1:]}
# first-round judgements, per annotator
FIRST = {1: {}, 2: {}}
for k in (1, 2):
    for r in openpyxl.load_workbook(os.path.join(HERE, 'verification_annotator%d_completed.xlsx' % k))['Candidates'].iter_rows(min_row=2, values_only=True):
        if r[0]: FIRST[k][str(r[0])] = d1(r[6])
# second-round judgements
SK = {(int(t), s): c for s, c, t in (l.rstrip('\n').split('\t') for l in list(open(os.path.join(HERE, 'second_annotation_KEY.tsv'), encoding='utf-8'))[1:])}
SECOND = {}
for k in (1, 2):
    for r in openpyxl.load_workbook(os.path.join(D, 'second_annotation_for_annotator%d.xlsx' % k))['Items'].iter_rows(min_row=2, values_only=True):
        if r[0]: SECOND[SK[(k, str(r[0]))]] = (k, d1(r[6]))
# adjudication
JK = {l.split('\t')[0]: l.split('\t')[1] for l in list(open(os.path.join(HERE, 'j3_adjudication_KEY.tsv'), encoding='utf-8'))[1:]}
ADJ = {}
ws = openpyxl.load_workbook(os.path.join(D, 'adjudication_disagreements.xlsx'))['Disagreements']
h = [c.value for c in ws[1]]; ci = h.index('AGREED DECISION')
for r in ws.iter_rows(min_row=2, values_only=True):
    if r[0]: ADJ[JK[str(r[0])]] = d1(r[ci])
NK = {l.split('\t')[0]: l.split('\t')[1].strip() for l in list(open(os.path.join(HERE, 'negation_check_KEY.tsv')))[1:]}
NEG = {NK[str(x[0])]: (2 if str(x[5]).strip().lower() == 'no' else 1) for x in openpyxl.load_workbook(os.path.join(HERE, 'negation_check.xlsx'))['Negation'].iter_rows(min_row=2, values_only=True) if x[0]}

final, src, pairs = {}, collections.Counter(), {}
for i, k in K.items():
    if k[1] != 'Candidates' or 'relation rsm' in k[3] or 'voice' in k[3]: continue
    if k[7] == 'yes':
        final[i] = int(BH[i]) if BH.get(i, '').isdigit() else None; src['shared (BHASHA)'] += 1; continue
    first_ann = 1 if i in FIRST[1] else 2
    a, (sk, b) = FIRST[first_ann][i], SECOND.get(i, (None, None))
    pairs[i] = (a, b)
    if i in NEG: final[i] = NEG[i]; src['expert negation check'] += 1
    elif a == b and a in (1, 2): final[i] = a; src['agreed'] += 1
    elif i in ADJ and ADJ[i] in (1, 2): final[i] = ADJ[i]; src['adjudicated'] += 1
    else: final[i] = None; src['undecided'] += 1
print('label sources:', dict(src))
res = {'sources': dict(src), 'layers': {}, 'subtypes': {}, 'systems': {}, 'agreement': {}, 'change_vs_single': {}}
NAMES = {'L2': 'Morphology (TAM, number)', 'L3': 'Semantic relations', 'L4': 'Discourse connectives', 'L5': "Speaker's view", 'L6': 'Sentence type'}
for L in ['L2', 'L3', 'L4', 'L5', 'L6', 'ALL']:
    ids = [i for i, v in final.items() if v in (1, 2) and (L == 'ALL' or K[i][2] == L)]
    c = sum(final[i] == 1 for i in ids); lo, hi = wilson(c, len(ids))
    res['layers'][L] = dict(candidates=len(ids), confirmed=c, precision=c / len(ids), ci=[lo, hi])
    print('%-4s %4d / %4d = %.3f [%.3f, %.3f]' % (L, c, len(ids), c / len(ids), lo, hi))
sub = collections.defaultdict(lambda: [0, 0])
for i, v in final.items():
    if v in (1, 2): s = re.sub(r' \(.*', '', K[i][3]); sub[(K[i][2], s)][1] += 1; sub[(K[i][2], s)][0] += v == 1
res['subtypes'] = {'%s|%s' % k: v for k, v in sorted(sub.items())}
for s in sorted({K[i][6] for i in final}):
    ids = [i for i, v in final.items() if v in (1, 2) and K[i][6] == s]
    c = sum(final[i] == 1 for i in ids); lo, hi = wilson(c, len(ids))
    res['systems'][s] = dict(candidates=len(ids), confirmed=c, precision=c / len(ids), ci=[lo, hi])
    print('system %-24s %4d / %4d = %.3f' % (s, c, len(ids), c / len(ids)))


def agree(ps):
    ps = [(a, b) for a, b in ps if a in (1, 2) and b in (1, 2)]; n = len(ps)
    po = sum(a == b for a, b in ps) / n
    xa = [a for a, b in ps]; xb = [b for a, b in ps]
    pe = sum(xa.count(c) / n * xb.count(c) / n for c in (1, 2)); q = (xa.count(1) + xb.count(1)) / (2 * n); pg = 2 * q * (1 - q)
    return dict(n=n, agreement=po, kappa=(po - pe) / (1 - pe), ac1=(po - pg) / (1 - pg))


for L in ['L2', 'L3', 'L4', 'L5', 'L6', 'ALL']:
    r = agree([v for i, v in pairs.items() if L == 'ALL' or K[i][2] == L]); res['agreement'][L] = r
    print('agreement %-4s n=%4d raw %.2f kappa %.2f AC1 %.2f' % (L, r['n'], r['agreement'], r['kappa'], r['ac1']))
# effect of the second judgement: single-annotator precision (BHASHA labels) vs J3 labels, on the same non-shared items
ns = [i for i in pairs if final.get(i) in (1, 2) and BH.get(i, '').isdigit()]
c1 = sum(int(BH[i]) == 1 for i in ns); c2 = sum(final[i] == 1 for i in ns)
res['change_vs_single'] = dict(items=len(ns), single_confirmed=c1, double_confirmed=c2, flipped_to_not_error=sum(int(BH[i]) == 1 and final[i] == 2 for i in ns),
                               flipped_to_error=sum(int(BH[i]) == 2 and final[i] == 1 for i in ns))
print('non-shared items: single-judgement confirmed %d -> double-judgement %d of %d' % (c1, c2, len(ns)), res['change_vs_single'])
with open(os.path.join(HERE, 'j3_final_labels.tsv'), 'w', encoding='utf-8') as f:
    f.write('item\tlayer\tsubtype\tdomain\tid\tsystem\tfirst\tsecond\tfinal\n')
    for i, v in final.items():
        k = K[i]; a, b = pairs.get(i, ('', ''))
        f.write('\t'.join(map(str, [i, k[2], k[3], k[4], k[5], k[6], a, b, v])) + '\n')
json.dump(res, open(os.path.join(HERE, 'j3_results.json'), 'w'), indent=1)
