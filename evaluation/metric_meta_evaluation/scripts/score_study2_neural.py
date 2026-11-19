#!/usr/bin/env python3
"""COMET (Unbabel/wmt22-comet-da) and BERTScore F1 (roberta-large, baseline-rescaled) for the 450 USR-route outputs of
Study 2 (150 sentences x 3 LLMs, thesis_runs v6b_few_v2chunks), with exactly the settings of
experiments/stats/semantic_metrics.py, so that the scores are comparable with the cached ones.

Run in the same environment as semantic_metrics.py (Linux/WSL, CPU is enough, ~10 minutes):
    ~/semenv/bin/python score_study2_neural.py
Output: study2_neural.json next to this script, keyed "system|domain|id"."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(HERE, '..', '..', 'experiments')
KEY = os.path.join(EXP, 'human_eval', 'human_eval_final_KEY.tsv')
FILES = {'final:groq_gpt-oss-120b': 'groq_gpt-oss-120b_v6b_few_v2chunks.tsv',
         'final:mistral_ministral-14b': 'mistral_ministral-14b_v6b_few_v2chunks.tsv',
         'final:ollama_gemma3-4b': 'ollama_gemma3-4b_v6b_few_v2chunks.tsv'}
REF = {}
for d in ('tourism', 'health', 'geography'):
    for l in open(os.path.join(EXP, 'inputs', d + '.jsonl'), encoding='utf-8'):
        r = json.loads(l)
        if r['reference']: REF[(d, r['id'])] = (r['hindi'], r['reference'])
SRC = {}
for l in open(os.path.join(EXP, 'exp1', 'exp1_input.tsv'), encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) == 3: SRC[(p[0], p[1])] = p[2]
sents = sorted({tuple(l.split('\t')[1:3]) for l in open(KEY, encoding='utf-8').read().splitlines()[1:]})
items = []
for s, fn in FILES.items():
    out = {}
    for l in open(os.path.join(EXP, 'thesis_runs', 'outputs', fn), encoding='utf-8'):
        p = l.rstrip('\n').split('\t', 2)
        if len(p) == 3: out[(p[0], p[1])] = p[2]
    for d, sid in sents:
        h, ref = REF[(d, sid)]
        items.append(('%s|%s|%s' % (s, d, sid), SRC.get((d, sid), h), out.get((d, sid), ''), ref))
print(len(items), 'items')
from bert_score import score
P, R, F = score([i[2] for i in items], [i[3] for i in items], lang='en', rescale_with_baseline=True, batch_size=16, verbose=True)
from comet import download_model, load_from_checkpoint
model = load_from_checkpoint(download_model('Unbabel/wmt22-comet-da'))
c = model.predict([dict(src=i[1], mt=i[2], ref=i[3]) for i in items], batch_size=16, gpus=0)
res = {i[0]: dict(comet=float(cs), bert=float(f)) for i, cs, f in zip(items, c.scores, F)}
json.dump(res, open(os.path.join(HERE, 'study2_neural.json'), 'w'), indent=0)
print('written', len(res))
