"""Morphology layer: inflect(lemma, pos, feats) -> surface form.

Backed by the Apertium English generator (lt-proc -g eng.autogen.bin), batched and cached.
Words Apertium does not know (returned with '#') fall back to regular English rules.
Another target language plugs in its own generator with the same inflect() interface.
"""
import os
import re
import subprocess

_BUNDLED = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'apertium_eng', 'eng.autogen.bin')
APERTIUM_BIN = os.environ.get(
    'USR2CHUNK_EN_AUTOGEN',
    _BUNDLED if os.path.exists(_BUNDLED) else '/root/projects/multilingual_rule_based_updated/apertium_eng/eng.autogen.bin')

# feature bundle -> Apertium tag string
_VERB_TAGS = {
    'inf': '<vblex><inf>', 'past': '<vblex><past>', 'pp': '<vblex><pp>', 'ger': '<vblex><ger>',
    'pres3sg': '<vblex><pres><p3><sg>', 'pres': '<vblex><pres>',
}
_BE = {'pres3sg': 'is', 'pres': 'are', 'pres1sg': 'am', 'past3sg': 'was', 'past': 'were', 'pp': 'been',
       'ger': 'being', 'inf': 'be'}
_HAVE = {'pres3sg': 'has', 'pres': 'have', 'past': 'had', 'pp': 'had', 'ger': 'having', 'inf': 'have'}
_DO = {'pres3sg': 'does', 'pres': 'do', 'past': 'did', 'pp': 'done', 'ger': 'doing', 'inf': 'do'}

_cache = {}
_acache = {}
_rawcache = {}
APERTIUM_ANA = APERTIUM_BIN.replace('autogen', 'automorf')


