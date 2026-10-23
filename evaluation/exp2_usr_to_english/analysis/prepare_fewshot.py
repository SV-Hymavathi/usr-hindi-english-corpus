"""Condition E2d (few-shot): USR + guide + gloss (as E2c) + four worked examples (glossed USR -> correct English).

Examples (left out of the test set): G166 (pariNAma 'therefore', passive, plural), H100 (viroXI 'but', BI 'also', future,
addressee), 949 (names with begin/inside, cause rh), H184 (passive, BI 'also', modality 'can', participle).
Test set: 250 USRs drawn at random (seed 2026), stratified by domain (tourism 134, health 49, geography 67), from the
corrected glossed input (exp2_input_gloss_v2.tsv); the same 250 are compared with E2c.
Systems: groq_gpt-oss-120b_fewshot, mistral_ministral-14b_fewshot (same settings as their _gloss systems).

  python3 prepare_fewshot.py
  python3 run_exp2.py --only groq_gpt-oss-120b_fewshot mistral_ministral-14b_fewshot
"""
import json, os, random
HERE = os.path.dirname(os.path.abspath(__file__))
NL = chr(92) + 'n'
EXAMPLES = [('geography', 'G166', 'Therefore these are called temperate zones.'),
            ('health', 'H100', 'But you will also be safe from eye diseases.'),
            ('tourism', '949', 'This place is named Kallar because of the Kallar river.'),
            ('health', 'H184', 'The brain can also be kept sharp by adopting some good habits.')]
STRATA = {'tourism': 134, 'health': 49, 'geography': 67}

gloss = {}
for l in open(os.path.join(HERE, 'exp2_input_gloss_v2.tsv'), encoding='utf-8'):
    d, i, u = l.rstrip('\n').split('\t')
    gloss[(d, i)] = u
ex_keys = {(d, i) for d, i, _ in EXAMPLES}

block = 'EXAMPLES (glossed USR and the correct English sentence):\n'
for n, (d, i, en) in enumerate(EXAMPLES, 1):
    block += '\nExample %d\nUSR:\n%s\nEnglish: %s\n' % (n, gloss[(d, i)].replace(NL, '\n'), en)

R = random.Random(2026)
test = []
for d, k in STRATA.items():
    pool = sorted(key for key in gloss if key[0] == d and key not in ex_keys)
    test += R.sample(pool, k)
test.sort(key=lambda x: (list(STRATA).index(x[0]), x[1]))
with open(os.path.join(HERE, 'exp2_input_fewshot.tsv'), 'w', encoding='utf-8', newline='\n') as f:
    for d, i in test:
        f.write('%s\t%s\t%s\n' % (d, i, gloss[(d, i)]))

cfgp = os.path.join(HERE, 'config.json')
cfg = json.load(open(cfgp, encoding='utf-8'))
for m in ('groq_gpt-oss-120b', 'mistral_ministral-14b'):
    c = dict(cfg['systems'][m + '_gloss'])
    pu = c['prompt_user']
    assert '\n\nUSR:\n{usr}' in pu
    c['prompt_user'] = pu.replace('\n\nUSR:\n{usr}', '\n\n' + block + '\nNow write the English sentence for this USR.\n\nUSR:\n{usr}')
    c['input'] = 'exp2_input_fewshot.tsv'
    c['enabled'] = True
    cfg['systems'][m + '_fewshot'] = c
json.dump(cfg, open(cfgp, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
print('test USRs:', len(test), {d: sum(1 for x in test if x[0] == d) for d in STRATA})
print('systems added: groq_gpt-oss-120b_fewshot, mistral_ministral-14b_fewshot')
print('\n----- example block -----\n' + block)
