"""Rebuilds the E2c input (USR + English gloss of every concept) from exp2_input.tsv and checks it against
exp2_input_gloss.tsv, the input the models received.

Rules: every concept with a sense number gets the English of that sense from the concept dictionary
(analysis/resources/concept-to-mrs-rels.dat), e.g. xarSana_23=visit, mila_22=get-wA_hE_1. The light verb of a complex
predicate (construction role 'verbalizer', e.g. kara_1, ho_1) carries a conventional sense number that is not a
dictionary sense of the verb; it gets the English of the whole complex predicate from the generator's dictionary
(<kriyAmUla>+<light verb>_<n>, preferring the entry whose source list contains the USR's kriyAmUla sense), or else the
default English light verb (usr2chunk/tables/en/verbalizers.tsv), as in the rule-based generator.

  python build_gloss.py   ->  exp2_input_gloss_rebuilt.tsv (+ number of USRs identical to exp2_input_gloss.tsv)
"""
import collections, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
U2C = os.path.join(HERE, '..', '..', 'usr2chunk')
NL = chr(92) + 'n'

EN = {}                                                    # concept dictionary: sense -> English
for l in open(os.path.join(HERE, 'analysis', 'resources', 'concept-to-mrs-rels.dat'), encoding='utf-8'):
    c = l.split()
    if len(c) >= 4 and re.search(r'_\d+$', c[0]):
        e = re.sub(r'_\d+', '', c[3]).replace('+', ' ').strip()
        if e and e != '-':
            EN[c[0]] = e.replace(' ', '_')
CPEN, SL, CP = {}, {}, collections.defaultdict(list)       # generator's dictionary: complex predicates
for l in open(os.path.join(U2C, 'data', 'concept-to-mrs-rels.dat'), encoding='utf-8'):
    c = l.split()
    if len(c) < 4 or c[0] == 'cl':
        continue
    CPEN[c[1]] = re.sub(r'_\d+(?=$|\+)', '', c[3]).replace('+', ' ')
    SL[c[1]] = c[2].split(',')
    m = re.match(r'^(.+\+[A-Za-z]+)_(\d+)$', c[1])
    if m:
        CP[m.group(1)].append((int(m.group(2)), c[1]))
LIGHT = {}
for l in open(os.path.join(U2C, 'tables', 'en', 'verbalizers.tsv'), encoding='utf-8'):
    if l.strip() and not l.startswith('#'):
        a, b = l.rstrip('\n').split('\t')[:2]
        LIGHT[a] = b


def cp_english(kri, light_root):
    cands = sorted(CP.get('%s+%s' % (kri.rsplit('_', 1)[0], light_root), []))
    hit = next((k for _, k in cands if kri in SL.get(k, [])), None) or (cands[0][1] if cands else None)
    if hit and CPEN.get(hit, '-') not in ('-', ''):
        return CPEN[hit]
    return LIGHT.get(light_root, 'do')


def gloss_usr(usr):
    cells = [r.split(' ') for r in usr.split(NL)]
    kri = {c[8].split(':')[0]: re.sub(r'-.*$', '', c[0]) for c in cells if len(c) >= 9 and c[8].endswith(':kriyAmUla')}
    out = []
    for c in cells:
        if len(c) >= 9 and not c[0].startswith(('[', '$', '@')):
            m = re.match(r'^(.*?_\d+)(-.+)?$', c[0])
            if m:
                concept, tam = m.group(1), m.group(2) or ''
                if c[8].endswith(':verbalizer') and c[8].split(':')[0] in kri:
                    e = cp_english(kri[c[8].split(':')[0]], concept.split('_')[0]).replace(' ', '_')
                else:
                    e = EN.get(concept)
                if e:
                    c = [concept + '=' + e + tam] + c[1:]
        out.append(' '.join(c))
    return NL.join(out)


used = {}
for l in open(os.path.join(HERE, 'exp2_input_gloss.tsv'), encoding='utf-8'):
    d, i, u = l.rstrip('\n').split('\t')
    used[(d, i)] = u
same = n = 0
with open(os.path.join(HERE, 'exp2_input_gloss_rebuilt.tsv'), 'w', encoding='utf-8', newline='\n') as f:
    for l in open(os.path.join(HERE, 'exp2_input.tsv'), encoding='utf-8'):
        d, i, u = l.rstrip('\n').split('\t')
        g = gloss_usr(u)
        f.write('%s\t%s\t%s\n' % (d, i, g))
        n += 1; same += g == used.get((d, i))
print('rebuilt %d USRs; identical to exp2_input_gloss.tsv: %d' % (n, same))