class _LtProc:
    """One persistent lt-proc process in null-flush mode (-z): send 'input' + NUL, read until NUL.
    Starting lt-proc once instead of once per word makes generation many times faster."""
    def __init__(self, args):
        self.args, self.p = args, None

    def query(self, text):
        try:
            if self.p is None or self.p.poll() is not None:
                self.p = subprocess.Popen(['lt-proc', '-z'] + self.args, stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self.p.stdin.write(text.encode('utf-8') + b'\0')
            self.p.stdin.flush()
            buf = bytearray()
            while True:
                ch = self.p.stdout.read(1)
                if not ch or ch == b'\0':
                    break
                buf += ch
            return buf.decode('utf-8')
        except (OSError, BrokenPipeError):        # fall back to one process per call
            self.p = None
            return subprocess.run(['lt-proc'] + self.args, input=text, capture_output=True, text=True,
                                  encoding='utf-8').stdout


_ANA = _LtProc([APERTIUM_ANA])
_GEN = _LtProc(['-g', APERTIUM_BIN])


def _analysis(word):
    """Raw Apertium analysis line for a word (cached; one persistent process)."""
    if word not in _rawcache:
        _rawcache[word] = _ANA.query(word + '\n') if os.path.exists(APERTIUM_ANA) else ''
    return _rawcache[word]


def analyse(word):
    """Set of Apertium analyses (tag strings) for a surface word; empty if unknown."""
    if word in _acache:
        return _acache[word]
    tags = set()
    if os.path.exists(APERTIUM_ANA) and re.fullmatch(r"[a-z\-']+", word):
        out = _analysis(word)
        for a in re.findall(r'/([^/$]+)', out):
            if a.startswith('*'):          # Apertium: unknown word
                continue
            tags.add(re.sub(r'^[^<]*', '', a))
    _acache[word] = tags
    return tags


def pp_lemmas(word):
    """Lemmas of which `word` is a past participle ('found' -> {'find'})."""
    if not os.path.exists(APERTIUM_ANA) or not re.fullmatch(r"[a-z\-']+", word or ''):
        return set()
    out = _analysis(word)
    return set(re.findall(r'/([^/<$]+)<vblex><pp>', out))


def is_predicative(word):
    """True for adjectives / past participles that cannot be a base verb (known, rich, situated)."""
    t = analyse(word)
    if not t:
        return False
    base_verb = any(x.startswith('<vblex><inf>') or x.startswith('<vblex><pres>') for x in t)
    return not base_verb and any(x.startswith('<adj>') or x.startswith('<vblex><pp>') for x in t)


def _apertium(items):
    """items: list of '^lemma<tags>$' strings -> list of surfaces ('' when unknown)."""
    todo = [i for i in items if i not in _cache]
    if todo and os.path.exists(APERTIUM_BIN):
        data = '\n'.join(todo) + '\n'
        out = _GEN.query(data).split('\n')
        for i, o in zip(todo, out):
            o = o.strip()
            # spelling variants come as 'worshiped/worshipped': take the last (British) variant
            _cache[i] = '' if (not o or o.startswith(('#', '@', '^'))) else o.split('/')[-1]
    return [_cache.get(i, '') for i in items]


def _regular_verb(lemma, form):
    if form in ('inf', 'pres'):
        return lemma
    if form == 'pres3sg':
        if re.search(r'(s|sh|ch|x|z|o)$', lemma):
            return lemma + 'es'
        if re.search(r'[^aeiou]y$', lemma):
            return lemma[:-1] + 'ies'
        return lemma + 's'
    if form in ('past', 'pp'):
        if lemma.endswith('e'):
            return lemma + 'd'
        if re.search(r'[^aeiou]y$', lemma):
            return lemma[:-1] + 'ied'
        return lemma + 'ed'
    if form == 'ger':
        if lemma.endswith('ie'):
            return lemma[:-2] + 'ying'
        if lemma.endswith('e') and not lemma.endswith(('ee', 'ye', 'oe')):
            return lemma[:-1] + 'ing'
        return lemma + 'ing'
    return lemma


def _regular_plural(n):
    if re.search(r'(s|sh|ch|x|z)$', n):
        return n + 'es'
    if re.search(r'[^aeiou]y$', n):
        return n[:-1] + 'ies'
    return n + 's'


_bcache = {}


def base_verb(word):
    """'came' -> 'come', 'happened' -> 'happen' (dictionary English sometimes stores an inflected form)."""
    if word in _bcache:
        return _bcache[word]
    res = word
    if os.path.exists(APERTIUM_ANA) and re.fullmatch(r"[a-z\-']+", word):
        out = _analysis(word)
        past =re.findall(r'/([^/<$]+)<vblex><past>', out)
        # only forms that are also a simple past are reduced (happened, fell, came); participle-only / adjectival
        # forms (known, situated) stay as they are
        if past and not re.search(r'/[^/<$]+<vblex><inf>', out) and not re.search(r'<adj>', out):
            res = past[0]
    _bcache[word] = res
    return res


def verb(lemma, form):
    """form: inf | pres | pres3sg | past | past3sg | pp | ger.  Multi-word lemmas inflect the first word."""
    if ' ' in lemma:
        head, rest = lemma.split(' ', 1)
        return verb(head, form) + ' ' + rest
    lemma = base_verb(lemma)
    if lemma == 'be':
        return _BE.get(form, _BE.get(form.replace('3sg', ''), 'be'))
    f = form.replace('past3sg', 'past')
    if lemma == 'have':
        return _HAVE.get(f, 'have')
    if lemma == 'do':
        return _DO.get(f, 'do')
    if f in ('inf', 'pres'):
        return lemma
    if f == 'ger' and lemma.endswith('ing') and len(lemma) > 5:
        return lemma
    s = _apertium(['^%s%s$' % (lemma, _VERB_TAGS[f])])[0]
    return s or _regular_verb(lemma, f)


_IRREG_PL = {'medium': 'media', 'criterion': 'criteria', 'phenomenon': 'phenomena', 'datum': 'data'}
_INVARIANT_PL = {'billion', 'million', 'thousand', 'hundred', 'crore', 'lakh', 'dozen', 'fish', 'sheep', 'deer', 'series', 'species', 'aircraft', 'people', 'police', 'cattle', 'both', 'bacteria', 'breath', 'percent', 'information'}


def noun(lemma, number='sg'):
    if number != 'pl' or not lemma:
        return lemma
    if ' ' in lemma or '-' in lemma:          # inflect the last element: "goods-train" -> "goods-trains"
        sep = ' ' if ' ' in lemma else '-'
        head, last = lemma.rsplit(sep, 1)
        return head + sep + noun(last, 'pl')
    if lemma in _INVARIANT_PL:
        return lemma
    if lemma in _IRREG_PL:
        return _IRREG_PL[lemma]
    if lemma.endswith('s') and any(t.startswith('<n><pl>') for t in analyse(lemma)):
        return lemma                      # already plural (ruins, remains)
    s = _apertium(['^%s<n><pl>$' % lemma])[0]
    return s or _regular_plural(lemma)


_IRR_ADJ = {'little': ('less', 'least'), 'good': ('better', 'best'), 'bad': ('worse', 'worst'),
            'much': ('more', 'most'), 'many': ('more', 'most'), 'far': ('farther', 'farthest')}


def adj(lemma, degree='pos'):
    if degree == 'pos':
        return lemma
    if lemma in _IRR_ADJ:
        return _IRR_ADJ[lemma][0 if degree == 'comp' else 1]
    tag = {'comp': '<adj><sint><comp>', 'sup': '<adj><sint><sup>'}[degree]
    s = _apertium(['^%s%s$' % (lemma, tag)])[0]
    if s:
        return s
    return ('more ' if degree == 'comp' else 'most ') + lemma


def inflect(lemma, pos, **feats):
    if pos == 'v':
        return verb(lemma, feats.get('form', 'inf'))
    if pos == 'n':
        return noun(lemma, feats.get('number', 'sg'))
    if pos == 'adj':
        return adj(lemma, feats.get('degree', 'pos'))
    return lemma
