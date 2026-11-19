"""Paper 2: span-level faithfulness errors (missing, added and wrong information) in Study 2 (folder 25).
Reads the staged release file (same data as the annotators' sheets), writes spans.json and prints a report."""
import csv, json, os, re, sys, random, collections, statistics as st
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', '..', 'human_evaluation_study2', 'ratings.tsv')
R = list(csv.DictReader(open(SRC, encoding='utf-8'), delimiter='\t'))
num = lambda v: (float(re.match(r'(\d+)', str(v)).group(1)) if re.match(r'\s*(\d+)', str(v).strip()) else 0.0)
K = ('missing', 'added', 'wrong')
for r in R:
    for k in K:
        r[k + '1'] = num(r['ann1_%s_count' % k]); r[k + '2'] = num(r['ann2_%s_count' % k])
        r[k] = (r[k + '1'] + r[k + '2']) / 2
        r[k + '_both'] = r[k + '1'] > 0 and r[k + '2'] > 0
        r[k + '_either'] = r[k + '1'] > 0 or r[k + '2'] > 0
    r['route'] = 'mt' if r['system'] in ('google_translate', 'indictrans2') else ('usr' if r['input'] == 'USR chunks' else 'hindi')
SYS = ['google_translate', 'indictrans2', 'gpt-oss-120b', 'gemma3-4b', 'ministral-14b']
CONF = [('google_translate', 'Hindi sentence'), ('indictrans2', 'Hindi sentence')] + [(m, i) for m in SYS[2:] for i in ('Hindi sentence', 'USR chunks')]


def boot(vals, n=4000, seed=3):
    rnd = random.Random(seed); m = len(vals); s = sorted(sum(vals[rnd.randrange(m)] for _ in range(m)) / m for _ in range(n))
    return s[int(0.025 * n)], s[int(0.975 * n)]


def wilcoxon(d):
    import math
    d = [x for x in d if x != 0]; n = len(d)
    if n == 0: return 1.0
    a = sorted(range(n), key=lambda i: abs(d[i])); r = [0.0] * n; i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(d[a[j + 1]]) == abs(d[a[i]]): j += 1
        for k in range(i, j + 1): r[a[k]] = (i + j) / 2 + 1
        i = j + 1
    wp = sum(r[i] for i in range(n) if d[i] > 0); mu = n * (n + 1) / 4; sd = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    return math.erfc(abs((wp - mu) / sd) / math.sqrt(2))


OUT = {'n': len(R)}
# ---- per configuration
conf = {}
for s, i in CONF:
    v = [r for r in R if r['system'] == s and r['input'] == i]
    d = dict(n=len(v))
    for k in K:
        d[k + '_items_per100'] = round(100 * st.mean(r[k] for r in v), 1)
        d[k + '_both_pct'] = round(100 * st.mean(r[k + '_both'] for r in v), 1)
        d[k + '_either_pct'] = round(100 * st.mean(r[k + '_either'] for r in v), 1)
    d['any_both_pct'] = round(100 * st.mean(any(r[k + '_both'] for k in K) for r in v), 1)
    d['clean_pct'] = round(100 * st.mean(all(r[k] == 0 for k in K) for r in v), 1)
    conf['%s|%s' % (s, i)] = d
OUT['configurations'] = conf
# ---- paired: same model, same sentence, Hindi vs USR
pairs = {}
by = {}
for r in R: by[(r['domain'], r['id'], r['system'], r['input'])] = r
for m in SYS[2:]:
    sents = sorted({(r['domain'], r['id']) for r in R if r['system'] == m})
    P = {}
    for k in K:
        d = [by[(dd, ii, m, 'USR chunks')][k] - by[(dd, ii, m, 'Hindi sentence')][k] for dd, ii in sents]
        lo, hi = boot(d)
        P[k] = dict(mean_diff_per100=round(100 * st.mean(d), 1), ci=[round(100 * lo, 1), round(100 * hi, 1)], p=round(wilcoxon(d), 4),
                    hindi_only=sum(1 for dd, ii in sents if by[(dd, ii, m, 'Hindi sentence')][k + '_both'] and not by[(dd, ii, m, 'USR chunks')][k + '_both']),
                    usr_only=sum(1 for dd, ii in sents if by[(dd, ii, m, 'USR chunks')][k + '_both'] and not by[(dd, ii, m, 'Hindi sentence')][k + '_both']))
    pairs[m] = P
OUT['paired'] = pairs
# ---- agreement on presence
agree = {}
for k in K:
    a = [r[k + '1'] > 0 for r in R]; b = [r[k + '2'] > 0 for r in R]
    po = sum(x == y for x, y in zip(a, b)) / len(a); pa, pb = sum(a) / len(a), sum(b) / len(b)
    pe = pa * pb + (1 - pa) * (1 - pb); p = (pa + pb) / 2; pe1 = 2 * p * (1 - p)
    agree[k] = dict(raw=round(po, 3), kappa=round((po - pe) / (1 - pe), 3), ac1=round((po - pe1) / (1 - pe1), 3), n1=sum(a), n2=sum(b))
