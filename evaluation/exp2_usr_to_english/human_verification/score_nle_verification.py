r"""Score the human verification of the Experiment 2 error candidates (annotator_tasks/4_NLE_exp2_verification):
precision of the automatic flags (share confirmed as real errors) by condition, system and layer, and agreement
between annotator 1 (all items) and annotator 2 (overlap items). Rows without an item ID are ignored.
Output: nle_verification_results.json and a printed summary. Usage: python score_nle_verification.py"""
import collections, json, os, sys
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
D = HERE   # the annotator sheets are in this folder
key = {r['item']: r for r in (dict(zip(h, l.rstrip('\n').split('\t'))) for h in [open(os.path.join(HERE, 'nle_verification_KEY.tsv'), encoding='utf-8').readline().rstrip('\n').split('\t')]
                                for l in list(open(os.path.join(HERE, 'nle_verification_KEY.tsv'), encoding='utf-8'))[1:])}

def labels(fn):
    out = {}
    for r in list(openpyxl.load_workbook(os.path.join(D, fn), read_only=True).active.iter_rows(values_only=True))[1:]:
        if not r or not r[0]: continue
        v = str(r[5] or '').strip().lower()
        if v in ('yes', 'no', 'unsure'): out[str(r[0]).strip()] = (v, str(r[6] or '').strip())
    return out

a1, a2 = labels('annotator1_verification_359.xlsx'), labels('annotator2_verification_72.xlsx')
print('annotator 1: %d labelled items, annotator 2: %d labelled items; key: %d items' % (len(a1), len(a2), len(key)))
missing = sorted(set(key) - set(a1), key=lambda x: int(x[1:]))
print('key items without an annotator-1 label:', missing)

def prec(group):
    t = collections.Counter()
    for it, (v, _) in a1.items():
        k = key.get(it)
        if k: t[(k[group], v)] += 1
    res = {}
    for g in sorted({x[0] for x in t}):
        y, n, u = t[(g, 'yes')], t[(g, 'no')], t[(g, 'unsure')]
        res[g] = {'yes': y, 'no': n, 'unsure': u, 'precision': round(y / (y + n), 3) if y + n else None}
    return res

R = {'n_annotator1': len(a1), 'n_annotator2': len(a2),
     'overall': {'yes': sum(v == 'yes' for v, _ in a1.values()), 'no': sum(v == 'no' for v, _ in a1.values()),
                 'unsure': sum(v == 'unsure' for v, _ in a1.values())},
     'by_condition': prec('condition'), 'by_system': prec('system'), 'by_layer': prec('layer'), 'by_sub_type': prec('sub_type')}
R['overall']['precision'] = round(R['overall']['yes'] / (R['overall']['yes'] + R['overall']['no']), 3)

# agreement on the overlap
both = sorted(set(a1) & set(a2), key=lambda x: int(x[1:]))
pairs = [(a1[i][0], a2[i][0]) for i in both]
agree = sum(x == y for x, y in pairs)
cats = ('yes', 'no', 'unsure')
po = agree / len(pairs) if pairs else 0
pe = sum((sum(x == c for x, _ in pairs) / len(pairs)) * (sum(y == c for _, y in pairs) / len(pairs)) for c in cats) if pairs else 0
kappa = (po - pe) / (1 - pe) if pe < 1 else 1.0
R['agreement'] = {'items': len(pairs), 'agree': agree, 'observed': round(po, 3), 'cohen_kappa': round(kappa, 3),
                  'confusion': dict(collections.Counter('%s/%s' % p for p in pairs)),
                  'annotator2_yes': sum(y == 'yes' for _, y in pairs)}
R['annotator1_distinct_notes'] = len({n for _, n in a1.values() if n})
R['annotator2_distinct_notes'] = len({n for _, n in a2.values() if n})
json.dump(R, open(os.path.join(HERE, 'nle_verification_results.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(json.dumps({k: R[k] for k in ('overall', 'agreement', 'by_condition', 'by_system', 'by_layer')}, indent=1, ensure_ascii=False))
print('distinct notes: annotator 1 %d, annotator 2 %d' % (R['annotator1_distinct_notes'], R['annotator2_distinct_notes']))
