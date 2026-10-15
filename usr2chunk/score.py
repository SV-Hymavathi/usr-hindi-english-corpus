"""score.py <output> <gold.tsv> <split.txt> [previous_output]
Exact match (lowercase, whitespace-normalised) and chunk-level P/R/F1 on one split; gains/losses vs previous run."""
import re, sys, collections


def norm(s):
    return re.sub(r'\s+', ' ', s.strip().lower())


def load_out(p):
    d = {}
    for line in open(p, encoding='utf-8'):
        m = re.match(r'^([^\s:<]+): (.*)$', line.rstrip('\n'))
        if m:
            d[m.group(1)] = m.group(2)
    return d


def chunks(s):
    return collections.Counter(norm(b) + (t or '') for b, t in re.findall(r'\[([^\]]*)\](_[A-Z]+)?', s))


def main():
    out = load_out(sys.argv[1])
    gold = {}
    for line in open(sys.argv[2], encoding='utf-8'):
        p = line.rstrip('\n').split('\t')
        if len(p) >= 2:
            gold[p[0]] = p[-1]
    ids = [l.strip() for l in open(sys.argv[3]) if l.strip()]
    prev = load_out(sys.argv[4]) if len(sys.argv) > 4 else None
    ex = tp = ns = ng = 0
    won, lost = [], []
    for i in ids:
        g, s = gold.get(i, ''), out.get(i, '')
        ok = norm(g) == norm(s)
        ex += ok
        cg, cs = chunks(g), chunks(s)
        tp += sum((cg & cs).values()); ng += sum(cg.values()); ns += sum(cs.values())
        if prev is not None:
            was = norm(prev.get(i, '')) == norm(g)
            if ok and not was:
                won.append(i)
            if was and not ok:
                lost.append(i)
    P = tp / ns if ns else 0; R = tp / ng if ng else 0; F = 2 * P * R / (P + R) if P + R else 0
    print('%s: exact %d/%d = %.1f%%   chunk P %.3f R %.3f F1 %.3f' % (sys.argv[3].split('/')[-1], ex, len(ids), 100 * ex / len(ids), P, R, F))
    if prev is not None:
        print('  gained %d %s\n  lost   %d %s' % (len(won), won[:40], len(lost), lost[:40]))


if __name__ == '__main__':
    main()
