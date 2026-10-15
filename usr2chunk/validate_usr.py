"""validate_usr.py <usr_file> [out.csv]
Structural USR checks that block faithful generation (the generator never guesses around them):
  - head index that does not exist
  (dependents of NE members / cp parts are USR conventions the generator normalises; not reported)
  - main verb missing or duplicated
  - k1 / k2 attached to a non-verbal head
  - concept ID with no dictionary entry"""
import csv
import sys
import generate as G

G.load_dict()
rows = []
for s in G.read_usrs(sys.argv[1]):
    mains = [n for n in s.nodes if n.rel == 'main']
    for a_, b_ in getattr(s, 'cycles', []):
        rows.append([s.sid, a_, 'dependency cycle with %s (loop broken)' % b_, s.hindi])
    if getattr(s, 'read_error', ''):
        rows.append([s.sid, '-', 'unreadable USR block: ' + s.read_error, s.hindi])
    if len(mains) != 1:
        rows.append([s.sid, '-', 'main verb count = %d' % len(mains), s.hindi])
    for n in s.nodes:
        if n.head and n.head != '0':
            h = s.by.get(n.head)
            if h is None:
                rows.append([s.sid, n.concept, 'head %s does not exist' % n.head, s.hindi])
            elif n.rel in ('k1', 'k2') and h.rel not in ('main',) and not G.is_verbal(h) and h.kind != 'cp' and 'kqw' not in (h.gnp or '')                     and h.role not in ('kriyAmUla', 'verbalizer'):
                rows.append([s.sid, n.concept, '%s attached to non-verbal head %s (%s)' % (n.rel, n.head, h.concept), s.hindi])
        r = n.root.lstrip('^')
        if '_' in r and r.rsplit('_', 1)[1].isdigit() and r not in G.EN and not r.startswith(('$', '[', '@')) \
                and not r.split('_')[0].replace('.', '').isdigit() and n.role != 'verbalizer':
            rows.append([s.sid, n.concept, 'concept id not in dictionary', s.hindi])
out = sys.argv[2] if len(sys.argv) > 2 else None
if out:
    with open(out, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['sent_id', 'concept', 'issue', 'hindi'])
        w.writerows(rows)
print('%d issues in %d sentences' % (len(rows), len({r[0] for r in rows})))
for r in rows[:40]:
    print(' ', r[0], r[1], '|', r[2])
