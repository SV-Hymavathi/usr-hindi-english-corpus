"""Sheet B: chunks written from scratch (no draft) vs the post-edited corpus gold and vs the generator."""
import os, re, sys, collections, statistics
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
F = 'chunks_written_without_draft.xlsx'
K = {l.split('\t')[0]: l.rstrip('\n').split('\t') for l in list(open(os.path.join(HERE, 'annotation_keys', 'B_gold_chunks_KEY.tsv'), encoding='utf-8'))[1:]}


def chunks(s):
    s = re.sub(r'\s+', ' ', str(s or '').strip().lower())
    return [re.sub(r'\s+', ' ', c).strip() for c in re.findall(r'\[[^\]]*\][a-z_]*', s)]


def prf(a, b):
    ca, cb = collections.Counter(a), collections.Counter(b); m = sum((ca & cb).values())
    p = m / len(a) if a else 0; r = m / len(b) if b else 0
    return p, r, (2 * p * r / (p + r) if p + r else 0)


ws = openpyxl.load_workbook(F).active
rows = [r for r in list(ws.iter_rows(values_only=True))[1:] if r[0]]
res = collections.defaultdict(list); bad = []; out = []
for r in rows:
    sid, dom, mine = r[0], r[1], r[5]
    if not mine: bad.append(sid); continue
    _, _, gold, gen = K[sid]
    A, G, S = chunks(mine), chunks(gold), chunks(gen)
    if not A: bad.append(sid); continue
    for name, ref in (('gold', G), ('generator', S)):
        res[(name, dom)].append((A == ref, prf(A, ref)[2])); res[(name, 'all')].append((A == ref, prf(A, ref)[2]))
    res[('gold_vs_gen', 'all')].append((G == S, prf(S, G)[2]))
    out.append((sid, dom, A == G, A == S, mine, gold, gen))
print('rows', len(rows), 'unusable', bad)
for name in ('gold', 'generator'):
    for d in ('tourism', 'health', 'geography', 'all'):
        v = res[(name, d)]
        print('%-9s vs scratch %-9s n=%3d exact %5.1f%%  chunkF1 %.3f' % (name, d, len(v), 100 * sum(e for e, _ in v) / len(v), statistics.mean(f for _, f in v)))
v = res[('gold_vs_gen', 'all')]; print('generator vs gold (same 100): exact %.1f%% F1 %.3f' % (100 * sum(e for e, _ in v) / len(v), statistics.mean(f for _, f in v)))
both = sum(1 for o in out if o[2] and o[3]); og = sum(1 for o in out if o[2] and not o[3]); os_ = sum(1 for o in out if o[3] and not o[2])
print('scratch = gold and generator:', both, '| = gold only:', og, '| = generator only:', os_, '| neither:', len(out) - both - og - os_)
for o in out[:0]: pass
print('\nexamples where scratch differs from gold:')
for o in [o for o in out if not o[2]][:12]:
    print(' ', o[0], '\n    scratch:', o[4], '\n    gold   :', o[5], '\n    gen    :', o[6])
