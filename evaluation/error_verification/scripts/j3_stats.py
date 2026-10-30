#!/usr/bin/env python3
"""Statistics for the J3 paper (double-judged labels, human_verification/j3_final_labels.tsv): exact opportunity counts per phenomenon, error rates with Wilson 95% CIs,
exact McNemar tests between systems on the same sentences, and the 'metrics hide errors' analysis.
Only HUMAN-CONFIRMED errors are counted (human_verification/final_labels.tsv, final label 1); voice is excluded
(reported separately, see human_verification/final_results.json).
    python bhasha_stats.py           -> bhasha_stats.json (+ printed tables)
    python bhasha_stats.py --rules   -> rule candidates without the human filter (for comparison)"""
import collections, json, math, os, re, statistics, sys
import sacrebleu

HERE = os.path.dirname(os.path.abspath(__file__))
EXP1 = os.path.join(HERE, '..', '..', 'experiments', 'exp1')
SRC = open(os.path.join(EXP1, 'layered_analysis.py'), encoding='utf-8').read().split('# ---------------- run ----------------')[0]
RULES_ONLY = '--rules' in sys.argv
CONF = set()
for l in list(open(os.path.join(HERE, 'human_verification', 'j3_final_labels.tsv'), encoding='utf-8'))[1:]:
    i, L, sub, d, sid, s_, a_, b_, f = l.rstrip(chr(10)).split(chr(9))
    if f == '1':
        CONF.add((d, sid, s_, L, 'connective' if L == 'L4' else re.sub(r' \(.*', '', sub)))
SYS = ['google_translate', 'indictrans2_local', 'groq_gpt-oss-120b', 'ollama_gemma3-4b', 'mistral_ministral-14b']
PART = ('hI', 'BI', 'lagaBaga', 'kevala', 'sirPa', 'mAwra')
REL = ('rh', 'rt', 'rasneg')   # rsm = possessor (not similarity): excluded


def phen(nodes, st, hin):
    """phenomena required by the USR of one sentence"""
    p = set()
    if any(n['tam'] and n['rel'] == 'main' for n in nodes): p.add('tam')
    if any('pl' in n['gnp'] and not n['concept'].startswith(('[', '$')) for n in nodes): p.add('plural')
    if 'pass' in st: p.add('passive')
    else: p.add('active')
    if 'negative' in st or any(n['rel'] == 'neg' for n in nodes): p.add('negation')
    else: p.add('no_negation')
    if any(n['rel'] in REL for n in nodes): p.add('relation')
    if any(n['disc'] and n['disc'] != 'coref' for n in nodes): p.add('discourse')
    if any(re.search(r'\b(%s)_\d' % '|'.join(PART), n['spk'] + ' ' + n['scope']) for n in nodes): p.add('particle')
    if any(x in (n['spk'], n['scope']) for n in nodes for x in ('proximal', 'distal')): p.add('deixis')
    if any('respect' in n['spk'] for n in nodes): p.add('honorific')
    if 'interrogative' in st or hin.strip().endswith('?'): p.add('question')
    return p


# error type -> (label, opportunity)
def etype(t, sub):
    s = sub.lower()
    if s.startswith('tense'): return ('Tense', 'tam')
    if s.startswith('aspect'): return ('Aspect', 'tam')
    if s.startswith('modality'): return ('Modality', 'tam')
    if 'plural' in s: return ('Plural lost', 'plural')
    if 'passive -> active' in s: return ('Passive rendered active', 'passive')
    if 'active -> passive' in s: return ('Active rendered passive', 'active')
    if s.startswith('negation lost'): return ('Negation lost', 'negation')
    if s.startswith('negation added'): return ('Negation added', 'no_negation')
    if s.startswith('relation rsm'): return (None, None)
    if s.startswith('relation'): return ('Cause/purpose/without/like lost', 'relation')
    if t.startswith('L4'): return ('Connective missing', 'discourse')
    if s.startswith('particle'): return ('Focus particle lost', 'particle')
    if s.startswith('deixis'): return ('Deixis lost or reversed', 'deixis')
    if s.startswith('honorific'): return ('Honorific dropped', 'honorific')
    if s.startswith('question'): return ('Question rendered as statement', 'question')
    return (None, None)


