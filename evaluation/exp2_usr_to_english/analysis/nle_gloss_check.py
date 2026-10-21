"""Check of the E2c gloss: the verbalizer kara_1 ('do') of complex predicates received the dictionary English of
kara_1, which is the noun 'hand'. Counts the affected inputs and the outputs that contain a spurious 'hand'."""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
NL = chr(92) + 'n'
inp = {}
for l in open(os.path.join(HERE, 'exp2_input_gloss.tsv'), encoding='utf-8'):
    c = l.rstrip('\n').split('\t', 2); inp[(c[0], c[1])] = c[2].split(NL)
ref = {}
for d in ('tourism', 'health', 'geography'):
    for l in open(os.path.join(HERE, '..', 'inputs', d + '.jsonl'), encoding='utf-8'):
        j = json.loads(l); ref[(d, j['id'])] = j['reference']
hk = [k for k, rows in inp.items() if any(r.startswith('kara_1=hand') for r in rows)]
verb = sum(1 for rows in inp.values() for r in rows if r.startswith('kara_1=hand') and r.split()[-1].endswith('verbalizer'))
allr = sum(1 for rows in inp.values() for r in rows if r.startswith('kara_1=hand'))
print('inputs with kara_1=hand: %d; rows %d, of which verbalizer %d' % (len(hk), allr, verb))
for m in ('groq_gpt-oss-120b', 'mistral_ministral-14b', 'ollama_gemma3-4b'):
    o = {}
    for l in open(os.path.join(HERE, 'outputs', m + '_gloss.tsv'), encoding='utf-8'):
        c = l.rstrip('\n').split('\t', 2)
        if len(c) == 3:
            o[(c[0], c[1])] = c[2]
    n = sum(1 for k in hk if re.search(r'\bhand', o.get(k, ''), re.I) and not re.search(r'\bhand', ref[k], re.I))
    print(m, 'outputs with a spurious "hand": %d of %d' % (n, len(hk)))
