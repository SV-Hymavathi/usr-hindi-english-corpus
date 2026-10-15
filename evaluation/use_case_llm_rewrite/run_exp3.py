#!/usr/bin/env python3
"""Experiment 3: rewrite the rule-based generator's chunks as one fluent English sentence; every Hindi sentence (tourism, health, geography) with each enabled system.

  python3 run_exp3.py              run all enabled systems in parallel (one thread each)
  python3 run_exp3.py --only groq_llama3.3-70b google_translate
  python3 run_exp3.py --limit 5    quick trial: first 5 sentences of each domain
  python3 run_exp3.py --status     show progress per system and stop

Resumable: every answer is appended at once to outputs/<system>.tsv; a rerun skips what is done.
Daily limits: a key that reports a per-day limit is parked until tomorrow (state.json) and the next key is used;
when all keys of a system are parked, that system stops and the others continue.
Then run  python3 collect_exp3.py  to build exp3_outputs.xlsx (one sheet per system)."""
import argparse, json, os, re, sys, threading, time, datetime, urllib.request, urllib.parse, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, 'config.json'), encoding='utf-8'))
KEYS = json.load(open(os.path.join(HERE, '..', 'exp1', 'keys.json'), encoding='utf-8'))   # same keys as Experiment 1
INPUT = os.path.join(HERE, 'exp3_input.tsv')            # domain <TAB> id <TAB> generator chunks
OUTD = os.path.join(HERE, 'outputs'); os.makedirs(OUTD, exist_ok=True)
STATE = os.path.join(HERE, 'state.json')
LOCK = threading.Lock()
TODAY = datetime.date.today().isoformat()


class DailyLimit(Exception):
    pass


class Fatal(Exception):
    pass


def load_state():
    try:
        s = json.load(open(STATE, encoding='utf-8'))
    except Exception:
        s = {}
    return s if s.get('date') == TODAY else {'date': TODAY, 'parked': {}}


def save_state(s):
    with LOCK:
        json.dump(s, open(STATE, 'w', encoding='utf-8'), indent=1)


def http(url, data=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                 headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0 (exp1-runner)', **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')[:500]
        if e.code == 429 or 'quota' in body.lower() or 'rate limit' in body.lower():
            daily = re.search(r'per day|\bRPD\b|\bTPD\b|daily|quota exceeded|exceeded your current quota|PerDay', body, re.I)
            raise DailyLimit(body) if daily else RuntimeError('RATE ' + body)
        if e.code in (401, 403):
            raise Fatal('HTTP %d (bad or unauthorised key): %s' % (e.code, body))
        raise RuntimeError('HTTP %d: %s' % (e.code, body))


def clean(t):
    t = (t or '').strip()
    t = re.sub(r'^(english( translation)?\s*:\s*)', '', t, flags=re.I)
    t = t.split('\n')[0].strip().strip('"').strip()
    return t


# ---------- one call per system type ----------
def call_openai(cfg, key, hindi):
    body = {'model': cfg['model'], 'temperature': 0, 'max_tokens': 300,
            'messages': [{'role': 'system', 'content': CFG['prompt_system']},
                         {'role': 'user', 'content': CFG['prompt_user'].format(chunks=hindi)}]}
    body.update(cfg.get('extra', {}))                 # provider-specific options, e.g. reasoning_effort
    h = {} if cfg['provider'] == 'ollama' else {'Authorization': 'Bearer ' + key}
    return clean(http(cfg['url'], body, h, timeout=(600 if cfg['provider'] == 'ollama' else 60))['choices'][0]['message']['content'])


def call_gemini(cfg, key, hindi):
    url = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s' % (cfg['model'], key)
    body = {'systemInstruction': {'parts': [{'text': CFG['prompt_system']}]},
            'contents': [{'role': 'user', 'parts': [{'text': CFG['prompt_user'].format(chunks=hindi)}]}],
            'generationConfig': {'temperature': 0, 'maxOutputTokens': 300}}
    r = http(url, body)
    return clean(''.join(p.get('text', '') for p in r['candidates'][0]['content']['parts']))


def call_google(cfg, key, hindi):
    url = 'https://translate.googleapis.com/translate_a/single?client=gtx&sl=hi&tl=en&dt=t&q=' + urllib.parse.quote(hindi)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            j = json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 429:                       # free endpoint blocks for a few minutes, not a day
            time.sleep(60)
            raise RuntimeError('google 429: paused 60 s')
        raise
    return ''.join(seg[0] for seg in j[0] if seg[0]).strip()


_BH = {}


def call_bhashini(cfg, key, hindi):
    """IndicTrans2 through the Bhashini ULCA pipeline (userID + ulcaApiKey from bhashini.gov.in)."""
    k = key['userID']
    if k not in _BH:
        r = http('https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline',
                 {'pipelineTasks': [{'taskType': 'translation', 'config': {'language': {'sourceLanguage': 'hi', 'targetLanguage': 'en'}}}],
                  'pipelineRequestConfig': {'pipelineId': '64392f96daac500b55c543cd'}},
                 {'userID': key['userID'], 'ulcaApiKey': key['ulcaApiKey']})
        ep = r['pipelineInferenceAPIEndPoint']
        _BH[k] = (ep['callbackUrl'], ep['inferenceApiKey']['name'], ep['inferenceApiKey']['value'],
                  r['pipelineResponseConfig'][0]['config'][0]['serviceId'])
    url, hn, hv, sid = _BH[k]
    r = http(url, {'pipelineTasks': [{'taskType': 'translation', 'config': {
        'language': {'sourceLanguage': 'hi', 'targetLanguage': 'en'}, 'serviceId': sid}}],
        'inputData': {'input': [{'source': hindi}]}}, {hn: hv})
    return r['pipelineResponse'][0]['output'][0]['target'].strip()


