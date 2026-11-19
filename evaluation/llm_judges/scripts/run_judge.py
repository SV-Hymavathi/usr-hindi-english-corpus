#!/usr/bin/env python3
"""LLM-as-judge for the 2,384 rated outputs (Study 1 and Study 2). The judge sees what the annotators saw (Hindi source,
English reference, output), uses the annotators' adequacy scale, and says whether information was added, omitted or
changed. Resumable (appends to judge_<name>.jsonl); rotates over the API keys on rate limits.
Usage (WSL):  python3 run_judge.py gptoss|qwen [n_items]"""
import json, os, re, sys, time, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__))
SEG = os.path.join(HERE, '..', 'lre_metrics', 'segments.json')
KEYS = json.load(open(os.path.join(HERE, '..', '..', 'experiments', 'exp1', 'keys.json')))
EXP = os.path.join(HERE, '..', '..', 'experiments')
JUDGES = {'gptoss': ('https://api.groq.com/openai/v1/chat/completions', 'openai/gpt-oss-120b', 'groq'),
          'qwen': ('https://api.groq.com/openai/v1/chat/completions', 'qwen/qwen3.8-27b', 'groq'),
          'qwen_noref': ('https://api.groq.com/openai/v1/chat/completions', 'qwen/qwen3.8-27b', 'groq')}
NAME = sys.argv[1]
NOREF = NAME.endswith('_noref')
URL, MODEL, PROV = JUDGES[NAME]
KEYLIST = KEYS[PROV] if isinstance(KEYS[PROV], list) else [KEYS[PROV]]
OUT = os.path.join(HERE, 'judge_%s.jsonl' % NAME)
SRC = {}
for l in open(os.path.join(EXP, 'exp1', 'exp1_input.tsv'), encoding='utf-8'):
    p = l.rstrip('\n').split('\t')
    if len(p) == 3: SRC[(p[0], p[1])] = p[2]
SYSTEM = ('You are an expert evaluator of translations from Hindi into English. You judge meaning, not style. '
          'Answer only with a JSON object.')
PROMPT = '''Hindi source sentence:
{src}

English reference translation (a guide only; other wordings of the same meaning are acceptable):
{ref}

English output to evaluate:
{out}

Rate the ADEQUACY of the output: how much of the meaning of the Hindi source it preserves.
5 = all meaning preserved; 4 = minor nuance lost; 3 = part of the meaning wrong or missing;
2 = main meaning wrong or largely missing; 1 = unrelated or no translation.
Judge meaning only: plain or literal wording, word order and transliterated Indian names are not errors if the meaning is kept.

Also answer:
- added: does the output add information that is not in the source (yes/no)?
- omitted: does the output leave out information that is in the source (yes/no)?
- changed: does the output change information, for example a wrong name, place, number or claim (yes/no)?

Return exactly: {{"adequacy": <1-5>, "added": "yes|no", "omitted": "yes|no", "changed": "yes|no"}}'''
if NOREF:   # same prompt without the reference translation
    PROMPT = PROMPT.replace('''English reference translation (a guide only; other wordings of the same meaning are acceptable):
{ref}

''', '')
    assert '{ref}' not in PROMPT

seg = json.load(open(SEG, encoding='utf-8'))
items, seen = [], set()
for r in seg:
    k = '%s|%s|%s' % (r['sys'], r['dom'], r['sid'])
    if k in seen: continue
    seen.add(k); items.append((k, SRC.get((r['dom'], r['sid'])), r['ref'], r['out']))
done = set()
if os.path.exists(OUT):
    for l in open(OUT, encoding='utf-8'):
        try: done.add(json.loads(l)['key'])
        except Exception: pass
todo = [it for it in items if it[0] not in done]
if len(sys.argv) > 2: todo = todo[:int(sys.argv[2])]
print(NAME, MODEL, '|', len(items), 'unique outputs;', len(done), 'done;', len(todo), 'to do;', len(KEYLIST), 'keys', flush=True)
ki = 0


def parse(text):
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.S)
    m = re.search(r'\{[^{}]*"adequacy"[^{}]*\}', text, flags=re.S)
    if not m: raise ValueError('no json: ' + text[:120])
    d = json.loads(m.group(0))
    d['adequacy'] = int(d['adequacy'])
    assert 1 <= d['adequacy'] <= 5
    return d


def call(src, ref, out):
    global ki
    payload = {'model': MODEL, 'temperature': 0, 'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': (PROMPT.format(src=src, out=out) if NOREF else PROMPT.format(src=src, ref=ref, out=out))}]}
    if NAME == 'gptoss': payload['reasoning_effort'] = 'low'
    if NAME.startswith('qwen'): payload['reasoning_effort'] = 'none'
    body = json.dumps(payload).encode()
    last = None
    for attempt in range(3 * len(KEYLIST)):
        key = KEYLIST[ki % len(KEYLIST)]
        try:
            req = urllib.request.Request(URL, data=body, headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json', 'User-Agent': 'eval-script'})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return parse(json.loads(resp.read())['choices'][0]['message']['content'])
        except urllib.error.HTTPError as e:
            last = 'HTTP %d %s' % (e.code, e.read()[:150])
            if e.code == 400 and 'reasoning_effort' in last:
                payload.pop('reasoning_effort', None); body = json.dumps(payload).encode(); continue
            ki += 1                                   # rotate key on rate limit or server error
            if e.code not in (429, 500, 502, 503, 413): raise RuntimeError(last)
            time.sleep(1 if e.code == 429 else 3)
        except (ValueError, AssertionError, KeyError) as e:
            last = 'parse ' + str(e)[:150]; time.sleep(1)
        except Exception as e:
            last = 'net ' + str(e)[:150]; time.sleep(3)
    raise RuntimeError('failed: ' + str(last))


t0 = time.time()
with open(OUT, 'a', encoding='utf-8') as f:
    for n, (k, src, ref, out) in enumerate(todo, 1):
        res = call(src, ref, out)
        f.write(json.dumps({'key': k, 'model': MODEL, **res}, ensure_ascii=False) + '\n'); f.flush()
        if n % 50 == 0 or n == len(todo): print('%d/%d  %.0fs' % (n, len(todo), time.time() - t0), flush=True)
        ki += 1                                      # spread load over the keys
print('finished', flush=True)
