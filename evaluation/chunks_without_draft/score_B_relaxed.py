"""Sheet B, convention-neutral: compare content words (tags, articles, punctuation removed), chunk boundaries
(article/tag-free chunks), and the draft-bias test on the sentences where the gold differs from the generator."""
import os, re, sys, collections, statistics
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'score_B_chunks.py'), encoding='utf-8').read().split('ws = openpyxl')[0])
STOP = {'the', 'a', 'an'}


def words(s):
    s = re.sub(r'_[a-z]+', ' ', str(s or '').lower()); s = re.sub(r'[^\w\s]', ' ', s.replace('-', ' '))
    return [w for w in s.split() if w not in STOP]


def nchunks(s):
    return [' '.join(words(c)) for c in re.findall(r'\[([^\]]*)\]', str(s or '').lower())]


def tags(s):
    return re.findall(r'\]_([a-z]+)', str(s or '').lower())


ws = openpyxl.load_workbook(F).active
rows = [r for r in list(ws.iter_rows(values_only=True))[1:] if r[0] and r[5]]
R = collections.defaultdict(list); tagc = collections.Counter(); bias = []
for r in rows:
    sid, dom, mine = r[0], r[1], r[5]; _, _, gold, gen = K[sid]
    for nm, ref in (('gold', gold), ('gen', gen)):
        R[('word', nm, dom)].append(prf(words(mine), words(ref))[2]); R[('word', nm, 'all')].append(prf(words(mine), words(ref))[2])
        R[('chunk', nm, 'all')].append(prf(nchunks(mine), nchunks(ref))[2])
        R[('wexact', nm, 'all')].append(sorted(words(mine)) == sorted(words(ref)))
    tagc.update(tags(mine))
    if chunks(gold) != chunks(gen):
        bias.append((sid, prf(words(mine), words(gold))[2], prf(words(mine), words(gen))[2]))
for d in ('tourism', 'health', 'geography', 'all'):
    print('content-word F1 %-9s scratch~gold %.3f  scratch~generator %.3f' % (d, statistics.mean(R[('word', 'gold', d)]), statistics.mean(R[('word', 'gen', d)])))
print('chunk F1 (no tags/articles) scratch~gold %.3f  scratch~gen %.3f' % (statistics.mean(R[('chunk', 'gold', 'all')]), statistics.mean(R[('chunk', 'gen', 'all')])))
print('same content words (any order) gold %d%%  gen %d%%' % (100 * sum(R[('wexact', 'gold', 'all')]) / len(rows), 100 * sum(R[('wexact', 'gen', 'all')]) / len(rows)))
print('tags used by annotator', tagc.most_common())
print('draft-bias test: %d sentences where gold != generator' % len(bias))
print('  scratch closer to gold %d, closer to generator %d, tie %d' % (sum(g > s for _, g, s in bias), sum(s > g for _, g, s in bias), sum(g == s for _, g, s in bias)))
print('  mean F1 scratch~gold %.3f  scratch~gen %.3f' % (statistics.mean(g for _, g, _ in bias), statistics.mean(s for _, _, s in bias)))
