"""Final scores of the human verification (Experiment 2) after the E2c rerun with the corrected gloss: the 24 E2c items
whose output was regenerated are replaced by their re-check items (V3 -> V3r). Precision by flag group, condition and
model; agreement on the overlap (observed, Cohen's kappa, Gwet's AC1). Output: nle_verification_final.json"""
import collections, json, os, sys
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
D = HERE


def tsv(p):
    h, *rr = [l.rstrip('\n').split('\t') for l in open(p, encoding='utf-8')]
    return {r[0]: dict(zip(h, r)) for r in rr}


def labels(f):
    out = {}
    for r in list(openpyxl.load_workbook(os.path.join(D, f), read_only=True).active.iter_rows(values_only=True))[1:]:
        if r and r[0] and str(r[5] or '').strip().lower() in ('yes', 'no', 'unsure'):
            out[str(r[0]).strip()] = str(r[5]).strip().lower()
    return out


key, rkey = tsv(os.path.join(HERE, 'nle_verification_KEY.tsv')), tsv(os.path.join(HERE, 'nle_verification_KEY_recheck.tsv'))
replaced = {r['replaces'] for r in rkey.values()}
key = {k: v for k, v in key.items() if k not in replaced}
key.update(rkey)
a1 = {k: v for k, v in labels('annotator1_verification_359.xlsx').items() if k not in replaced}
a1.update(labels('recheck_annotator1.xlsx'))
a2 = {k: v for k, v in labels('annotator2_verification_72.xlsx').items() if k not in replaced}
a2.update(labels('recheck_annotator2.xlsx'))
missing = sorted(set(key) - set(a1))
print('items %d, annotator-1 labels %d, missing %s' % (len(key), len(a1), missing))


def group(k):
    lay, sub = k['layer'], k['sub_type']
    if lay == 'L1a Lexical & NE':
        return 'Names' if sub.startswith('NE') else 'Numbers'
    return {'L1b Cultural concepts': 'Cultural concepts', 'L1d Other sense used': 'Word senses', 'L2 Morphology': 'TAM and number',
            'L3 Semantic relations': 'Relations, voice, negation', 'L4 Discourse': 'Connectives', "L5 Speaker's view": 'Particles and deixis',
            'L6 Sentence type': 'Sentence type'}[lay]


def prec(fn):
    t = collections.defaultdict(collections.Counter)
    for it, v in a1.items():
        t[fn(key[it])][v] += 1
    return {g: dict(checked=c['yes'] + c['no'] + c['unsure'], confirmed=c['yes'], unsure=c['unsure'],
                    precision=round(c['yes'] / (c['yes'] + c['no']), 2)) for g, c in sorted(t.items())}


R = {'overall': prec(lambda k: 'All')['All'], 'by_group': prec(group), 'by_condition': prec(lambda k: k['condition']),
     'by_model': prec(lambda k: k['system'].split()[0]), 'by_sub_type': prec(lambda k: k['sub_type'])}
both = sorted(set(a1) & set(a2))
pairs = [(a1[i], a2[i]) for i in both]
n = len(pairs); agree = sum(x == y for x, y in pairs); po = agree / n
cats = sorted({c for p in pairs for c in p})
pe_k = sum((sum(x == c for x, _ in pairs) / n) * (sum(y == c for _, y in pairs) / n) for c in cats)
pi = {c: (sum(x == c for x, _ in pairs) + sum(y == c for _, y in pairs)) / (2 * n) for c in cats}
q = max(2, len(cats))
pe_g = sum(p * (1 - p) for p in pi.values()) / (q - 1)
R['agreement'] = dict(items=n, agree=agree, observed=round(po, 3), cohen_kappa=round((po - pe_k) / (1 - pe_k), 3),
                      gwet_ac1=round((po - pe_g) / (1 - pe_g), 3), confusion=dict(collections.Counter('%s/%s' % p for p in pairs)),
                      share_yes=round(pi.get('yes', 0), 3))
json.dump(R, open(os.path.join(HERE, 'nle_verification_final.json'), 'w', encoding='utf-8'), indent=1)
print(json.dumps(R['overall'])); print(json.dumps(R['by_group'], indent=0)); print(json.dumps(R['by_condition'])); print(json.dumps(R['by_model']))
print(json.dumps(R['agreement']))
print('names:', {k: v for k, v in R['by_sub_type'].items() if k.startswith('NE')}, '| numbers:', R['by_sub_type'].get('number missing / changed'))
