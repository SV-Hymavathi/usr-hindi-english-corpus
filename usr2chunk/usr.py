"""usr.py sid [sid...] : print parsed USR rows (concept idx sem gnp head:rel spk cx:role)"""
import sys
import generate as G
G.load_dict()
want = set(sys.argv[1:])
for s in G.read_usrs('/root/projects/multilingual_rule_based_updated/gen_input_final.txt'):
    if s.sid in want:
        print('==', s.sid, s.stype, '|', s.hindi)
        for n in s.nodes:
            print('   %-22s %-4s %-6s %-5s %-10s %-14s %-12s en=%s' % (n.concept, n.idx, n.sem, n.gnp, '%s:%s' % (n.head, n.rel), n.spk, '%s:%s' % (n.cx, n.role), G.EN.get(n.root, '')))
