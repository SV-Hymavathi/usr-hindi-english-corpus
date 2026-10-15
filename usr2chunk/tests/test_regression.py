"""Regression lock: every sentence in tests/locked.tsv (exact gold matches at the time it was frozen) must still match.
Refresh deliberately with:  python3 tests/test_regression.py --freeze <gold.tsv>"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
USR = os.environ.get('USR2CHUNK_USR', '/root/projects/multilingual_rule_based_updated/gen_input_final.txt')
LOCK = os.path.join(HERE, 'locked.tsv')


def norm(s):
    return re.sub(r'\s+', ' ', s.strip().lower())


def run():
    out = subprocess.run([sys.executable, os.path.join(ROOT, 'generate.py'), USR], capture_output=True, text=True,
                         encoding='utf-8').stdout
    return {m.group(1): m.group(2) for m in (re.match(r'^([^\s:<]+): (.*)$', l) for l in out.split('\n')) if m}


if len(sys.argv) > 2 and sys.argv[1] == '--freeze':
    gold = {}
    for l in open(sys.argv[2], encoding='utf-8'):
        p = l.rstrip('\n').split('\t')
        if len(p) >= 2:
            gold[p[0]] = p[-1]
    got = run()
    keep = [(k, gold[k]) for k in gold if k in got and norm(got[k]) == norm(gold[k])]
    with open(LOCK, 'w', encoding='utf-8') as f:
        for k, g in keep:
            f.write('%s\t%s\n' % (k, g))
    print('frozen %d sentences' % len(keep))
    sys.exit(0)

locked = [l.rstrip('\n').split('\t') for l in open(LOCK, encoding='utf-8') if '\t' in l]
got = run()
bad = [(k, g, got.get(k, '')) for k, g in locked if norm(got.get(k, '')) != norm(g)]
print('regression: %d/%d locked sentences still exact' % (len(locked) - len(bad), len(locked)))
for k, g, s in bad[:20]:
    print('  BROKE %s\n    gold: %s\n    now : %s' % (k, g, s))
sys.exit(1 if bad else 0)