def call_custom(cfg, key, hindi):
    """Any JSON translation API: url, headers and body come from config.json with {key} and {text} filled in;
    'response_path' says where the translation is in the answer, e.g. "output.0.target"."""
    fill = lambda v: json.loads(json.dumps(v).replace('{key}', key).replace('{text}', json.dumps(hindi, ensure_ascii=False)[1:-1]))
    r = http(fill(cfg['url']), fill(cfg['body']), fill(cfg.get('headers', {})))
    for p in cfg['response_path'].split('.'):
        r = r[int(p)] if isinstance(r, list) else r[p]
    return str(r).strip()


CALL = {'custom': call_custom, 'openai': call_openai, 'gemini': call_gemini, 'google': call_google, 'bhashini': call_bhashini}


def done_ids(name):
    f = os.path.join(OUTD, name + '.tsv')
    if not os.path.exists(f):
        return set()
    return {tuple(l.split('\t')[:2]) for l in open(f, encoding='utf-8') if l.count('\t') >= 2}


def worker(name, cfg, rows, state, report):
    if 'PASTE_' in json.dumps(cfg):
        report[name] = 'skipped: config.json still has a PASTE_ placeholder for this system'; return
    keys = KEYS.get(cfg['provider'], [])
    keys = [k for k in keys if not (isinstance(k, str) and k.startswith('PASTE_'))]
    if not keys:
        report[name] = 'skipped: no key in keys.json for provider "%s"' % cfg['provider']; return
    parked = set(state['parked'].get(name, []))
    ki = 0
    done = done_ids(name)
    todo = [r for r in rows if (r[0], r[1]) not in done]
    out = open(os.path.join(OUTD, name + '.tsv'), 'a', encoding='utf-8')
    n_new, last = 0, 0.0
    for dom, sid, hindi in todo:
        while True:
            live = [i for i in range(len(keys)) if str(i) not in parked]
            if not live:
                report[name] = 'stopped: all %d keys reached the daily limit (%d new today, %d left) - rerun tomorrow' % (
                    len(keys), n_new, len(todo) - n_new)
                out.close(); return
            ki = ki if ki in live else live[0]
            wait = cfg.get('min_interval_sec', 0) - (time.time() - last)
            if wait > 0:
                time.sleep(wait)
            try:
                last = time.time()
                txt = CALL[cfg['type']](cfg, keys[ki], hindi)
                break
            except DailyLimit as e:
                parked.add(str(ki)); state['parked'][name] = sorted(parked); save_state(state)
                print('[%s] key %d reached its daily limit -> next key' % (name, ki + 1), flush=True)
            except Fatal as e:
                print('[%s] key %d rejected: %s' % (name, ki + 1, str(e)[:200]), flush=True)
                parked.add(str(ki)); state['parked'][name] = sorted(parked); save_state(state)
            except Exception as e:                       # per-minute limits, timeouts, network: wait and retry
                print('[%s] %s -> retry in 20 s' % (name, str(e)[:150]), flush=True)
                time.sleep(20)
                ki = (ki + 1) % len(keys)
        txt = re.sub(r'[\t\r\n]+', ' ', txt)
        with LOCK:
            out.write('%s\t%s\t%s\n' % (dom, sid, txt)); out.flush()
        n_new += 1
        if n_new % 25 == 0:
            print('[%s] %d/%d done this run' % (name, n_new, len(todo)), flush=True)
    out.close()
    report[name] = 'complete (%d new this run)' % n_new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--status', action='store_true')
    a = ap.parse_args()
    rows = [l.rstrip('\n').split('\t') for l in open(INPUT, encoding='utf-8') if l.count('\t') == 2]
    if a.limit:
        per = {}
        rows = [r for r in rows if per.setdefault(r[0], []).append(r) or len(per[r[0]]) <= a.limit]
    systems = {n: c for n, c in CFG['systems'].items() if c.get('enabled') and (not a.only or n in a.only)}
    if a.status:
        for n in CFG['systems']:
            d = done_ids(n)
            print('%-24s %5d / %d' % (n, len([r for r in rows if (r[0], r[1]) in d]), len(rows)))
        return
    state = load_state(); report = {}
    th = [threading.Thread(target=worker, args=(n, c, rows, state, report)) for n, c in systems.items()]
    for t in th:
        t.start()
    for t in th:
        t.join()
    print('\n==== summary ====')
    for n in systems:
        print('%-24s %s' % (n, report.get(n, '?')))
    print('\nNext: python3 collect_exp3.py  (builds exp3_outputs.xlsx)')


if __name__ == '__main__':
    main()
