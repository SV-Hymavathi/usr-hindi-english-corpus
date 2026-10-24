"""Build Telugu USRs from the Hindi USRs (same structure; concept, TAM and particle layers in Telugu) and the
Telugu -> English concept dictionary. Rules and tables only, no model calls.
  in : ../../experiments/inputs/tourism.jsonl, ../../telugu/data/te2en/te250_gold.tsv,
       data/te/hi2te_verified.tsv, tables/te/tam_hi2te.tsv, tables/te/marker_hi2te.tsv
  out: data/te/te_usr_<n>.txt  (Telugu USRs, '#' line = gold Telugu sentence)
       data/te/concept-te-en.dat (Telugu concept -> English sense + MRS predicate, in the shared dictionary format)
Usage: python build_te_usr.py 10"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
N = sys.argv[1] if len(sys.argv) > 1 else '10'      # a number (first N USRs) or 'checked' (all gold-checked sentences)


def tsv(p):
    return [l.rstrip('\n').split('\t') for l in open(p, encoding='utf-8') if l.strip() and not l.startswith('#')]


from te2wx import te2wx
HI = {}
for l in open(os.path.join(HERE, 'data', 'concept-to-mrs-rels.dat'), encoding='utf-8'):
    c = l.split()
    if len(c) >= 4 and c[0] != 'cl': HI[c[1]] = c          # last row wins, as in generate.load_dict
# Telugu function concepts are mapped back to the generator's inventory by tables/te/canonical.tsv: keep their WX as given
FUNC = {r[1] for r in tsv(os.path.join(HERE, 'tables', 'te', 'canonical.tsv')) if r[0] == 'concept'}
EN_OVR = {r[0]: r[1] for r in tsv(os.path.join(HERE, 'data', 'te', 'te_overrides.tsv'))}
FUNC_HI = {r[0] for r in tsv(os.path.join(HERE, 'tables', 'te', 'function_hi.tsv'))}   # Hindi function concepts rules key on
# Hindi concept -> (Telugu WX root, English). Roots are derived from the Telugu script (case-sensitive WX).
ALIGN = []
for f in ('hi2te_verified.tsv', 'hi2te_batch2.tsv', 'hi2te_batch3.tsv', 'hi2te_batch4.tsv'):        # later batches add concepts of newly confirmed sentences
    p = os.path.join(HERE, 'data', 'te', f)
    if not os.path.exists(p): continue
    for r in tsv(p):
        if r[1] == '-': ALIGN.append((r[0], '-', None, r[2] if len(r) > 2 else '')); continue
        wx = r[1] if r[1] in FUNC else te2wx(r[2]) if len(r) > 2 and r[2] not in ('', '-') else re.sub(r'_\d+$', '', r[1])
        en = EN_OVR.get(r[0]) or (HI[r[0]][3] if r[0] in HI else None)
        ALIGN.append((r[0], wx, en, r[2] if len(r) > 2 else ''))
# sense numbers: one sense per distinct English meaning of the same Telugu root
SENSES, C, TEDICT = {}, {}, []
for hi, wx, en, scr in ALIGN:
    if wx == '-': C[hi] = '-'; continue
    if re.search(r'_\d+$', wx): C[hi] = wx; continue            # function concept with explicit WX + sense
    meaning = re.sub(r'_\d+$', '', en or hi)
    s = SENSES.setdefault(wx, [])
    if meaning not in s: s.append(meaning)
    # sense numbers already taken by a function concept of the same root (e.g. uMdu_1 copula, ceyu_7 light verb) are skipped
    free = [k for k in range(1, 100) if '%s_%d' % (wx, k) not in FUNC]
    C[hi] = '%s_%d' % (wx, free[s.index(meaning)])
    TEDICT.append((C[hi], scr, en, hi))
FUSE = [(r[0], r[1], r[2], r[3] if len(r) > 3 else '-') for r in tsv(os.path.join(HERE, 'data', 'te', 'te_name_fusions.tsv'))]


def fuse_names(lines):
    """General rule: an honorific modifier that depends on a name which Telugu expresses as ONE name
    (te_name_fusions.tsv) is removed, and the name becomes that Telugu name. Works on USR structure only."""
    rows = [l.split() for l in lines]
    idx = {c[1]: c for c in rows if len(c) >= 9}
    members = {}                                   # ne index -> member rows in order
    for c in rows:
        if len(c) >= 9 and c[8] != '-' and c[8].split(':')[0] in idx and idx[c[8].split(':')[0]][0].startswith('[ne_'):
            members.setdefault(c[8].split(':')[0], []).append(c)
    drop, repl = set(), {}
    for c in rows:
        if len(c) < 9 or c[4] == '-': continue
        for mod, name, te, cat in FUSE:
            if c[0] != mod: continue
            head = c[4].split(':')[0]
            h = idx.get(head)
            if not h: continue
            mem = members.get(head, [])
            if mem and ' '.join(m[0] for m in mem) == name:      # name is a named-entity construction
                drop.add(c[1]); repl[mem[0][1]] = (te2wx(te), None)
                drop.update(m[1] for m in mem[1:])
            elif re.sub(r'-.*', '', h[0]) == name and te == '-':  # phrase: Telugu uses the head's own word
                drop.add(c[1])
            elif h[0] == name:                                    # name is a concept row
                drop.add(c[1]); repl[h[1]] = (te2wx(te), cat)
    out = []
    for c, l in zip(rows, lines):
        if len(c) >= 9 and c[1] in drop: continue
        if len(c) >= 9 and c[1] in repl:
            c[0] = repl[c[1]][0]
            if repl[c[1]][1] not in (None, '-') and c[2] == '-': c[2] = repl[c[1]][1]
            out.append(' '.join(c)); continue
        out.append(l)
    return out
TAM = {r[0]: r[1] for r in tsv(os.path.join(HERE, 'tables', 'te', 'tam_hi2te.tsv'))}
MK = {r[0]: r[1] for r in tsv(os.path.join(HERE, 'tables', 'te', 'marker_hi2te.tsv'))}
GOLD = {r[0]: r[4] for r in tsv(os.path.join(HERE, '..', '..', 'telugu', 'data', 'te2en', 'te250_gold.tsv'))[1:]}
xs = [json.loads(l) for l in open(os.path.join(HERE, '..', '..', 'experiments', 'inputs', 'tourism.jsonl'), encoding='utf-8')]
from corrected_usrs import corrected_usrs
_CU = corrected_usrs()
for _x in xs: _x['usr'] = _CU.get(_x['id'], _x['usr'])   # use the corrected USRs
CHECKED = {r[0] for r in tsv(os.path.join(HERE, '..', '..', 'telugu', 'data', 'te2en', 'te250_gold.tsv'))[1:] if len(r) > 6 and r[6] == 'checked'}
xs = [x for x in xs if x['id'] in CHECKED] if N == 'checked' else xs[:int(N)]
missing, used, VERBALIZER = set(), {}, {}
CPKRI = set()                       # Hindi kriyAmUla concepts that occur in these USRs (only their cp entries are copied)
for x in xs:
    for line in x['usr'].split('\n'):
        c = line.split()
        if len(c) >= 9 and c[8].endswith(':kriyAmUla'): CPKRI.add(c[0])
        if len(c) >= 9 and '[shade:' in c[6]: CPKRI.add(re.sub(r'-.*', '', c[0]))   # verb + vector-verb idioms (Ko+jA = get lost)
out = []
for x in xs:
    rows = []
    NE = {l.split()[1] for l in x['usr'].split('\n') if l.startswith('[ne_') and len(l.split()) > 1}   # indices of name heads
    for line in fuse_names(x['usr'].split('\n')):
        c = line.split()
        if len(c) < 9 or line.startswith(('%', '#')):
            rows.append(line); continue
        con = c[0]; tam = ''
        if not re.search(r'_\d+', con) and not con.startswith(('[', '$', '@')) and c[8] == '-':
            rows.append(line); continue                            # a (fused) Telugu name: keep as it is
        m =re.match(r'^([^\[\]$@]+?_\d+)-(.+)$', con)
        if m: con, tam = m.group(1), m.group(2)
        elif con.endswith('-pres') or con.endswith('-past'): con, tam = con.rsplit('-', 1)
        in_name = c[8] != '-' and c[8].split(':')[0] in NE      # members of a name stay as they are (transliterated)
        if re.search(r'_\d+$', con) and not con.startswith(('[', '$', '@')) and not in_name and not re.match(r'^[\d.]+_\d+$', con):
            if con in C and C[con] == '-': continue     # the Telugu gold has no word for this concept: drop the row
            if con in C:
                used[C[con]] = con
                if c[8].endswith(':verbalizer'): VERBALIZER[C[con]] = con   # Telugu light verb -> generator's light verb
                if re.sub(r'_\d+$', '', con) in FUNC_HI: VERBALIZER[C[con]] = con   # rule-keyed function concept
                con = C[con]
            else: missing.add(con)
        if tam: tam = TAM.get(tam, tam); con = con + '-' + tam
        c[0] = con
        c[6] = '/'.join(MK.get(m_, m_) for m_ in c[6].split('/')) if c[6] != '-' else '-'
        rows.append(' '.join(c))
    out.append('<sent_id=%s>\n#%s\n%s\n</sent_id>' % (x['id'], GOLD.get(x['id'], ''), '\n'.join(rows)))
open(os.path.join(HERE, 'data', 'te', 'te_usr_%s.txt' % N), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
# Telugu -> English dictionary: the English sense and MRS predicate of the Hindi concept it was aligned with
with open(os.path.join(HERE, 'data', 'te', 'concept-te-en.dat'), 'w', encoding='utf-8') as f:
    f.write('cl hl sl el mrsc\n')
    for te, hi in sorted(used.items()):
        r = HI.get(hi)
        ov = EN_OVR.get(hi, '').split()
        en = ov[0] if ov else (r[3] if r else None)
        mrs = ov[1] if len(ov) > 1 else ('-' if ov else (r[4] if r and len(r) > 4 else '-'))
        if en: f.write('%s %s - %s %s\n' % (te, te, en, mrs))
# human-readable Telugu concept dictionary (all aligned concepts, not only those in these USRs)
with open(os.path.join(HERE, 'data', 'te', 'te_dictionary.tsv'), 'w', encoding='utf-8') as f:
    f.write('# Telugu concept (WX, case-sensitive)\tTelugu\tEnglish\tHindi concept aligned\n')
    for te, scr, en, hi in sorted(set(TEDICT)):
        f.write('%s\t%s\t%s\t%s\n' % (te, scr, en, hi))
with open(os.path.join(HERE, 'data', 'te', 'concept-te-en.dat'), 'a', encoding='utf-8') as f:
    # complex predicates: Telugu kriyAmUla + light verb carry the Hindi cp's dictionary entry (looked up as a whole)
    # Every Telugu root aligned with a Hindi kriyAmUla gets that kriyAmUla's entries. Column 3 names the kriyAmUla sense an
    # entry is for (the generator prefers that entry), so it is carried over in Telugu. When one Telugu root + light verb
    # collects entries of several Hindi kriyAmUlas (prawIwa+ho 'seem' and mana+ho 'wish' -> anipiMcu+ho), the entries are
    # renumbered so keys stay distinct, and an untagged entry is tagged with the Telugu senses aligned with its own
    # kriyAmUla that no other entry of that kriyAmUla claims, so each Telugu sense still finds its own Hindi entry.
    # whole-compound entries (kaluRa_1+vinASanI_1 = 'blemish destroyer'): copied when every member has a Telugu concept
    hi2te = {h: te for te, h in used.items()}
    for key, r in list(HI.items()):
        parts = key.split('+')
        if len(parts) > 1 and all(re.search(r'_\d+$', p) and p in hi2te for p in parts):
            k = '+'.join(hi2te[p] for p in parts)
            f.write(k + ' ' + k + ' - ' + r[3] + ' ' + (r[4] if len(r) > 4 else '-') + '\n')
    te_of = {}                                       # Hindi kriyAmUla concept -> Telugu concept
    for te, h in used.items():
        if h in CPKRI: te_of[h] = te
    for h in CPKRI:
        if h in C and C[h] != '-' and h not in te_of: te_of[h] = C[h]
    groups = {}                                      # (Telugu root, light verb) -> [(Hindi base, n, sl Telugu, row)]
    for key, r in list(HI.items()):
        m = re.match(r'^(.+)\+([A-Za-z]+)_(\d+)$', key)
        if not m: continue
        base, lv = m.group(1), m.group(2)
        senses = {h: te for h, te in te_of.items() if re.sub(r'_\d+$', '', h) == base}
        sl = r[2].split(',') if r[2] != '-' else []
        for root in sorted({re.sub(r'_\d+$', '', te) for te in senses.values()}):
            slte = [senses[s] for s in sl if s in senses and re.sub(r'_\d+$', '', senses[s]) == root]
            groups.setdefault((root, lv), []).append((base, int(m.group(3)), slte, sl, r, senses))
    for (root, lv), ents in groups.items():
        multi = len({e[0] for e in ents}) > 1
        for i, (base, n, slte, sl, r, senses) in enumerate(sorted(ents, key=lambda e: (e[0], e[1]))):
            if multi and not sl:
                claimed = {s for e in ents if e[0] == base for s in e[3]}
                slte = sorted(te for h, te in senses.items() if h not in claimed and re.sub(r'_\d+$', '', te) == root)
            k = '%s+%s_%d' % (root, lv, i + 1 if multi else n)
            f.write(k + ' ' + k + ' ' + (','.join(slte) or '-') + ' ' + r[3] + ' ' + (r[4] if len(r) > 4 else '-') + '\n')
# light verbs of complex predicates map back to the generator's light verbs (general rule, by USR role 'verbalizer')
with open(os.path.join(HERE, 'tables', 'te', 'canonical_auto.tsv'), 'w', encoding='utf-8') as f:
    f.write('# generated by build_te_usr.py: Telugu light verbs (USR role verbalizer) -> generator light verbs\n')
    for te, hi in sorted(VERBALIZER.items()): f.write('concept\t%s\t%s\n' % (te, hi))
print('USRs', len(xs), 'Telugu concepts', len(used), 'Hindi concepts without a verified Telugu entry:', sorted(missing))