OUT['agreement'] = agree

# ---- what is affected: categories of the marked words
MISS_CAT = [('discourse connective', r'^(पर|परंतु|परन्तु|किंतु|किन्तु|लेकिन|अर्थात्?|यानी|तो|और|तथा|एवं|क्योंकि|इसलिए|अतः|अत:|फिर|जबकि|यद्यपि|ताकि|वरना|अन्यथा|बल्कि|इस ?प्रकार|साथ ही)$'),
            ('particle (emphasis, inclusion)', r'^(ही|भी|तक|मात्र|केवल|सिर्फ़?)$'),
            ('quantifier or determiner', r'^(सभी|सब|पूरे|पूरा|पूरी|कुछ|हर|प्रत्येक|कई|अनेक|अधिक|कम|बहुत|ज्यादा|ज़्यादा|सारे|सारी|दोनों|एक|यह|वह|ये|वे|इस|उस|इन|उन)$'),
            ('postposition or case', r'^(में|से|का|की|के|को|पर|द्वारा|लिए|ओर|तरफ़?|नाम से|के नाम से|की ओर)$')]
ADD_CAT = [('speaker or addressee invented', r'^(i|we|you|me|my|our|your|us)$'),
           ('evaluative or decorative modifier', r'^(lush|beautiful|sacred|rich|famous|magnificent|stunning|breathtaking|picturesque|serene|quaint|vibrant|exquisite|ancient|deep|various|variety|wonderful|popular|major|important|renowned|scenic|holy|revered|sweet|juicy|dripping|sweetness|truly)$'),
           ('hedge or approximation', r'^(approximately|about|around|roughly|nearly|generally|typically|usually|often|may|might|perhaps|also)$'),
           ('function word', r'^(and|the|a|an|of|in|to|namely|which|that|is|are|was|were|with|for|on|by|as|its|it)$')]


def tokens(s):
    s = re.sub(r'(not\s*=|=|instead of|should be|missing|is named|wrong|order is wrong in sentence).*$', '', s, flags=re.I)
    return [t for t in re.split(r'[,;/|]+', s) if t.strip()]


def classify(phrase, cats, latin):
    p = phrase.strip().strip('.').strip()
    if not p: return None
    words = p.split()
    if latin and len(words) >= 3: return 'clause or phrase added'
    for name, rx in cats:
        if all(re.match(rx, w, flags=re.I) for w in words): return name
    if latin and p[:1].isupper() and len(words) <= 3: return 'name or proper noun'
    if not latin and len(words) >= 3: return 'clause or phrase'
    return 'content word'


cat = {}
for k, cats, latin in (('missing', MISS_CAT, False), ('added', ADD_CAT, True), ('wrong', [], True)):
    C = collections.Counter(); ex = collections.defaultdict(list)
    for r in R:
        if not r[k + '_both']: continue                 # only spans where both annotators marked this kind of error
        for a in (1, 2):
            for ph in tokens(r['ann%d_%s_words' % (a, k)]):
                c = classify(ph, cats, latin)
                if k == 'wrong':
                    c = 'name or proper noun' if ph.strip()[:1].isupper() or re.search(r'[A-Z]', ph) else 'common word or phrase'
                if c:
                    C[c] += 1
                    if len(ex[c]) < 6: ex[c].append((r['system'], r['input'], ph.strip(), r['output'][:90]))
    cat[k] = dict(counts=dict(C.most_common()), examples={c: v for c, v in ex.items()})
OUT['categories'] = cat
json.dump(OUT, open(os.path.join(HERE, '..', 'results', 'spans.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

print('agreement:', agree)
print('\n%-36s %8s %8s %8s | %6s %6s %6s | %6s %6s' % ('configuration', 'miss/100', 'add/100', 'wrong/100', 'miss%', 'add%', 'wrng%', 'any%', 'clean%'))
for c, d in conf.items():
    print('%-36s %8.1f %8.1f %8.1f | %6.1f %6.1f %6.1f | %6.1f %6.1f' % (c, d['missing_items_per100'], d['added_items_per100'], d['wrong_items_per100'],
          d['missing_both_pct'], d['added_both_pct'], d['wrong_both_pct'], d['any_both_pct'], d['clean_pct']))
print('\npaired (USR minus Hindi, items per 100 outputs, mean of annotators):')
for m, P in pairs.items(): print('  ', m, {k: (v['mean_diff_per100'], v['ci'], v['p'], '%d/%d' % (v['hindi_only'], v['usr_only'])) for k, v in P.items()})
for k in K:
    print('\n### categories:', k, cat[k]['counts'])
    for c, v in cat[k]['examples'].items():
        for e in v[:3]: print('     [%s] %s/%s: "%s" in: %s' % (c, e[0], e[1][:5], e[2], e[3]))
