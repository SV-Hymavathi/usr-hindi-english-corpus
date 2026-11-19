import csv, json, os, re, sys, random, math, statistics as st
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
R = list(csv.DictReader(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'human_evaluation_study2', 'ratings.tsv'), encoding='utf-8'), delimiter='\t'))
num = lambda v: min(3, int(re.match(r'\s*(\d+)', v).group(1))) if re.match(r'\s*(\d+)', v or '') else 0
K = ('missing', 'added', 'wrong')
by = {(r['domain'], r['id'], r['system'], r['input']): r for r in R}
from spans import wilcoxon, boot
LLM = ['gpt-oss-120b', 'gemma3-4b', 'ministral-14b']
pairs = [(by[(d, i, m, 'Hindi sentence')], by[(d, i, m, 'USR chunks')]) for (d, i, m, inp) in by if m in LLM and inp == 'Hindi sentence']
out = {'n_pairs': len(pairs)}
items = lambda r, k: (num(r['ann1_%s_count' % k]) + num(r['ann2_%s_count' % k])) / 2
for k in K + ('all',):
    f = (lambda r: sum(items(r, kk) for kk in K)) if k == 'all' else (lambda r, k=k: items(r, k))
    d = [f(u) - f(h) for h, u in pairs]; lo, hi = boot(d)
    out[k] = dict(hindi=round(100 * st.mean(f(h) for h, u in pairs), 1), usr=round(100 * st.mean(f(u) for h, u in pairs), 1), diff=round(100 * st.mean(d), 1), ci=[round(100 * lo, 1), round(100 * hi, 1)], p=wilcoxon(d))
def mcn(fn):
    b = sum(1 for h, u in pairs if fn(h) and not fn(u)); c = sum(1 for h, u in pairs if fn(u) and not fn(h))
    n = b + c; p = min(1.0, 2 * sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n) if n else 1.0
    return dict(hindi_only=b, usr_only=c, hindi=sum(1 for h, u in pairs if fn(h)), usr=sum(1 for h, u in pairs if fn(u)), p=p)
out['critical_either'] = mcn(lambda r: 'critical' in (r['ann1_severity'], r['ann2_severity']))
out['major_or_critical_both'] = mcn(lambda r: r['ann1_severity'] in ('major', 'critical') and r['ann2_severity'] in ('major', 'critical'))
out['clean_both'] = mcn(lambda r: all(num(r['ann%d_%s_count' % (a, k)]) == 0 for a in (1, 2) for k in K))
for k in ('critical_either', 'major_or_critical_both', 'clean_both', 'missing', 'added', 'wrong', 'all'): print(k, out[k])
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'pooled.json'), 'w'), indent=1)
