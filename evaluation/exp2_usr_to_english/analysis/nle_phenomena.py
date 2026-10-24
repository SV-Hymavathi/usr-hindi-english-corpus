"""Experiment 2 analysis: loss rate per phenomenon: for each phenomenon that the USR records and the reference expresses,
the share of outputs that lose it. The opportunities of a sentence are the flags that the checks raise for an output
that expresses nothing (a dummy output); a run loses the phenomenon when the same flag is raised for its output.
Output: nle_phenomena.json and a printed table. Reuses the objects of nle_extended_analysis.py."""
import collections, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'nle_extended_analysis.py'), encoding='utf-8').read().split('# ---------------- changed USRs')[0]
src = src.replace("res[r][k] = ns['analyse'](it, hin[k], ref[k], o.get(k, ''))",
                  "res[r][k] = ns['analyse'](it, hin[k], ref[k], o.get(k, ''))\n        opp[k] = ns['analyse'](it, hin[k], ref[k], 'zzz qqq')")
src = src.replace("keys, ref, hin, usr, res, nrows = [], {}, {}, {}, collections.defaultdict(dict), {}",
                  "keys, ref, hin, usr, res, nrows = [], {}, {}, {}, collections.defaultdict(dict), {}\nopp = {}")
g = {'__file__': os.path.join(HERE, 'nle_extended_analysis.py'), '__name__': 'x'}
exec(src, g)
keys, RUNS, res, opp = g['keys'], g['RUNS'], g['res'], g['opp']
GROUPS = [('Names', r'^NE (dropped|replaced)'), ('Numbers', r'^number missing'), ('Culture-specific concepts', r'^cultural concept missing'),
          ('Modality', r'^modality'), ('Perfect aspect', r'^aspect \(perfect'), ('Passive voice', r'^voice \(passive'),
          ('Negation', r'^negation lost'), ('Purpose (rt)', r'relation rt '), ('Cause (rh)', r'relation rh '),
          ('Similarity (rsm)', r'relation rsm '), ('Connectives', r'^connective missing'), ('Particles', r'^particle '),
          ('Deixis', r'^deixis'), ('Questions', r'^question -> statement')]


def has(R, pat):
    return any(re.search(pat, s) for t, s, d in R)


out = {}
for name, pat in GROUPS:
    ks = [k for k in keys if has(opp[k], pat)]
    row = {'n': len(ks)}
    for r in RUNS:
        lost = sum(1 for k in ks if has(res[r][k], pat))
        row[r] = round(100.0 * lost / len(ks), 1) if ks else None
    out[name] = row
json.dump(out, open(os.path.join(HERE, 'nle_phenomena.json'), 'w', encoding='utf-8'), indent=1)
cols = ['gpt-oss-120b|E2a', 'gpt-oss-120b|E2b', 'gpt-oss-120b|E2c', 'Ministral 14B|E2c', 'Gemma 3 4B|E2c', 'gpt-oss-120b|DT', 'Ministral 14B|DT',
        'Gemma 3 4B|DT', 'gpt-oss-120b|CP', 'Ministral 14B|CP', 'Gemma 3 4B|CP', 'Ministral 14B|E2a', 'Ministral 14B|E2b', 'Gemma 3 4B|E2a', 'Gemma 3 4B|E2b']
print('%-26s %5s ' % ('phenomenon', 'n') + ' '.join('%9s' % c.replace('gpt-oss-120b', 'G').replace('Ministral 14B', 'M').replace('Gemma 3 4B', 'g') for c in cols))
for name, row in out.items():
    print('%-26s %5d ' % (name, row['n']) + ' '.join('%9s' % row[c] for c in cols))
