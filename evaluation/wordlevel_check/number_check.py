r"""Value-based number check: the 50 number candidates of the digit rule re-checked after normalising both sides to values.
Hindi: digits (Devanagari converted), fractions 'a b/c', multipliers sau/hazAra/lAKa/karoda. English: digits, number words
(one ... ninety, hyphenated), fractions (1/2, 1/4, one-fourth, half, quarter) and symbols (1/2-sign, 1/4-sign), multipliers
(hundred, thousand, lakh, crore, million, billion), 'noon'/'midnight' = 12, and figure numbers split by a space ('4. 4').
A candidate is kept if a Hindi value is not among the output values. Output: printed table (no LLM)."""
import json, os, re, sys

sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
import csv
V = list(csv.DictReader(open(os.path.join(HERE, 'expert_verdicts.tsv'), encoding='utf-8'), delimiter='\t'))
DEV = str.maketrans('०१२३४५६७८९', '0123456789')
UNITS = {w: i for i, w in enumerate('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen '
                                     'fifteen sixteen seventeen eighteen nineteen'.split())}
TENS = {w: 10 * i for i, w in enumerate('_ _ twenty thirty forty fifty sixty seventy eighty ninety'.split()) if w != '_'}
MULT_EN = {'hundred': 100, 'thousand': 1e3, 'lakh': 1e5, 'lakhs': 1e5, 'crore': 1e7, 'crores': 1e7, 'million': 1e6, 'billion': 1e9}
MULT_HI = {'सौ': 100, 'हज़ार': 1e3, 'हजार': 1e3, 'लाख': 1e5, 'करोड़': 1e7, 'करोड़': 1e7}
FRAC = {'half': .5, 'quarter': .25, 'one-fourth': .25, 'one-half': .5, 'three-fourths': .75, '½': .5, '¼': .25, '¾': .75}


def r(v): return round(v, 4)


def hindi_values(s):
    s = s.translate(DEV).replace(',', '')
    s = re.sub(r'(\d+)\s*\((\d+)/(\d+)\)', r'\1 \2/\3', s)                # 365(1/4) -> 365 1/4
    vals = set()
    for m in re.finditer(r'(?<![\d/])(\d+)/(\d+)(?![\d/])', s):            # a fraction on its own: 1/4
        if not re.search(r'\d\s+$', s[:m.start()]): vals.add(r(float(m.group(1)) / float(m.group(2))))
    for m in re.finditer(r'(?<![/\d])(\d+(?:\.\d+)?)(?![/\d.])(?:\s+(\d+)/(\d+))?(?:\s*(सौ|हज़ार|हजार|लाख|करोड़|करोड़))?', s):
        v = float(m.group(1))
        if m.group(2): v += float(m.group(2)) / float(m.group(3))
        if m.group(4): v *= MULT_HI[m.group(4)]
        vals.add(r(v))
        if not m.group(2) and not m.group(4) and '.' in m.group(1):
            vals.add(r(v))
    return vals


def word_number(tokens, i):
    """an English number word at tokens[i] (one, twenty-five, forty five), with its length"""
    t = tokens[i]
    if t in FRAC: return FRAC[t], 1
    parts = t.split('-')
    if len(parts) > 1 and (parts[0] in UNITS or parts[0] in TENS) and not all(p in UNITS or p in TENS for p in parts):
        parts = parts[:1]                                                # six-year -> six
    if all(p in UNITS or p in TENS for p in parts):
        return sum(UNITS.get(p, 0) + TENS.get(p, 0) for p in parts), 1
    if t in TENS and i + 1 < len(tokens) and tokens[i + 1] in UNITS:
        return TENS[t] + UNITS[tokens[i + 1]], 2
    if t in ('noon', 'midnight'): return 12, 1
    return None, 0


def english_values(s):
    s = s.replace(',', '').replace('\\', ' ').replace('‑', '-').replace('‐', '-')
    s = re.sub(r'(?<!\d)\.(\d)', r'0.\1', s)                             # .3% -> 0.3
    s = re.sub(r'(\d+)\.\s+(\d+)', r'\1.\2', s)                      # figure numbers split by a space: 4. 4 -> 4.4
    s = re.sub(r'(\d+):\s+(\d+)', r'\1:\2', s)
    toks = re.findall(r"\d+(?:\.\d+)?[½¼¾]?|[½¼¾]|[A-Za-z]+(?:-[A-Za-z]+)*", s)
    toks = [t.lower() for t in toks]
    vals, i = set(), 0
    while i < len(toks):
        t = toks[i]
        m = re.match(r'^(\d+(?:\.\d+)?)([½¼¾]?)$', t)
        v, n = (float(m.group(1)) + (FRAC[m.group(2)] if m.group(2) else 0), 1) if m else word_number(toks, i)
        if v is None:
            i += 1; continue
        if i + n < len(toks) and toks[i + n] in MULT_EN:
            v *= MULT_EN[toks[i + n]]; n += 1
        vals.add(r(v))
        if re.match(r'^\d+\.\d+$', t):                                # 4.4 may also be read as 4 and 4
            vals |= {r(float(x)) for x in t.split('.')}
        i += n
    return vals


rows = []
for x in V:
    if not x['rule'].startswith('number'): continue
    hv, ov = hindi_values(x['hindi']), english_values(x['output'])
    rows.append((x['item'], x['system'], x['expert_verdict'], sorted(hv - ov), x['output'][:70]))
kept = [r_ for r_ in rows if r_[3]]
conf = [r_ for r_ in rows if r_[2] == 'yes']
print('candidates', len(rows), '| kept by the value check', len(kept), '| confirmed', len(conf),
      '| confirmed kept', sum(1 for r_ in kept if r_[2] == 'yes'))
for r_ in rows: print(r_[2], 'KEPT' if r_[3] else '    ', r_[3], '|', r_[4])
json.dump({'candidates': len(rows), 'kept': len(kept), 'confirmed': len(conf), 'confirmed_kept': sum(1 for r_ in kept if r_[2] == 'yes'),
           'kept_rejected': sum(1 for r_ in kept if r_[2] != 'yes')}, open(os.path.join(HERE, 'number_check.json'), 'w'), indent=1)
