"""Windows dry run (no Apertium): English morphology falls back to the rule-based inflection in morph.py.
Runs the SAME 10 sentences from the Hindi USRs and from the Telugu USRs and compares both with the gold chunks.
The real evaluation is run in WSL with Apertium (generate_te2en.py)."""
import json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8')
import morph
if '--real' not in sys.argv:                          # in WSL: python3 dryrun_te_vs_hi.py 40 --real (uses Apertium)
    morph._LtProc.query = lambda self, text: ''      # dry run only: no lt-proc on Windows
import generate as G
import generate_te2en as T
HERE = os.path.dirname(os.path.abspath(__file__))
N = sys.argv[1] if len(sys.argv) > 1 else '10'      # a number or 'checked'
xs = [json.loads(l) for l in open(os.path.join(HERE, '..', '..', 'experiments', 'inputs', 'tourism.jsonl'), encoding='utf-8')]
from corrected_usrs import corrected_usrs
_CU = corrected_usrs()
for _x in xs: _x['usr'] = _CU.get(_x['id'], _x['usr'])   # use the corrected USRs
_te_ids = [l.strip().split('=')[1].rstrip('>') for l in open(os.path.join(HERE, 'data', 'te', 'te_usr_%s.txt' % N), encoding='utf-8') if l.startswith('<sent_id=')]
xs = [x for x in xs if x['id'] in set(_te_ids)]
tmp = os.path.join(HERE, 'data', 'te', '_hi_%s.txt' % N)
open(tmp, 'w', encoding='utf-8').write('\n'.join('<sent_id=%s>\n#%s\n%s\n</sent_id>' % (x['id'], x['hindi'], x['usr']) for x in xs) + '\n')
G.load_dict(); hs = G.read_usrs(tmp); G.ALL_SENTS.update({s.sid: s for s in hs})
hi = {s.sid: G.generate(s) for s in hs}
_, te = T.run(os.path.join(HERE, 'data', 'te', 'te_usr_%s.txt' % N))
norm = lambda t: re.sub(r'\s+', ' ', t.strip().lower())
same = gte = ghi = 0
for x in xs:
    i = x['id']
    a, b, g = hi[i], te.get(i, ''), x['gold_chunks']
    same += norm(a) == norm(b); ghi += norm(a) == norm(g); gte += norm(b) == norm(g)
    print('%s\n  GOLD   : %s\n  from HI: %s\n  from TE: %s%s' % (i, g, a, b, '' if norm(a) == norm(b) else '   <-- differs'))
print('\nTelugu USR output = Hindi USR output: %d/%d | exact match with gold: Hindi %d/%d, Telugu %d/%d' % (same, len(xs), ghi, len(xs), gte, len(xs)))
