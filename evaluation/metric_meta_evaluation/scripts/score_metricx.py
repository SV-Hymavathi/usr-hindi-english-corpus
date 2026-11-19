#!/usr/bin/env python3
"""MetricX-24 (google/metricx-24-hybrid-large-v2p6, reference-based mode) for every rated output of both studies.
Follows the reference implementation (google-research/metricx): input "source: ... candidate: ... reference: ...",
EOS removed from the input, one decoder step with decoder input 0, score = logit of token 250089 clipped to [0, 25].
MetricX is an ERROR score: lower is better.  Run in WSL:  ~/semenv/bin/python score_metricx.py
Output: metricx.json  {"sys|domain|id": score}"""
import json, os, sys, time, torch
from transformers import AutoTokenizer, MT5ForConditionalGeneration
HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(HERE, '..', '..', '..', 'experiments')
SEG = json.load(open(os.path.join(HERE, '..', 'segments.json'), encoding='utf-8'))
SRC = {}
for l in open(os.path.join(EXP, 'exp1', 'exp1_input.tsv'), encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) == 3: SRC[(p[0], p[1])] = p[2]
OUT = os.path.join(HERE, 'metricx.json')
done = json.load(open(OUT)) if os.path.exists(OUT) else {}
items = {}
for r in SEG:
    k = '%s|%s|%s' % (r['sys'], r['dom'], r['sid'])
    if k not in done: items[k] = 'source: %s candidate: %s reference: %s' % (SRC[(r['dom'], r['sid'])], r['out'], r['ref'])
print(len(items), 'to score;', len(done), 'already done', flush=True)
torch.set_num_threads(max(1, os.cpu_count() - 2))
tok = AutoTokenizer.from_pretrained('google/mt5-large')
model = MT5ForConditionalGeneration.from_pretrained('google/metricx-24-hybrid-large-v2p6', torch_dtype=torch.bfloat16)
model.eval()
keys = list(items); B = 8; t0 = time.time()
for i in range(0, len(keys), B):
    ks = keys[i:i + B]
    enc = [tok(items[k], truncation=True, max_length=1536)['input_ids'][:-1] for k in ks]   # drop EOS
    L = max(len(e) for e in enc)
    ids = torch.tensor([e + [tok.pad_token_id] * (L - len(e)) for e in enc])
    att = torch.tensor([[1] * len(e) + [0] * (L - len(e)) for e in enc])
    with torch.no_grad():
        out = model(input_ids=ids, attention_mask=att, decoder_input_ids=torch.zeros((len(ks), 1), dtype=torch.long))
    pred = torch.clamp(out.logits[:, 0, 250089].float(), 0, 25).tolist()
    for k, v in zip(ks, pred): done[k] = v
    if (i // B) % 10 == 0:
        json.dump(done, open(OUT, 'w')); print('%d/%d  %.0fs' % (i + len(ks), len(keys), time.time() - t0), flush=True)
json.dump(done, open(OUT, 'w')); print('written', len(done), flush=True)
