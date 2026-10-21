"""Label leakage: outputs that turn a USR label into content. Counts, per run, outputs with 'begin/began/beginning'
when the USR marks a name with the construction role 'begin' and the reference has no form of 'begin', and outputs with
'proximal/distal/respect' or relation labels (k1, k7p, r6 ...)."""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
it = {}
for d in ('tourism', 'health', 'geography'):
    for l in open(os.path.join(HERE, '..', 'inputs', d + '.jsonl'), encoding='utf-8'):
        j = json.loads(l); it[(d, j['id'])] = j
BEG = [k for k, j in it.items() if re.search(r':begin\b', j['usr']) and not re.search(r'\bbeg[iau]n', j['reference'], re.I)]
print('USRs with a name (begin) and no begin in the reference:', len(BEG))
res = {}
for m in ('groq_gpt-oss-120b', 'mistral_ministral-14b', 'ollama_gemma3-4b'):
    for c in ('raw', 'guide', 'gloss'):
        o = {}
        for l in open(os.path.join(HERE, 'outputs', '%s_%s.tsv' % (m, c)), encoding='utf-8'):
            x = l.rstrip('\n').split('\t', 2)
            if len(x) == 3:
                o[(x[0], x[1])] = x[2]
        b = sum(1 for k in BEG if re.search(r'\bbeg[iau]n', o.get(k, ''), re.I))
        lab = sum(1 for k in it if re.search(r'\b(proximal|distal|k1s?|k2|k7p?|k7t|r6|kriyAmUla|verbalizer|samuccaya|coref)\b', o.get(k, '')))
        res['%s_%s' % (m, c)] = dict(begin=b, labels=lab)
        print('%-28s begin %4d / %d   labels %4d' % (m + '_' + c, b, len(BEG), lab))
json.dump(dict(n_begin=len(BEG), runs=res), open(os.path.join(HERE, 'nle_label_leak.json'), 'w'), indent=1)
