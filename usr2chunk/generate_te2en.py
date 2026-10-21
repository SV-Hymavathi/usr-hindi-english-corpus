"""usr2chunk for TELUGU USRs -> English chunks. Rules and tables only, no model calls.
Telugu rule layer (tables/te/canonical.tsv): Telugu function concepts (copula ఉండు, light verbs), Telugu TAM labels and
Telugu particles are mapped to the generator's function inventory; Telugu content concepts are looked up in
data/te/concept-te-en.dat. generate.py and tables/en are imported unchanged, so the Hindi/English results do not change.
Usage: python generate_te2en.py data/te/te_usr_10.txt [gold.tsv]"""
import os, re, sys, json, tempfile
import generate as G
HERE = os.path.dirname(os.path.abspath(__file__))
CAN = {'concept': {}, 'tam': {}, 'marker': {}}
for _f in ('canonical.tsv', 'canonical_auto.tsv'):
    _p = os.path.join(HERE, 'tables', 'te', _f)
    if not os.path.exists(_p): continue
    for l in open(_p, encoding='utf-8'):
        c = l.rstrip('\n').split('\t')
        if len(c) == 3 and not l.startswith('#'): CAN[c[0]].setdefault(c[1], c[2])


def canonical_line(line):
    c = line.split()
    if len(c) < 9 or line.startswith(('#', '%', '<')): return line
    con, tam = c[0], ''
    if '-' in con and not con.startswith(('[', '@', '$')): con, tam = con.split('-', 1)
    con = CAN['concept'].get(con, con)
    if tam: con = con + '-' + CAN['tam'].get(tam, tam)
    c[0] = con
    if c[6] != '-': c[6] = '/'.join(CAN['marker'].get(m, m) for m in c[6].split('/'))
    return ' '.join(c)


def run(path):
    G.load_dict()                                                   # shared dictionary (function inventory)
    # concepts the rule layer maps to keep their shared entry even if a Telugu concept has the same spelling (aneka_1)
    keep = {k: (G.EN.get(k), G.SL.get(k), G.POS.get(k)) for k in CAN['concept'].values() if k in G.EN}
    G.load_dict(os.path.join(HERE, 'data', 'te', 'concept-te-en.dat'))   # Telugu content concepts -> English
    for k, (en, sl, pos) in keep.items(): G.EN[k], G.SL[k], G.POS[k] = en, sl, pos
    txt = '\n'.join(canonical_line(l.rstrip('\n')) for l in open(path, encoding='utf-8'))
    tmp = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8'); tmp.write(txt); tmp.close()
    sents = G.read_usrs(tmp.name); os.unlink(tmp.name)
    G.ALL_SENTS.update({x.sid: x for x in sents})
    out = {}
    for s in sents:
        try: out[s.sid] = G.generate(s)
        except Exception as e: out[s.sid] = '[ERROR %s]' % type(e).__name__
    return sents, out


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sents, out = run(sys.argv[1])
    for s in sents: print('%s\t%s\t%s' % (s.sid, s.hindi, out[s.sid]))
