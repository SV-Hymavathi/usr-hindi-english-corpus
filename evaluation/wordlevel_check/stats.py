r"""Wilson intervals of the share of sentences with a confirmed word-level error per system, and two-sided Fisher exact
tests between systems (exact hypergeometric, no external packages)."""
import math
N = 960
S = {'Google Translate': 11, 'IndicTrans2': 21, 'gpt-oss-120b': 16, 'Ministral 14B': 24, 'Gemma 3 4B': 22}


def wilson(k, n, z=1.96):
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return 100 * (c - h) / d, 100 * (c + h) / d


def fisher(a, b, c, d):
    n1, n2, k = a + b, c + d, a + c
    def pmf(x): return math.comb(n1, x) * math.comb(n2, k - x) / math.comb(n1 + n2, k)
    p0 = pmf(a)
    return min(1.0, sum(pmf(x) for x in range(max(0, k - n2), min(k, n1) + 1) if pmf(x) <= p0 * (1 + 1e-9)))


for s, k in S.items():
    lo, hi = wilson(k, N); print('%-16s %2d %.1f%% (%.1f-%.1f)' % (s, k, 100 * k / N, lo, hi))
print('Google vs Ministral p = %.3f' % fisher(11, N - 11, 24, N - 24))
print('Google vs IndicTrans2 p = %.3f' % fisher(11, N - 11, 21, N - 21))
print('Google vs Gemma p = %.3f' % fisher(11, N - 11, 22, N - 22))
print('gpt-oss vs Ministral p = %.3f' % fisher(16, N - 16, 24, N - 24))
# names: MT systems 5 confirmed name errors in 1,920 outputs, LLMs 30 in 2,880
print('names MT vs LLM p = %.4f' % fisher(5, 1920 - 5, 30, 2880 - 30))