def wilson(k, n, z=1.96):
    if not n: return (0, 0)
    p = k / n; d = 1 + z * z / n; c = p + z * z / (2 * n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (100 * (c - h) / d, 100 * (c + h) / d)


def mcnemar(b, c):
    """exact two-sided McNemar (binomial) on discordant counts b, c"""
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


opp = collections.Counter(); opp_dom = collections.Counter(); err = collections.defaultdict(set); per_sent = collections.defaultdict(dict)
chrf, flagged = collections.defaultdict(dict), collections.defaultdict(set)
for d in ['tourism', 'health', 'geography']:
    sys.argv = ['x', '--domain', d]
    ns = {'__file__': os.path.join(EXP1, 'layered_analysis.py'), '__name__': 'la'}
    exec(SRC, ns)
    for it in ns['items']:
        sid = (d, it['id'])
        hin = ns['hindi'].get(it['id'], it['hindi'])
        nodes, st = ns['parse_usr'](it['usr'])
        P = phen(nodes, st, hin)
        for p in P:
            opp[p] += 1; opp_dom[(d, p)] += 1
        for s in SYS:
            out = ns['SYS'][s].get(it['id'], '')
            chrf[s][sid] = sacrebleu.sentence_chrf(out, [it['reference']], word_order=2).score
            for t, sub, det in ns['analyse'](it, hin, it['reference'], out):
                if t.split()[0] not in ('L2', 'L3', 'L4', 'L5', 'L6'):
                    continue
                lab, o = etype(t, sub)
                L = t.split()[0]
                ckey = (d, it['id'], s, L, 'connective' if L == 'L4' else re.sub(r' \(.*', '', sub))
                if lab in ('Passive rendered active', 'Active rendered passive'):
                    continue
                if not RULES_ONLY and ckey not in CONF:
                    continue
                if lab and o in P:
                    err[(s, lab)].add(sid); flagged[s].add(sid)
LABELS = [('Tense', 'tam'), ('Aspect', 'tam'), ('Modality', 'tam'), ('Plural lost', 'plural'), ('Negation lost', 'negation'), ('Negation added', 'no_negation'),
          ('Cause/purpose/without/like lost', 'relation'), ('Connective missing', 'discourse'), ('Focus particle lost', 'particle'),
          ('Deixis lost or reversed', 'deixis'), ('Honorific dropped', 'honorific'), ('Question rendered as statement', 'question')]
table = []
for lab, o in LABELS:
    row = dict(label=lab, opp=opp[o], cells={})
    for s in SYS:
        k = len(err[(s, lab)]); lo, hi = wilson(k, opp[o])
        row['cells'][s] = dict(k=k, rate=100 * k / opp[o] if opp[o] else 0, lo=lo, hi=hi)
    table.append(row)
    print('%-32s n=%5d ' % (lab, opp[o]) + ' '.join('%5.1f[%4.1f-%4.1f]' % (row['cells'][s]['rate'], row['cells'][s]['lo'], row['cells'][s]['hi']) for s in SYS))

# McNemar: for each error type, worst system vs each other system (same opportunity sentences)
tests = []
for lab, o in LABELS:
    rates = {s: len(err[(s, lab)]) for s in SYS}
    worst = max(SYS, key=lambda s: rates[s])
    for s in SYS:
        if s == worst: continue
        A, B = err[(worst, lab)], err[(s, lab)]
        b, c = len(A - B), len(B - A)
        tests.append(dict(label=lab, worst=worst, other=s, b=b, c=c, p=mcnemar(b, c)))
print('\nMcNemar (worst system vs other), significant at 0.05:')
for t in tests:
    if True:
        print('  %-30s %-22s vs %-22s b=%3d c=%3d p=%.4f' % (t['label'], t['worst'], t['other'], t['b'], t['c'], t['p']))

# metrics hide errors
hide = {}
for s in SYS:
    med = statistics.median(chrf[s].values())
    fl = flagged[s]
    above = sum(1 for x in fl if chrf[s][x] >= med)
    clean = [chrf[s][x] for x in chrf[s] if x not in fl]
    hide[s] = dict(flagged=len(fl), above_median=above, share=100 * above / len(fl) if fl else 0, median=med,
                   mean_chrf_flagged=statistics.mean(chrf[s][x] for x in fl) if fl else 0,
                   mean_chrf_clean=statistics.mean(clean))
    print('%-22s flagged %4d, at/above median chrF++ %.1f%%  mean chrF flagged %.1f vs clean %.1f' %
          (s, len(fl), hide[s]['share'], hide[s]['mean_chrf_flagged'], hide[s]['mean_chrf_clean']))
GROUP = {'Tense': 'L2', 'Aspect': 'L2', 'Modality': 'L2', 'Plural lost': 'L2', 'Passive rendered active': 'L3', 'Active rendered passive': 'L3',
         'Negation lost': 'L3', 'Negation added': 'L3', 'Cause/purpose/without/like lost': 'L3', 'Connective missing': 'L4',
         'Focus particle lost': 'L5', 'Deixis lost or reversed': 'L5', 'Honorific dropped': 'L5', 'Question rendered as statement': 'L6'}
dom_layer = collections.defaultdict(set)
for (s, lab), ids in err.items():
    for (d, i) in ids:
        dom_layer[(d, GROUP[lab], s)].add(i)
for d in ['tourism', 'health', 'geography']:
    for L in ['L2', 'L3', 'L4', 'L5', 'L6']:
        print('DOM', d, L, [len(dom_layer[(d, L, s)]) for s in SYS])
json.dump(dict(opp=dict(opp), opp_dom={'%s|%s' % k: v for k, v in opp_dom.items()}, table=table, tests=tests, hide=hide, dom={'%s|%s' % (d_, L_): [len(dom_layer[(d_, L_, s_)]) for s_ in SYS] for d_ in ['tourism', 'health', 'geography'] for L_ in ['L2', 'L3', 'L4', 'L5', 'L6']}), open(os.path.join(HERE, 'j3_stats_rules.json' if RULES_ONLY else 'j3_stats.json'), 'w'), indent=1)
