"""usr2chunk: layered USR -> English chunk generator.

Layers (see nlg_reports/chunking_spec.md):
  A  read USR, resolve constructions (ne, conj/disjunct, cp, dist/meas, span, calendar, compounds)
  B  noun phrases   (det, quant, mods, head, of-r6 chain, post-modifiers, markers)
  C  case marking   (relation -> preposition, refined by lexical lists)
  D  verb group     (TAM table + voice + negation + agreement, inflected through morph.py)
  E  clause         (subject, k1s/k2s predicate, non-finite clauses, connectives)
  F  chunk order    (frame adverbials, SUBJ, rest in Hindi order, predicate, verb)
All language-specific facts live in tables/<lang>/ and the concept dictionary.
"""
import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import morph  # noqa: E402

_BUNDLED_DICT = os.path.join(HERE, 'data', 'concept-to-mrs-rels.dat')
DICT_PATH = os.environ.get('USR2CHUNK_DICT', _BUNDLED_DICT if os.path.exists(_BUNDLED_DICT) else
                           '/root/projects/multilingual_rule_based_updated/dictionaries/concept-to-mrs-rels.dat')
TABLES = os.path.join(HERE, 'tables', 'en')


# ----------------------------------------------------------------------------- tables
def _tsv(name):
    out = []
    for line in open(os.path.join(TABLES, name), encoding='utf-8'):
        if line.strip() and not line.startswith('#'):
            out.append(line.rstrip('\n').split('\t'))
    return out


MARKERS = {r[0]: (r[1], r[2] if len(r) > 2 else 'pre') for r in _tsv('markers.tsv')}
DISCOURSE = {r[0]: r[1] for r in _tsv('discourse.tsv')}
ABBREV = {r[0]: r[1] for r in _tsv('abbreviations.tsv')}   # word acronyms: 'edsa' = 'AIDS'
TAM = {r[0]: {'tense': r[1], 'aspect': r[2], 'modal': r[3]} for r in _tsv('tam.tsv')}
RELPREP = {r[0]: r[1] for r in _tsv('relations.tsv')}
LISTS = {r[0]: set(r[1].split()) for r in _tsv('prep_lists.tsv')}
LIGHT = {r[0]: r[1] for r in _tsv('verbalizers.tsv')}
GOVERNED = {r[0]: r[1] for r in _tsv('governed.tsv')}
VERB_GOVERNED = {(r[0], r[1]): r[2] for r in _tsv('verb_governed.tsv') if len(r) > 2}

# ----------------------------------------------------------------------------- dictionary
EN, POS, SL = {}, {}, {}
CP_INDEX = defaultdict(list)   # 'nirmANa+kara' -> [(n, key), ...]


def load_dict(path=DICT_PATH):
    for line in open(path, encoding='utf-8'):
        c = line.split()
        if len(c) < 4 or c[0] == 'cl':
            continue
        en = re.sub(r'_\d+(?=$|\+)', '', c[3])     # strip sense numbers on every word of a multi-word entry
        EN[c[1]] = en.replace('+', ' ')
        if len(c) > 4 and '_v_' in c[4] and re.fullmatch(r'[a-z]+-(out|up|off|on|down|in|over|away)', EN[c[1]]):
            EN[c[1]] = EN[c[1]].replace('-', ' ')     # 'pawA+lagA' = 'find out'
        SL[c[1]] = c[2].split(',')
        m = re.match(r'^(.+\+[A-Za-z]+)_(\d+)$', c[1])
        if m:
            CP_INDEX[m.group(1)].append((int(m.group(2)), c[1]))
        mrs = c[4] if len(c) > 4 else ''
        POS[c[1]] = ('v' if ('_v_' in mrs or '/VB' in mrs) else 'n' if ('_n_' in mrs or '/NN' in mrs)
                     else 'a' if ('_a_' in mrs or '/JJ' in mrs) else 'x')


# ----------------------------------------------------------------------------- WX -> roman
_V = {'a': 'a', 'A': 'a', 'i': 'i', 'I': 'i', 'u': 'u', 'U': 'u', 'e': 'e', 'E': 'ai', 'o': 'o', 'O': 'au', 'q': 'r', 'Q': 'r'}
_C = {'k': 'k', 'K': 'kh', 'g': 'g', 'G': 'gh', 'f': 'n', 'c': 'c', 'C': 'ch', 'j': 'j', 'J': 'jh', 'F': 'n',
      't': 't', 'T': 'th', 'd': 'd', 'D': 'dh', 'N': 'n', 'w': 't', 'W': 'th', 'x': 'd', 'X': 'dh', 'n': 'n',
      'p': 'p', 'P': 'ph', 'b': 'b', 'B': 'bh', 'm': 'm', 'y': 'y', 'r': 'r', 'l': 'l', 'v': 'v', 'S': 'sh',
      'R': 'sh', 's': 's', 'h': 'h', 'L': 'l', 'H': 'h', 'Y': '', 'Z': ''}
_LAB = set('pPbBmv')
_NONLAB_STOP = set('kKgGcCjJtTdDwWxXN')


def roman(w):
    """Shared WX -> roman scheme; anusvara = homorganic nasal (n before non-labials, m elsewhere)."""
    if not w or not re.search(r'[A-Za-z]', w):
        return w
    out, i = [], 0
    while i < len(w):
        ch = w[i]
        two = w[i:i + 2]
        if two in ('dZ', 'DZ', 'jZ', 'kZ', 'KZ', 'gZ', 'PZ'):
            out.append({'dZ': 'd', 'DZ': 'dh', 'jZ': 'j', 'kZ': 'k', 'KZ': 'kh', 'gZ': 'g', 'PZ': 'ph'}[two]); i += 2; continue
        if ch == 'z':
            out.append('n'); i += 1; continue
        if ch == 'M':
            nxt = w[i + 1:i + 2]
            out.append('n' if nxt in _NONLAB_STOP else 'm'); i += 1; continue
        if ch in 'qQ' and out and out[-1].endswith('r'):
            i += 1                                   # 'Srq' (श्रृ) = 'shr', not 'shrr'
            continue
        if ch in _V:
            out.append(_V[ch])
        elif ch in _C:
            out.append(_C[ch])
        else:
            out.append(ch.lower())
        i += 1
    return ''.join(out).lower().replace('+', '-')


# ----------------------------------------------------------------------------- layer A
class Node:
    __slots__ = ('idx', 'concept', 'sem', 'gnp', 'head', 'rel', 'disc', 'spk', 'scope', 'cx', 'role',
                 'kids', 'members', 'sent')

    def __init__(self, c, sent):
        self.idx = c[1]
        self.concept, self.sem, self.gnp = c[0], c[2], c[3]
        self.head, self.rel = (c[4].split(':', 1) if ':' in c[4] else (None, None))
        self.disc, self.spk, self.scope = c[5], c[6], c[7]
        self.cx, self.role = (c[8].split(':', 1) if ':' in c[8] else (None, None))
        self.kids, self.members, self.sent = [], [], sent

    @property
    def pos(self):
        return int(float(self.idx)) if re.match(r'^[\d.]+$', self.idx) else 0

    @property
    def root(self):
        return self.concept.split('-', 1)[0] if self._has_tam() else self.concept

    def _has_tam(self):
        if '-' not in self.concept or self.concept.startswith(('[', '@')):
            return False
        if self.concept in EN:
            return False                             # hyphenated dictionary concept: 'BU-ABa_2', 'rakwa-pravAha_1'
        suf = self.concept.split('-', 1)[1]
        return suf in TAM or suf in ('pres', 'past', 'fut') or bool(re.fullmatch(r'[0A-Za-z]+(_[A-Za-z]+)*_\d+', suf))

    @property
    def tam(self):
        return self.concept.split('-', 1)[1] if self._has_tam() and not self.concept.startswith('$') else ''

    @property
    def kind(self):
        if self.concept.startswith('['):
            return re.sub(r'[_-]\d+\]$', '', self.concept.strip('[').rstrip(']')).split('_')[0].split('-')[-1] \
                if not re.match(r'^\[\d+[-_](waw|tat)', self.concept) else 'compound'
        return ''

    def markers(self):
        return [m for m in self.spk.split('/') if m and m != '-']

    def first_pos(self, _seen=None):
        """Hindi position where this phrase starts (min index over the subtree incl. members).
        Guarded against dependency loops in a malformed USR."""
        _seen = set() if _seen is None else _seen
        if id(self) in _seen:
            return self.pos
        _seen.add(id(self))
        ps = [self.pos] if not self.concept.startswith('[') else []
        for m in self.members:
            ps.append(m.first_pos(_seen))
        for k in self.kids:
            ps.append(k.first_pos(_seen))
        return min(ps) if ps else self.pos


class Sentence:
    def __init__(self, sid, rows, stype, hindi):
        self.sid, self.stype, self.hindi = sid, stype, hindi
        self._rows = rows
        self.cycles = []
        self.read_error = ''
        self.nodes = [Node(r, self) for r in rows]
        self.by = {n.idx: n for n in self.nodes}
        for n in self.nodes:
            if n.cx and n.cx in self.by and n.role:
                self.by[n.cx].members.append(n)
        for n in self.nodes:                        # pre-pass: a noun 'mod' of a name is an apposition
            h = self.by.get(n.head) if n.head else None
            if h is not None and h.cx in self.by and h.role in ('begin', 'inside') and n.rel == 'mod'                     and POS.get(n.root) == 'n' and not n.concept.startswith(('[', '$'))                     and any(x.head == n.idx and x.rel in ('r6', 'mod', 'rs') for x in self.nodes):
                n.rel = 'rs'                        # 'bAhubalI ke Cote BAI SreyaMRakumAra': keeps 'of bahubali'
        for n in self.nodes:
            h = self.by.get(n.head) if n.head else None
            # a dependent of a named-entity / compound member belongs to the construction as a whole
            if h is not None and h.cx in self.by and (h.role == 'verbalizer' or (h.role == 'kriyAmUla' and n.rel in VERBAL_DEP and n.rel not in ('k1', 'rn'))) and n.rel != 'r6':
                n.head = h.cx                       # dependent of the light verb belongs to the whole cp
                h = self.by[h.cx]
            if h is not None and h.cx in self.by and h.role in ('begin', 'inside'):
                n.head = h.cx                       # everything on an NE member belongs to the NE
                h = self.by[h.cx]
            elif h is not None and h.cx in self.by and h.role in ('mod', 'head') \
                    and self.by[h.cx].kind in ('compound', 'nc') and n.rel in ('r6', 'rs', 'card', 'quant', 'dem'):
                n.head = h.cx                       # phrase-level dependents of a compound member
                h = self.by[h.cx]
            # a genitive on a noun that is itself a modifier belongs to the phrase head (lok jIvan, padosI rAjya)
            if h is not None and n.rel == 'r6' and h.rel == 'mod' and POS.get(h.root) == 'n' and h.head in self.by \
                    and self.by[h.head].kind != 'ne' \
                    and (min(m.pos for m in n.members) if n.members else n.pos) < h.pos:
                n.head = h.head
                h = self.by[h.head]
                if h.cx in self.by and h.role in ('begin', 'inside', 'mod', 'head'):
                    n.head = h.cx                   # never leave a dependent on a construction member
                    h = self.by[h.cx]
            # a genitive before the FIRST conjunct (Hindi order) is shared by the whole coordination
            if h is not None and n.rel == 'r6' and h.role == 'op1' and h.cx in self.by and n.pos < h.pos \
                    and not any(x.head in [m.idx for m in self.by[h.cx].members if m is not h] and x.rel == 'r6'
                                for x in self.nodes) \
                    and self.by[h.cx].kind in ('conj', 'disjunct') \
                    and len(self.by[h.cx].members) <= 2 \
                    and not any(x.head in [m.idx for m in self.by[h.cx].members] and x is not n
                                and (x.rel == 'r6' or 'kqw' in (x.gnp or '') or x.rel in ('rvks', 'rbks'))
                                for x in self.nodes):
                # English puts a shared genitive after a SHORT list of bare nouns ('importance and acceptance of
                # seven places'); in a long or complex list it stays on the first item ('building plan of temple, ...')
                n.head = h.cx
                h = self.by[h.cx]
            # a genitive on a complex predicate is the genitive of its kriyAmUla noun = the verb's object
            # ('is saPara kA AnaMxa lenA' = 'enjoy this journey'), unless the cp already has an object
            if h is not None and n.rel == 'r6' and h.role == 'kriyAmUla' and h.cx in self.by:
                n.head = h.cx                       # genitive on the kriyAmUla noun = genitive on the cp
                h = self.by[h.cx]
            if h is not None and n.rel == 'r6' and h.kind == 'cp' and \
                    not any(r[4].split(':')[-1] in ('k1', 'k2') and r[4].split(':')[0] == str(h.idx) for r in self._rows):
                vb = next((r for r in self._rows if r[8].split(':')[-1] == 'verbalizer' and r[8].split(':')[0] == str(h.idx)), None)
                # 'X kI sWApanA huI' (ho: intransitive) = 'X was established' -> subject; 'X kA AnaMxa lenA' -> object
                n.rel = 'k1' if vb is not None and vb[0].split('_')[0] == 'ho' else 'k2'
            if h is not None and n.rel in ('card', 'quant') and h.rel == 'mod' and POS.get(h.root) in ('a', 'x') and h.head in self.by:
                n.head = h.head
                h = self.by[h.head]
            if h is not None and self._creates_cycle(n, h):
                self.cycles.append((n.concept, h.concept))   # malformed USR (A -> B -> A): break the loop, keep going
                n.head = None
                h = None
            if h is not None:
                h.kids.append(n)
        for n in self.nodes:
            if n.kind != 'ne':
                n.members.sort(key=lambda m: (_op_no(m.role), m.pos))
            else:
                n.members.sort(key=lambda m: 0 if m.role == 'begin' else 1)
            n.kids.sort(key=lambda k: k.first_pos())
        self.main = next((n for n in self.nodes if n.rel == 'main'), None)

    def _creates_cycle(self, n, h):
        """True if attaching n under h makes h its own descendant (n is an ancestor of h)."""
        seen, cur = set(), h
        while cur is not None and id(cur) not in seen:
            if cur is n:
                return True
            seen.add(id(cur))
            nxt = self.by.get(cur.head) if cur.head else None
            if nxt is None and cur.cx in self.by and cur.role in ('begin', 'inside', 'mod', 'head', 'kriyAmUla', 'verbalizer'):
                nxt = self.by[cur.cx]
            cur = nxt
        return False


def _op_no(role):
    m = re.search(r'(\d+)$', role or '')
    return int(m.group(1)) if m else 0


def read_usrs(path):
    sents, cur, rows, stype, hindi = [], None, [], '', ''
    for line in open(path, encoding='utf-8'):
        s = line.strip().strip('"')
        m = re.search(r'sent_id=\s*([^>\s]+)>', s)
        if m:
            cur, rows, stype, hindi = m.group(1), [], '', ''
            continue
        if cur is None:
            continue
        if s.startswith('#'):
            hindi = s[1:].strip()
        elif s.startswith('%'):
            stype = s[1:]
        elif s.startswith('</sent_id'):
            try:
                sents.append(Sentence(cur, rows, stype, hindi))
            except Exception as e:                   # one malformed USR never stops the whole file
                bad = Sentence(cur, [], stype, hindi)
                bad.read_error = type(e).__name__
                sents.append(bad)
            cur = None
        else:
            c = s.split()
            if len(c) >= 9 and re.match(r'^[\d.]+$', c[1]):
                if '-' in c[0] and not c[0].startswith(('[', '@', '$')):
                    root, suf = c[0].split('-', 1)
                    norm = re.sub(r'_\d+(?=_)', '', re.sub(r'(?<=[A-Za-z])\d+(?=_)', '', suf))
                    if suf not in TAM and norm in TAM:   # stray sense numbers inside a TAM: 'wA_1_hE_1' = 'wA_hE_1'
                        c[0] = root + '-' + norm
                rows.append(c[:9])
    return sents


# ----------------------------------------------------------------------------- lexical
# English letter names as written in WX ('eca' = H); an '@' word made only of letter names is an abbreviation
_LETTERS = {'e': 'A', 'bI': 'B', 'sI': 'C', 'dI': 'D', 'I': 'E', 'ePa': 'F', 'jI': 'G', 'eca': 'H', 'eMca': 'H',
            'AI': 'I', 'je': 'J', 'ke': 'K', 'ela': 'L', 'ema': 'M', 'ena': 'N', 'o': 'O', 'pI': 'P', 'kyU': 'Q',
            'Ara': 'R', 'esa': 'S', 'tI': 'T', 'yU': 'U', 'vI': 'V', 'dablyU': 'W', 'eksa': 'X', 'vAI': 'Y',
            'jZeda': 'Z', 'jeda': 'Z'}


def _spell(t):
    """Split a WX string into English letter names ('tIbI' -> 'TB'); None when it is not one."""
    if not t:
        return ''
    for k in sorted(_LETTERS, key=len, reverse=True):
        if t.startswith(k):
            rest = _spell(t[len(k):])
            if rest is not None:
                return _LETTERS[k] + rest
    return None


def abbreviation(t):
    """Capital Roman form of an abbreviation: dotted letter names, '-'/digit parts kept; word acronyms from the table."""
    key = t.strip('.')
    if key in ABBREV:
        return ABBREV[key]
    out = []
    for part in re.split(r'([.\-])', key):
        if part in ('.', ''):
            continue
        if part == '-' or part.isdigit():
            out.append(part)
            continue
        sp = _spell(part)
        if sp is None:
            return None
        out.append(sp)
    return ''.join(out) or None


def word(n):
    """English lemma for a single (non-construction) node."""
    full = n.concept.lstrip('^')
    if full != n.root.lstrip('^') and EN.get(full, '-') != '-':
        return EN[full]                              # hyphenated concept that is not 'word-TAM': 'hanumAna_1-baMxara_1'
    c = n.root
    if c.startswith('@'):
        ab = abbreviation(c[1:])
        if ab:
            return ab                                # '@o.Ara.esa' = 'ORS', '@tIbI' = 'TB', '@sIdI-4' = 'CD-4'
        t = c[1:].strip('.').lower()
        return roman(t.replace('.', ' ')).replace(' ', '.') + '.' if '.' in c else roman(t)
    c = c.lstrip('^')
    if re.fullmatch(r'[\d.,:]+_\d+', c):
        return c.rsplit('_', 1)[0]
    if c in MARKERS and MARKERS[c][0] not in ('-', '') and c not in EN:
        return MARKERS[c][0]
    if c in EN and EN[c] != '-':
        return EN[c]
    if '-' in c and not c.startswith('['):           # unknown concept with TAM-like parts: 'jI_3-saka_1-e_1'
        first = c.split('-', 1)[0]
        if first in EN and EN[first] != '-':
            return EN[first]
        c = first
    if re.fullmatch(r'[\d.,:]+', c):
        return c
    base = re.sub(r'_\d+$', '', c)
    if re.fullmatch(r'[\d.,:]+', base):
        return base
    return roman(base)


ALREADY_PLURAL = {'people', 'police', 'cattle', 'children', 'men', 'women', 'etc', 'others', 'these', 'those'}
PREP_HEADS = {'before', 'after', 'during', 'near', 'behind', 'above', 'below', 'under', 'inside', 'outside', 'around', 'beside',
              'besides', 'between', 'among', 'without', 'along', 'across', 'beyond', 'within', 'opposite', 'amidst',
              'towards', 'over', 'ahead', 'with', 'nearby', 'during', 'until', 'till', 'through', 'via', 'like', 'about', 'against', 'except', 'instead'}
FOCUS_PARTICLES = {'only', 'also', 'even', 'merely', 'just'}
FUNC_WORDS = set('a an the of in on at to by with from for and or but is are was were be been has have had not this that these those it its as than so very also only'.split())
PL_QUANT = {'most', 'few', 'various', 'numerous', 'several', 'many', 'all', 'both', 'innumerable', 'several', 'many', 'all', 'various', 'numerous', 'innumerable', 'some', 'few', 'both', 'these', 'those'}


def is_plural(n):
    if 'pl' in (n.gnp or ''):
        return True
    if (EN.get(n.root) or '').lower() in _MONTHS:
        return False                                 # '21 jUna' is a date, not 21 Junes
    for k in n.kids:
        if k.rel == 'card' and k.kind == 'span' and len(k.members) < 2:
            continue                         # 'up to 86 percentage': an open range does not make the noun plural
        if k.rel == 'card':
            w = word(k)
            if w not in ('one', '1', 'a', 'an'):
                return True
        if k.rel == 'quant' and word(k) in PL_QUANT and not k.root.startswith('koI_'):
            return True
        if k.rel == 'dem' and 'pl' in (k.gnp or ''):
            return True                      # 've prAcIna stamBa' = 'those ancient pillars'
    for c in n.sent.nodes:                   # conjunct of a coordination under a plural demonstrative
        if n in c.members and c.rel != 'dem' and any(k.rel == 'dem' and 'pl' in (k.gnp or '') for k in c.kids):
            return True
    return False


def honorific(n):
    """USR 'pl' on a person name or with 'respect' is honorific, not a real plural."""
    return 'respect' in ' '.join(n.markers())


def own_pos(n):
    """Position of the node itself (its members for a construction), ignoring its dependents."""
    return min(m.pos for m in n.members) if n.members else n.pos


def is_name(n):
    return n.kind == 'ne' or (not re.search(r'_\d+$', n.root) and not n.root.startswith(('$', '@', '[')) and
                              not re.fullmatch(r'[\d.,:]+', n.root))


# ----------------------------------------------------------------------------- layer B : noun phrases
NP_INTERNAL = {'dem', 'quant', 'card', 'ord', 'intf', 'mod', 'r6', 'rs', 're', 'rvks', 'rbks', 'rbk', 'count', 'unit',
               'rad', 'neg', 'jk1', 'rdl', 'rsm'}
VERBAL_DEP = {'rn', 'k1', 'k2', 'k3', 'k4', 'k4a', 'k5', 'k7', 'k7p', 'k7t', 'rt', 'rh', 'krvn', 'k2p', 'k7a', 'rkl', 'rsk',
              'rpk', 'rblak', 'rblpk', 'rblsk', 'k2s', 'k1s', 'rask1', 'rask3', 'mk1', 'ru', 'rhh', 'rv', 'vkvn', 'k5prk'}


ALL_SENTS = {}


def antecedent(n):
    # $apanA -> subject of its clause; $wyax/$yax -> the node named in the discourse column (sid.idx:coref)
    key = re.sub(r'_\d+$', '', n.root)
    if key == '$apanA':
        v = n.sent.main
        if v is not None:
            for k in v.kids + [x for m in v.members for x in m.kids]:
                if k.rel in ('k1', 'pk1') and k is not n:
                    return k
        return None
    m = re.match(r'^([^.:]+)\.([\d.]+):coref', n.disc or '')
    if m:
        s2 = ALL_SENTS.get(m.group(1))
        if s2 is not None:
            return s2.by.get(m.group(2))
    m = re.match(r'^(\d+):coref', n.disc or '')
    if m:
        return n.sent.by.get(m.group(1))          # same-sentence coreference
    return None


def person_poss(a):
    if a is None:
        return None
    if a.root.startswith('$'):
        key = re.sub(r'_\d+$', '', a.root)
        pl = 'pl' in (a.gnp or '')
        if key == '$speaker':
            return 'our' if pl else 'my'             # 'hama apane jIvana meM' = 'in our life'
        if key == '$addressee':
            return 'your'
        if key == '$wyax' and pl:
            return 'their'
        return None
    pl = is_plural(a) or 'pl' in (a.gnp or '') or (a.kind == 'conj' and len(a.members) > 1)
    if pl:
        return 'their'
    sem = (a.sem or '') + ' ' + ' '.join(m.sem or '' for m in a.members)
    if 'female' in sem:
        return 'her'
    hw = (word(a) or '').lower().split()
    if 'male' in sem or 'per' in sem.split() or (hw and hw[-1] in LISTS.get('male_person_nouns', set())):
        return 'his'
    return 'its'


def is_place(a):
    if a is None:
        return False
    return 'place' in (a.sem or '') or (a.kind in ('conj', 'disjunct') and bool(a.members)
                                         and all('place' in (m.sem or '') for m in a.members))


def pronoun(n, case):
    key = re.sub(r'_\d+$', '', n.root)
    pl = 'pl' in (n.gnp or '')
    if key == '$wyax' and not pl:
        a0 = antecedent(n)                   # plural antecedent: 'inake anusAra' (= the scholars) = 'according to them'
        pl = a0 is not None and a0.kind == 'conj' and len(a0.members) > 1 and not is_place(a0)
    mk = n.markers()
    if key == '$wyax' and n.rel in ('r6', 'k5', 'k7p', 'k7', 'k2p') and 'pl' not in (n.gnp or '') and is_place(antecedent(n))             and ('proximal' in mk or 'distal' in mk):
        return 'here' if 'proximal' in mk else 'there'   # place deixis from the USR marker (user rule)
    if key in ('$speaker',):
        return {'subj': 'we' if pl else 'i', 'obj': 'us' if pl else 'me', 'poss': 'our' if pl else 'my'}[case]
    if key == '$addressee':
        return {'subj': 'you', 'obj': 'you', 'poss': 'your'}[case]
    if key == '$kim':
        by_rel = {'k7t': 'when', 'k7p': 'where', 'k7': 'where', 'krvn': 'how', 'rh': 'why', 'k1': 'what', 'k2': 'what',
                  'mod': 'which', 'quant': 'how', 'intf': 'how'}
        h0 = n.sent.by.get(n.head) if n.head else None
        if n.rel == 'mod' and h0 is not None and any(k.rel == 'dem' for k in h0.kids):
            return 'what'                            # 'kyA EsA karma' = 'what such work'
        if n.rel in by_rel:
            return by_rel[n.rel]
        return {'subj': 'what', 'obj': 'what', 'poss': 'whose'}[case]
    if key == '$apanA':
        p = person_poss(antecedent(n))
        return p or ('their' if pl else ('his' if (n.sem in ('male', 'per') or 'anim' in n.sem) else 'its'))
    if key == '$yax':
        anim = 'anim' in (n.sem or '') or n.sem in ('per', 'male', 'female')
        a0 = antecedent(n)                           # 'jo' coreferring with a person: 'who'
        if a0 is not None and not anim:
            sem0 = ' '.join([a0.sem or ''] + [m.sem or '' for m in a0.members])
            anim = any(t in sem0.split() for t in ('per', 'male', 'female')) or \
                (not a0.concept.startswith(('[', '$')) and (head_word(a0) or '').split()[-1:] in
                 [['people'], ['person'], ['persons'], ['patient'], ['patients'], ['women'], ['woman'], ['learners']])
        rel_map = {'k7p': 'in which', 'k7': 'in which', 'k7t': 'when', 'rh': 'by which', 'k3': 'by which', 'k5': 'from which',
                   'k4': 'to whom' if anim else 'to which', 'krvn': 'how', 'r6': 'whose', 'dem': 'which',
                   'k1': 'who' if anim else 'which', 'k2': 'whom' if anim else 'which'}
        return rel_map.get(n.rel, 'which')
    if n.rel in ('k7p', 'k7', 'k2p') and key == '$wyax' and not ('pl' in (n.gnp or '') and 'proximal' in mk):   # goal of motion: 'yahAz Awe hEM' = 'come here'
        return 'here' if 'proximal' in mk else 'there'
    if case == 'poss':
        p = person_poss(antecedent(n))
        return p or ('their' if pl else 'its')
    if key == '$wyax' and n.rel == 'k5' and 'proximal' in mk and not n.disc.strip('-') and not pl \
            and not any(k.rel == 'dem' for k in n.kids):
        return 'here'                                # deictic 'yahIM se' (no antecedent) = 'from here'
    if key == '$wyax' and n.rel == 'vkvn':
        return 'as such'                             # sentence-level 'vEse wo' = 'as such'
    if key == '$wyax' and not pl:
        p0 = person_poss(antecedent(n))
        if p0 in ('his', 'her') and antecedent(n) is not None and not antecedent(n).root.startswith('$'):
            return {'subj': 'he' if p0 == 'his' else 'she', 'obj': 'him' if p0 == 'his' else 'her', 'poss': p0}[case]
    if case == 'obj' and n.rel in ('k2', 'k4', 'k4a') and not n.sent.stype.startswith('pass')             and getattr(n.sent, 'voice_override', '') != 'passive' \
            and not tam_is_passive(tam_of(n.sent.main) if n.sent.main is not None else ''):
        return 'them' if pl else 'it'                # object pronoun: 'it' / 'them' (user decision)                                # plural object pronoun (gold: 'them', not 'these')
    if 'proximal' in mk or key == '$yax':
        return 'these' if pl else 'this'
    if case == 'subj' and key == '$wyax' and not pl:
        p = person_poss(antecedent(n))
        if p in ('his', 'her'):
            return 'he' if p == 'his' else 'she'
    return {'subj': 'they' if pl else 'it', 'obj': 'them' if pl else 'it'}[case]


def construction_text(n, ctx):
    k = n.kind
    ms = n.members
    if not ms:
        return ''                                    # construction whose members are missing in the USR
    if k not in ('ne', 'span', 'calendar', 'temporal', 'spatial', 'dist', 'meas', 'rate') and len(ms) > 1:
        key = '+'.join(m.root.lstrip('^') for m in sorted(ms, key=lambda m: m.idx))
        an = morph.analyse(EN.get(key, '-').split()[-1]) if EN.get(key, '-') != '-' else []
        if EN.get(key, '-') != '-' and not (an and all(a.startswith('<adj>') for a in an)):   # whole pair/compound
            t = EN[key]                              # ('kenxraSAsiwa_1+praxeSa_1' = 'union territory')
            if any(is_plural(m) for m in ms) or 'pl' in (n.gnp or ''):
                t = morph.noun(t, 'pl')
            return t
    if k == 'ne':
        parts = [(word(m) if (m.root.startswith('@') or re.fullmatch(r'[\d.,:]+(_\d+)?', m.root))
                  else roman(re.sub(r'_\d+$', '', m.root))) for m in ms]
        t = ' '.join(p for p in parts if p)
        if 'respect' in ' '.join(n.markers()) and n.sem in ('per', 'male', 'female'):
            t += ' ji'
        elif is_plural(n) and not honorific(n) and t:
            t = morph.noun(t, 'pl')                  # 'cAra XAma' = 'four dhamas' (user rule: NE plurals)
        return t
    if k in ('conj', 'disjunct'):
        incl = [m for m in ms if m.role.startswith('op') and 'samAveSI' in ((m.disc or '') + '/' + (m.spk or ''))]
        if k == 'conj' and len(incl) == 1 and len(ms) == 2 and incl[0].role == 'op1' and any('BI_1' in m.markers() for m in ms if m is not incl[0]):   # 'X ke sAWa Y BI' = 'along with X also Y'
            rest = [m for m in ms if m is not incl[0]]
            return 'along with ' + np(incl[0], ctx, top=False) + ' ' + np(rest[0], ctx, top=False)
        if k == 'conj' and len(incl) == 1 and len(ms) >= 2 and not any('BI_1' in m.markers() for m in ms):
            rest = [np(m, ctx, top=False) for m in ms if m is not incl[0] and m.role.startswith('op')]
            rest = [o for o in rest if o]
            body = rest[0] if len(rest) == 1 else ', '.join(rest[:-1]) + ' and ' + rest[-1]
            return body + ' besides ' + np(incl[0], ctx, top=False)   # 'X ke alAvA Y, Z' = 'Y and Z besides X'
        ops = [np(m, ctx, top=False) for m in ms if m.role.startswith('op')]
        ops = [o for o in ops if o]
        if n.rel == 'ord':
            ops = [o + ('th' if o[-2:] in ('11', '12', '13') else {'1': 'st', '2': 'nd', '3': 'rd'}.get(o[-1], 'th'))
                   if re.fullmatch(r'\d+', o) else o for o in ops]
        cj = 'or' if k == 'disjunct' else 'and'
        if len(ops) <= 1:
            return ''.join(ops)
        if ops[-1] in ('etc', 'and others'):
            return ', '.join(ops[:-1]) + ' ' + ops[-1]
        return ', '.join(ops[:-1]) + ' %s ' % cj + ops[-1]
    if k in ('dist', 'meas', 'rate'):
        num = next((m for m in ms if m.role in ('count', 'card', 'quant')), None)
        unit = next((m for m in ms if m.role == 'unit'), None)
        nt = (np(num, ctx, top=False) if num.concept.startswith('[') else word(num)) if num else ''
        ut = word(unit) if unit else ''
        if ut and nt and nt not in ('1', 'one'):
            ut = morph.noun(ut, 'pl')
        if unit is not None:                         # 'varga kilomItara' = 'square kilometres'
            um = [word(x) for x in list(unit.kids) + list(n.kids) if x.rel == 'mod' and word(x)]
            ut = ' '.join(um + [ut]).strip()
        return ' '.join(x for x in (nt, ut) if x)
    if k == 'span':
        a = next((m for m in ms if m.role == 'start'), None)
        b = next((m for m in ms if m.role == 'end'), None)
        if not (a and b):                            # open span: 'till 1937' / 'from 1937'
            one = a or b
            if one is None:
                return ''
            if not a and one.sem == 'numex':
                return 'up to ' + np(one, ctx, top=False)     # '86 tak' = 'up to 86' (a quantity, not a time)
            return ('from ' if a else 'till ') + np(one, ctx, top=False)
        at, bt = np(a, ctx, top=False), np(b, ctx, top=False)
        aw, bw = at.split(), bt.split()
        if len(aw) >= 2 and len(aw) == len(bw) and aw[1:] == bw[1:]:
            at = aw[0]                               # 'from 9th to 10th century AD', 'from 1018 to 1054 AD'
        if n.rel == 'card':
            return '%s to %s' % (at, bt)             # range as a number: 'xo se wIna minata' = 'two to three minutes'
        lead = re.match(r'^((?:also|only|even)\s+)+', at)    # 'also from X to Y', not 'from also X'
        return ((lead.group(0) if lead else '') + 'from %s to %s' % (at[lead.end():] if lead else at, bt))
    if k == 'spatial':
        whole = next((m for m in ms if m.role == 'whole'), None)
        part = next((m for m in ms if m.role == 'part'), None)
        if whole is not None and part is not None:   # 'mevAdZa meM ciwwOdZagaDZa meM' = 'cittaudagadha in mevada'
            return np(part, ctx, top=False) + ' in ' + np(whole, ctx, top=False)
    if k == 'temporal':
        clock = next((m for m in ms if m.sem == 'clocktime'), None)
        whole = next((m for m in ms if m.role == 'whole'), None)
        if clock is not None:                        # 'subaha 7 baje' = 'at 7 o'clock in morning'
            return "at %s o'clock" % word(clock) + (' in ' + np(whole, ctx, top=False) if whole is not None else '')
    if k in ('calendar', 'temporal', 'spatial'):
        out = []
        for m in ms:
            if m.sem == 'dom' and re.fullmatch(r'\d+', m.root):
                d = m.root
                out.append(d + ('th' if d[-2:] in ('11', '12', '13') else {'1': 'st', '2': 'nd', '3': 'rd'}.get(d[-1], 'th')))
            elif not re.search(r'_\d+$', m.root) and (m.root + '_1') in EN and EN[m.root + '_1'] != '-':
                out.append(EN[m.root + '_1'].lower())
            else:
                out.append(np(m, ctx, top=False))
        return ' '.join(out)
    # compounds: nc, N-waw/tat, compound, xvanxva -> modifier(s) then head, English words
    if k == 'xvanxva':
        ops = [np(m, ctx, top=False) for m in ms]
        return ' and '.join(o for o in ops if o)
    mods = [m for m in ms if m.role != 'head']
    head = next((m for m in ms if m.role == 'head'), None)
    mt = [t for t in (np(m, ctx, top=False) for m in mods) if t]
    ht = head_word(head, head if 'pl' in (head.gnp or '') else n) if head else ''
    if head is not None and ht and 'pl' in (head.gnp or '') and ht == word(head):
        ht = morph.noun(ht, 'pl')                    # a compound head is a noun: 'bastara vAsiyoM' = 'residents of bastara'
    if head is not None and mt and ht in LISTS.get('postnominal_heads', set()):
        return ht + ' ' + ' '.join(mt)               # 'xo garBagqha yukwa' = 'having two sanctum-sanctorum'
    if head is not None and mt and re.match(r'^\[6[-_](waw|tat)', n.concept):
        return ht + ' of ' + ' '.join(mt)            # genitive compound (6-waw): 'construction of temple' (user rule)
    return ' '.join(mt + ([ht] if ht else []))      # other compounds: 'temple building'


def is_adjective_word(w):
    an = morph.analyse(w)
    return not an or any(a.startswith('<adj>') for a in an)


def head_word(n, plural_from=None):
    w = word(n)
    p = plural_from if plural_from is not None else n
    if (not is_name(n) or not honorific(n)) and POS.get(n.root, 'n') in ('n', 'x') and is_plural(p) and not n.root.startswith('$') \
            and n.rel not in ('card', 'ord', 'quant', 'intf', 'count') and w not in ALREADY_PLURAL \
            and not set(w.split()) & FUNC_WORDS and w not in PREP_HEADS:          # 'religious places', but never 'point of views'
        w = morph.noun(w, 'pl')
    if 'superl' in (n.gnp or '') and POS.get(n.root) in ('a', 'x', None) and not w.endswith('est') and not w.startswith('most '):
        w = morph.adj(w, 'sup')
    elif re.search(r'comp[ae]?rmore', n.gnp or '') and ' ' not in w and is_adjective_word(w):
        w = morph.adj(w, 'comp')                     # 'aXika mahawvapUrNa' = 'more important'
    return w


def participle(n):
    """Non-finite verb used as modifier / clause: rbks -> past participle, others -> V-ing."""
    lem = verb_lemma(n)
    if n.rel in ('rbks', 'rbk'):
        return morph.verb(lem, 'pp')
    return morph.verb(lem, 'ger')


def is_verbal(n):
    return n.kind == 'cp' or POS.get(n.root) == 'v' or bool(n.tam) or n.rel in ('rbks', 'rvks', 'rpk', 'rsk', 'rbk')


_IRREG_DEG = {'good': ('better', 'best'), 'bad': ('worse', 'worst'), 'much': ('more', 'most'), 'many': ('more', 'most'),
              'more': ('more', 'most'), 'little': ('less', 'least'), 'far': ('farther', 'farthest'), 'well': ('better', 'best')}


def degree(a, which):
    """'near' -> 'nearer' / 'nearest'; long adjectives take 'more' / 'most'."""
    if not a or ' ' in a:
        return a
    if a.endswith('s') and a[:-1] in ('more', 'long', 'short', 'small', 'big', 'high', 'low', 'near', 'far', 'hot', 'cold'):
        a = a[:-1]                                   # adjective that picked up a plural 's'
    if a in ('more', 'most'):
        return 'more' if which == 'compr' else 'most'
    if a in _IRREG_DEG:
        return _IRREG_DEG[a][0 if which == 'compr' else 1]
    suf = 'er' if which == 'compr' else 'est'
    if len(a) <= 6 and not re.search(r'(ful|ous|ive|ant|ent|al|ic|ed|ing)$', a):
        if a.endswith('y') and len(a) > 2 and a[-2] not in 'aeiou':
            return a[:-1] + 'i' + suf
        if a.endswith('e'):
            return a + suf[1:]
        if re.search(r'[^aeiou][aeiou][bdgmnpt]$', a) and len(a) <= 4:
            return a + a[-1] + suf
        return a + suf
    return ('more ' if which == 'compr' else 'most ') + a


def np(n, ctx, top=True):
    """Layer B: render the phrase rooted at node n (without its clause-level preposition)."""
    if n is None:
        return ''
    if n.root.startswith('$'):
        case = 'poss' if n.rel == 'r6' else ('subj' if n.rel in ('k1', 'k1s', 'dem') else 'obj')
        core = pronoun(n, case)
        pre, post = [], []
    elif n.concept.startswith('[') and n.kind not in ('cp',):
        core = construction_text(n, ctx)
        pre, post = [], []
    elif n.kind == 'cp' or (is_verbal(n) and n.rel in ('rbks', 'rvks', 'rpk', 'rsk', 'rbk', 'rblsk')):
        return nonfinite(n, ctx)
    elif n.rel == 'mod' and 'kqw' in (n.gnp or '') and POS.get(n.root) == 'v' and not n.concept.startswith(('[', '$')) \
            and any(k.rel == 'k2p' and not k.kids and not k.concept.startswith(('[', '$'))
                    and word(k) in ('up', 'down', 'back', 'forward', 'backward', 'ahead', 'away', 'upward', 'downward') for k in n.kids):
        return nonfinite(n, ctx)                     # participle modifier with a direction: 'going up from ground'
    elif 'kqw' in (n.gnp or '') and (n.rel in ('r6', 'k1', 'k2', 'k3', 'k5', 'k7', 'k7t', 'k4', 'k2p', 'rask1', 'rasneg')
                                     or (n.rel == 'rh' and n.root.startswith('ho_5') and any(k.rel == 'k1' for k in n.kids)) or not n.rel
                                     or (n.cx and n.cx in n.sent.by and n.sent.by[n.cx].kind in ('conj', 'disjunct')))             and not n.concept.startswith(('[', '$')):   # also a verbal noun inside a list: 'learning arts and practising them'
        return nonfinite(n, ctx)
    else:
        core = head_word(n)
        if n.rel == 'k2p' and core in ('side', 'direction') and any(k.rel == 'r6' for k in n.kids):
            return np(next(k for k in n.kids if k.rel == 'r6'), ctx, top=False)   # 'sUrya kI waraPa' = 'towards sun'
        if core == 'among':
            r6k = next((k for k in n.kids if k.rel == 'r6'), None)
            if r6k is not None and (r6k.kind in ('conj', 'disjunct') or r6k.root.startswith('$') or
                                    any(x.rel == 'r6' and x.kind in ('conj', 'disjunct') for x in r6k.kids)):
                core = 'between'                     # 'maMgala evaM bqhaspawi ke bIca' = 'between Mars and Jupiter'
        for deg in ('supl', 'compr'):
            if deg in (n.gnp or '').split() + (n.gnp or '').split('|') and ' ' not in core:
                core = degree(core, deg)             # 'sabase badZA' = 'biggest', 'sabase mahawvapUrNa' = 'most important'
        if n.rel == 'k3' and core == 'medium' and any(k.rel == 'r6' for k in n.kids) and not n.concept.startswith('['):
            r6k = next(k for k in n.kids if k.rel == 'r6')
            return np(r6k, ctx, top=False)          # 'X ke mAXyama se' = 'through X' (preposition from prep_for)
        if n.rel in ('krvn', 'vkvn') and core in ('way', 'kind', 'type', 'manner') and \
                any(k.rel == 'mod' and k.root.startswith('$kim') for k in n.kids):
            return 'how'                             # 'kisa prakAra' = 'how'
        if n.rel in ('krvn', 'vkvn') and core in ('kind', 'type', 'manner') and any(k.rel == 'dem' for k in n.kids):
            core = 'way'                             # manner adverbial 'isa prakAra' = 'in this way'
        if n.rel == 'krvn' and ' ' not in core and POS.get(n.root) == 'a' and not is_adverbial(core) \
                and all(k.rel == 'intf' for k in n.kids) \
                and not core.endswith('ly') and core not in ('more', 'less', 'much', 'very', 'fast', 'hard', 'well', 'far'):
            core = (core[:-1] + 'ily') if core.endswith('y') else (core[:-2] + 'ly') if core.endswith('le') \
                else (core + 'y') if core.endswith('ll') else core + 'ly'   # 'TIka se sAPa karanA' = 'clean properly'
        if core in ('a', 'an') and n.rel in ('k1', 'k2', 'k1s', 'k2s', 'rs'):
            core = 'one'                             # quantifier as a head: 'melon meM se eka' = 'one among fairs'
        if POS.get(n.root) == 'v' and n.rel in ('k1', 'k2', 'r6', 'k7', 'k7p', 'k3', 'k5', 'rt', 'rh', 'k2s', 'k1s') \
                and ' ' not in core and not n.tam and not morph.is_predicative(core)                 and (not any(t.startswith(('<n>', '<vblex><pp>')) for t in morph.analyse(core))
                     or (n.rel in ('rt', 'rh') and any(t.startswith('<vblex>') for t in morph.analyse(core)))):   # 'for staying'
            core = morph.verb(core, 'ger')            # 'building of battisa mandira' (not for noun-verbs: 'visit')
        elif n.rel in ('rt', 'rh') and ' ' not in core and not n.tam                 and any(k.rel in VERBAL_DEP and k.rel not in ('r6',) for k in n.kids)                 and any(t.startswith('<vblex>') for t in morph.analyse(core)):
            core = morph.verb(core, 'ger')            # 'saxiyoM se aMXere meM rahane ke kAraNa' = 'because of staying ...'
        pre, post = [], []
    dets, quants, mods, posts = [], [], [], []
    for k in n.kids:
        r = k.rel
        if r == 'dem':
            dets.append(demonstrative(k, n))
            if 'hI_1' in k.markers():
                posts.append(('', 'only', 10 ** 7))   # 'usI kRewra se' = 'from that place only'
        elif r in ('quant', 'card', 'ord', 'intf'):
            t = np(k, ctx, top=False)
            if r == 'card' and t in ('one', 'one only') and 'hI_1' in k.markers():
                t = 'same'                           # 'eka hI gusalaKAne' = 'same bathroom'
                quants.append(t)
                continue
            if k.root.startswith('koI_') and ('BI_1' in k.markers() or 'negative' in n.sent.stype):
                t = 'any'                            # 'koI BI jAnakArI' = 'any information', 'koI ilAja nahIM' = 'no ... any'
            if 'hI_1' in k.markers() and t.endswith(' only'):
                t = t[:-5]
                posts.append(('', 'only', 10 ** 7))   # 'eka hI bAra meM' = 'at a time only'
            if r == 'intf' and t == 'little':
                t = 'a little'                       # 'jarA sA hatake' = 'a little differently'
            elif r == 'intf' and t in ('how', 'so much', 'that much'):
                t = 'how' if t == 'how' else 'so'    # 'kiwanA acCA' = 'how good', 'iwanA badZA' = 'so big'
            elif r == 'intf' and POS.get(k.root) in ('a', 'x') and not t.endswith('ly') and t not in ('more', 'much', 'good') and \
                    t not in ('very', 'most', 'more', 'quite', 'less', 'much', 'so', 'too', 'a little'):
                t = (t[:-1] + 'ily') if t.endswith('y') else (t[:-2] + 'ly') if t.endswith('le') else t + 'ly'
            if r == 'ord' and t == 'first' and any(x.rel == 'mod' and word(x) == 'all' for x in k.kids):
                t = 'first of all'                   # 'saba se pahalA' = 'first of all'
            if r == 'ord' and re.fullmatch(r'\d+', t):
                t = t + ('th' if t[-2:] in ('11', '12', '13') else {'1': 'st', '2': 'nd', '3': 'rd'}.get(t[-1], 'th'))
            quants.append(t)
        elif r == 'r6' and (core == 'away' or k.kind == 'span'):
            if k.kind == 'span':
                posts.append(('', np(k, ctx, top=False), k.first_pos()))
                continue
            mods.append(np(k, ctx, top=False))
        elif r == 'rs' and k.sem == 'numex' and not k.kids:
            posts.append(('', np(k, ctx, top=False), 0))   # 'ciwra 3.3' = 'figure 3.3'
            continue
        elif r == 'rsm':
            posts.append(('like', np(k, ctx, top=False), 10 ** 5))   # 'hqxaya roga jEsI bImAriyAz' = 'diseases like heart diseases'
            continue
        elif r == 'mod' and not k.concept.startswith(('[', '$')) and word(k) == 'etc':
            posts.append(('', 'etc', 10 ** 7))       # 'meve Axi' = 'dry fruits etc'
            continue
        elif r == 'r6' and not k.concept.startswith(('[', '$')) and word(k) in ('everybody', 'everyone', 'someone', 'anyone'):
            mods.insert(0, word(k) + "'s")           # 'hara kisI kA apanA warIkA' = "everybody's own way"
            continue
        elif r == 'r6' and not k.concept.startswith(('[', '$')) and word(k) in ('after', 'before', 'among', 'between') and \
                any(x.rel == 'r6' for x in k.kids):
            posts.append(('', np(k, ctx, top=False), k.first_pos()))   # 'oYpareSana ke paScAwa kA xarxa' = 'pain after operation'
            continue
        elif r == 'r6' and k.root.startswith('apanA_') and word(k) == 'own':
            mods.insert(0, 'own')                    # 'apane ximAga' = 'own mind' (not 'mind of own')
            continue
        elif r == 'r6' or (r == 'rdl' and core not in PREP_HEADS and core in ('middle', 'centre', 'center', 'side', 'top')):
            if k.root.startswith('$') and pronoun(k, 'poss') in ('here', 'there'):
                posts.append(('of', pronoun(k, 'poss'), k.first_pos()))   # 'yahAz kA paryatana' = 'tourism of here'
            elif k.root.startswith('$'):
                dets.append(pronoun(k, 'poss'))
            else:
                t = np(k, ctx, top=False)
                if 'BI_1' in k.markers() and t.startswith('also '):
                    t = t[5:]                        # 'also' of a genitive dependent scopes over the whole phrase
                    dets.insert(0, 'also')
                posts.append(('of', t, k.first_pos()))
        elif r == 'mod' and k.kind in ('conj', 'disjunct') and k.members and \
                all(m.kind == 'ne' or is_name(m) or word(m) in ('etc', 'others') for m in k.members) and                 any(word(m) in ('etc', 'others') for m in k.members) and \
                not n.concept.startswith('['):
            posts.append(('', np(k, ctx, top=False), 10 ** 6))   # 'munnAra, ... Axi parvawIya kRewra' = 'mountainous area munnara, ... etc'
        elif r == 'mod' and not k.concept.startswith(('[', '$')) and word(k) == 'full' \
                and [x.rel for x in k.kids] == ['mod'] and not k.kids[0].concept.startswith('['):
            mods.append(word(k.kids[0]) + '-full')   # 'romAMca Bare' = 'adventure-full' (compound adjective)
        elif r == 'mod' and k.kind == 'span':
            posts.append(('', np(k, ctx, top=False), 10 ** 6))   # 'rAjyakAla (1433-1466)' = 'regime ... from 1433 to 1466'
        elif r == 'mod' and is_name(k) and 'place' in (k.sem or '') and (n.kind in ('conj', 'disjunct') or 'org' in (n.sem or '')):
            posts.append((',', np(k, ctx, top=False), 10 ** 6))  # 'pratApa saMgrahAlaya ..., uxayapura'
        elif r in ('mod', 'rvks', 'rbks', 'rbk', 'nc') or (r == 'rs' and False):
            t = np(k, ctx, top=False)
            if 'hI_1' in k.markers() and t.endswith(' only') and POS.get(n.root, 'n') in ('n', 'x'):
                t = t[:-5]
                posts.append(('', 'only', 10 ** 7))   # 'alaga hI anuBava' = 'different experience only'
            tw = t.split(' ')
            vi_ = 1 if tw and tw[0] in FOCUS_PARTICLES and len(tw) > 1 else 0       # skip a leading 'also/only'
            w0 = tw[vi_] if tw else ''
            an0 = morph.analyse(w0)
            if r == 'mod' and POS.get(k.root) == 'v' and k.kind != 'cp' and w0 \
                    and not morph.is_predicative(w0) and not w0.endswith('ing') \
                    and not (morph.pp_lemmas(w0) - {w0}) \
                    and (any(x.startswith('<vblex><inf>') for x in an0) or not any(x.startswith('<vblex><pp>') for x in an0)):
                tw[vi_] = morph.verb(w0, 'ger')
                t = ' '.join(tw)
            if r == 'mod' and ((POS.get(n.root) == 'a' and POS.get(k.root) == 'a')
                               or (t in LISTS.get('degree_adjectives', set()) and not n.concept.startswith(('[', '$'))
                                   and ' ' not in head_word(n)
                                   and any(x.startswith('<adj>') for x in morph.analyse(head_word(n))))) \
                    and ' ' not in t \
                    and t not in ('very', 'most', 'more', 'quite', 'so', 'too', 'other', 'another', 'such', 'same', 'own') \
                    and not t.endswith('ly'):
                t = (t[:-1] + 'ily') if t.endswith('y') else (t[:-2] + 'ly') if t.endswith('le') else t + 'ly'
            if 'superl' in (n.gnp or '') and POS.get(k.root) in ('a', 'x') and POS.get(n.root) != 'a' and ' ' not in t:
                t = morph.adj(t, 'sup')
            if 'superl' in (k.gnp or '') and ' ' not in t and not t.endswith('est') and not t.startswith('most'):
                t = morph.adj(t, 'sup')
            if r == 'mod' and POS.get(n.root, 'n') == 'n' and ' ' not in t and t.endswith('ly') \
                    and any(a.startswith('<adv>') for a in morph.analyse(t)) and morph.analyse(t[:-2]):
                t = t[:-2]                           # 'pUrNawaH aBAva' = 'complete lack' (adverb on a noun)
            if t in LISTS.get('degree_adjectives', set()) and any(x.rel == 'mod' and x is not k and x.pos > k.pos for x in n.kids):
                t = t + 'ly'                          # 'extreme beautiful' -> 'extremely beautiful'
            if not t:
                continue
            if (k.kind == 'ne' or is_name(k)) and any(not x.concept.startswith('[') and word(x) in ('named', 'called')
                                                     for x in k.kids):
                posts.append(('', re.sub(r'^called ', 'named ', t), -1))   # 'flowers named nilakurinji'
                continue
            has_deps = any(kk.rel in VERBAL_DEP or kk.rel in ('r6', 'rs', 'pk1', 'rdl')
                           for kk in k.kids + [y for m in (k.members if k.kind == 'cp' else []) for y in m.kids])
            if k.concept.startswith('[') and t.split()[0] in LISTS.get('postnominal_heads', set()):
                posts.append(('', t, k.first_pos()))   # 'temple having two sanctum-sanctorum'
                continue
            clause_deps = any(kk.rel in VERBAL_DEP and kk.rel not in ('rn',) for kk in k.kids)
            if core == 'name' and (k.kind == 'ne' or is_name(k)):
                posts.append(('', t, k.first_pos()))   # 'by name dehara'
                continue
            if (has_deps and (is_verbal(k) or POS.get(k.root) in ('a', 'v') or k.kind == 'cp'
                              or (t.split()[0] in PREP_HEADS and len(t.split()) > 1))) or \
                    (clause_deps and not k.concept.startswith('[')):   # 'small fish available in caves'
                posts.append(('', t, k.first_pos()))
            else:
                mods.append(t)
        elif r == 'rs' and not k.concept.startswith(('[', '$')) and \
                morph.noun(word(k), 'pl') in (morph.noun(core, 'pl'), core) or (r == 'rs' and word(k) == core):
            # apposition that translates to the head itself ('boGaxoM (tanala)'): one word, keep its plural
            if is_plural(k) and not core.endswith('s'):
                core = morph.noun(core, 'pl')
            quants += [np(x, ctx, top=False) for x in k.kids if x.rel in ('card', 'quant')]
        elif r == 'rs' and re.sub(r'_\d+$', '', k.root) == 'svayaM':
            refl = 'themselves' if is_plural(n) else ('herself' if 'female' in (n.sem or '') else
                                                      'himself' if n.sem in ('male', 'per') else 'itself')
            posts.append(('', apply_markers(k, refl), k.first_pos()))   # 'SraxXAlu svayaM hI' = 'devotees themselves only'
        elif r == 'rs':
            # apposition: before a noun head (Hindi order), after an adjective/participle host ('called X')
            if (k.kind == 'ne' or is_name(k)) and POS.get(n.root) not in ('a', 'v') and not is_verbal(n)                     and n.kind != 'ne' and not is_name(n)                     and any(x is not k and x.rel in ('mod', 'r6', 'ord', 'card') for x in n.kids):
                posts.append((',', np(k, ctx, top=False), 10 ** 5))   # 'nearest airport of pirumala, kocci ...'
            elif POS.get(n.root) == 'a' or is_verbal(n) or morph.is_predicative(core):
                posts.append(('', np(k, ctx, top=False), k.first_pos()))
            elif n.kind == 'ne' and k.kind == 'ne' and own_pos(k) < own_pos(n) and not any(x.sem in ('per', 'male', 'female') for x in (n, k)):   # persons keep C2 (name first)
                SUFFIX[('pre_app', id(n))] = np(k, ctx, top=False)   # two names: Hindi order (applied after the loop)
            elif n.kind == 'ne' or (is_name(n) and not n.concept.startswith('$')):
                posts.append((',', np(k, ctx, top=False), 10 ** 5))   # 'maharaja shivi, ancestor of lord rama'
            elif (k.kind == 'ne' or is_name(k)) and any(x is not k and x.rel in ('mod', 'r6', 'ord', 'card') for x in n.kids):
                posts.append((',', np(k, ctx, top=False), 10 ** 5))   # 'nearest railway station, kannura'
            else:
                mods.append(np(k, ctx, top=False))
        elif r in ('re', 'ru') and np(k, ctx, top=False).endswith('-like'):
            mods.insert(0, np(k, ctx, top=False))      # 'sIDZInumA saMracanAeM' = 'step-like structures'
        elif r == 're':
            posts.append(('like', np(k, ctx, top=False), k.first_pos()))
        elif r == 'rn':
            posts.append(('among', np(k, ctx, top=False), 10 ** 6))   # partitive 'X among Y' closes the phrase
        elif r in VERBAL_DEP and r not in ('k1', 'k2', 'k1s', 'k2s'):
            p = prep_for(k, ctx)
            t = np(k, ctx, top=False)
            posts.append((p, t, k.first_pos()))
        elif r in ('k1', 'k2', 'k2s', 'k1s'):
            posts.append(('of' if (r == 'k1' and 'kqw' in (n.gnp or '') and n.root.split('_')[0] != 'ho' and not k.concept.startswith('$') and n.rel in ('rh', 'r6', 'k1', 'k2', 'k5', 'k7')) else '', np(k, ctx, top=False), (-1 if (core == 'being' and r in ('k1s', 'k2s')) else k.first_pos())))   # 'falling of water'; 'being X in Y'
    if core in ('later', 'earlier') and not n.concept.startswith('['):
        o = next((k for k in n.kids if k.rel in ('r6', 'rdl')), None)
        if o is not None:                            # '15vIM SawAbxI ke bAxa kI' = 'later than 15th century'
            return apply_markers(n, core + ' than ' + np(o, ctx, top=False))
    dur = next((k for k in n.kids if k.rel == 'rkl'), None)
    if dur is not None and core in ('afterwards', 'later', 'previously', 'earlier', 'prior'):
        core = 'after' if core in ('afterwards', 'later') else 'before'   # 'X ke paScAwa' = 'after X'
    if core in ('after', 'before') and dur is not None and not any(x.rel in ('quant', 'card') for x in dur.kids):
        return apply_markers(n, core + ' ' + np(dur, ctx, top=False))   # 'svawaMwrawA prApwi se pUrva' = 'before X'
    if core in ('after', 'before') and dur is not None:
        o = next((k for k in dur.kids if k.rel == 'r6'), None) or next((k for k in n.kids if k.rel == 'r6'), None)
        dt = ' '.join([np(x, ctx, top=False) for x in dur.kids if x.rel in ('quant', 'card')] + [head_word(dur)])
        ot = (pronoun(o, 'obj') if o.root.startswith('$') else np(o, ctx, top=False)) if o is not None else ''
        return apply_markers(n, ' '.join(x for x in (dt, core, ot) if x))    # 'kaI varRa bAxa' = 'several years after'
    sp = next((k for k in n.kids if k.rel in ('r6', 'rdl') and k.kind == 'span'), None)
    if core == 'between' and sp is not None:
        a0 = next((m for m in sp.members if m.role == 'start'), None)
        b0 = next((m for m in sp.members if m.role == 'end'), None)
        if a0 is not None and b0 is not None:        # 'kArwika Sukla se pUrNimA ke bIca' = 'between X and Y'
            return apply_markers(n, 'between %s and %s' % (np(a0, ctx, top=False), np(b0, ctx, top=False)))
    if core in PREP_HEADS and not n.concept.startswith('['):
        objs = [k for k in n.kids if k.rel in ('r6', 'rdl')]
        if objs:
            o = objs[0]
            ot = pronoun(o, 'obj') if o.root.startswith('$') else np(o, ctx, top=False)
            rest = [t for p, t, _ in posts if t and not (p == 'of' and t == np(o, ctx, top=False))]
            dets = [d for d in dets if d not in ('its', 'their', 'his', 'her', 'my', 'our', 'your')]
            return apply_markers(n, ' '.join(dets + quants + mods + [core, ot] + rest).strip())
    mods = [('extremely' if (t == 'extreme' and (POS.get(n.root) in ('a', 'x') or len(mods) > 1)) else t) for t in mods]
    lead = [t for t in mods if t in ('last', 'first', 'next', 'previous', 'following')]
    if lead and quants:
        mods = [t for t in mods if t not in lead]
        quants = lead + quants
    words = []
    pre_app = SUFFIX.pop(('pre_app', id(n)), None)
    if pre_app:                                      # 'maxrAsa rAjya (varwamAna wamilanAdu)' = 'madrasa rajya, present tamilanadu'
        core = pre_app + ', ' + ' '.join(mods + [core])
        mods = []
    if n.concept.startswith('[') and core.split() and core.split()[0] in LISTS.get('postnominal_heads', set()) and quants:
        core = ' '.join([core.split()[0]] + quants + core.split()[1:])   # 'having two sanctum-sanctorum'
        quants = []
    if re.search(r'comp[ae]?rmore', n.gnp or '') and not is_adjective_word(head_word(n)) and not n.concept.startswith('[') \
            and n.rel != 'k5':
        dets = dets + ['more']                       # comparative noun: 'pulisa Porsa jyAxA' = 'more police force'
    if 'such' in dets and 'what' in mods:
        mods.remove('what')
        dets = ['what'] + [d for d in dets if d != 'what']   # 'EsA kyA karma' = 'what such work'
    detlike = [t for t in mods if t in ('some', 'any', 'every', 'each', 'no', 'all')]
    if detlike:                                      # 'koI' annotated as mod still leads: 'some extraordinary miracle'
        mods = [t for t in mods if t not in detlike]
        quants = detlike + quants
    if quants in (['some'], ['any']) and not dets and not n.concept.startswith(('[', '$')) \
            and POS.get(n.root) == 'a' and ' ' not in core:
        core, quants = quants[0] + 'thing ' + core, []   # 'kuCa asAXAraNa' (no noun) = 'something extraordinary'
    if dets == ['which'] and core in ('something', 'anything') and not quants and not mods:
        dets, core = [], 'whatever'                  # 'jo kuCa' = 'whatever'
    if 'such' in dets and quants and quants[0] not in ('a', 'an', 'one'):
        quants, dets = quants + ['such'], [d for d in dets if d != 'such']   # 'any such', but 'such a'
    if core in ('all', 'alls') and dets and not quants:
        core, dets = dets[0], ['all']                # 'ina saba' = 'all these'
    elif 'all' in quants and dets:
        quants = [t for t in quants if t != 'all']
        dets = ['all'] + dets
    if core == 'other' and is_plural(n) and not n.concept.startswith(('[', '$')):
        core = 'others'                              # 'anya 15 prawiSawa' = 'others 15 percent'
    if core in ('percentage', 'percentages') and any(k.rel == 'card' for k in n.kids):
        core = 'percent'                             # '55 prawiSawa' = '55 percent'
    if core in PREP_HEADS and dets and not quants and not mods:
        core, dets = core + ' ' + ' '.join(dets), []   # 'isa xOrAna' = 'during this'
    lead_q = [t for t in quants if t in ('every', 'each')]
    if lead_q:
        quants = lead_q + [t for t in quants if t not in lead_q]   # 'hara cAra GaMte' = 'every four hours'
    words += dets
    words += quants
    words += mods
    if n.sem in ('AD', 'BC') and not n.concept.startswith('$'):
        core = core + ' ' + n.sem
    words.append(core)
    # of-chain: Hindi "A kA B" -> "B of A"; several r6 -> closest first
    for p, t, _ in sorted(posts, key=lambda x: -x[2] if x[0] == 'of' else x[2]):
        if t:
            words.append((p + ' ' + t).strip())
    text = ' '.join(w for w in words if w).replace(' , ', ', ')
    text = re.sub(r'\betc etc\b', 'etc', text)
    text = re.sub(r'\b(a|an) (another)\b', r'\2', text)
    text = re.sub(r'\ban other\b', 'another', text)            # 'eka anya' (quant) = 'another'
    text = re.sub(r'\bone another\b', 'one other', text)       # 'eka anya' (card) = 'one other'
    text = re.sub(r'\ba ([aeiou])', r'an \1', text)
    return apply_markers(n, text)


def demonstrative(d, head):
    if not d.root.startswith('$') and word(d) and word(d) != '-':
        return word(d)                               # lexical determiner: 'uparokwa maMxira' = 'above temple'
    if re.sub(r'_\d+$', '', d.root) == '$yax':
        return 'which'
    if re.sub(r'_\d+$', '', d.root) == '$wyax' and 'distal' not in d.markers() and any(
            k is not d and ((k.rel in ('quant', 'card') and re.sub(r'_\d+$', '', k.root) in ('koI', 'eka'))
                            or (k.rel in ('dem', 'quant', 'mod') and k.root.startswith('$kim'))) for k in head.kids):
        return 'such'                                # 'aisA koI upAya' = 'any such solution'
    pl = is_plural(head)
    mk = d.markers()
    if 'distal' in mk:
        return 'those' if pl else 'that'
    return 'these' if pl else 'this'


def apply_markers(n, text):
    pre, post = [], []
    for m in n.markers():
        if m in ('proximal', 'distal', 'respect', 'def') or m.startswith('['):
            continue
        en, where = MARKERS.get(m, (EN.get(m, ''), 'pre'))
        if m == 'hI_1' and (n.rel == 'intf' or text in DEGREE_WORDS):
            continue
        if m == 'sI_1' and n.rel in ('quant', 'intf'):
            continue                                 # 'bahuwa sI xukAneM' = 'many shops' (agreement particle)                                 # 'badZA hI' = 'very', 'behaxa hI' = 'extremely'
        if en in FOCUS_PARTICLES and m != 'hI_1':     # kevala/mAwra/sirPa/BI -> 'only X', 'also X'; emphatic hI -> 'X only'
            where = 'pre'
        if not en or en == '-':
            continue
        (post if where == 'post' else pre).append(en)
    if text == 'still':
        pre = [x for x in pre if x != 'also']
    out = ' '.join(pre + [text] + post).strip()
    out = re.sub(r'^like (.+) like$', r'like \1', out)
    return re.sub(r'\blike (.+) like$', r'like \1', out)


# ----------------------------------------------------------------------------- layer C : case marking
def is_adverbial(w):
    # adverb/adjective that is never a noun (later, elsewhere, low): takes no preposition
    if ' ' in w:
        return False
    t = morph.analyse(w)
    return bool(t) and not any(x.startswith('<n>') or x.startswith('<np>') for x in t) and \
        any(x.startswith('<adv>') or x.startswith('<adj>') for x in t)


_MONTHS = {'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october',
           'november', 'december'}


def prep_for(n, ctx):
    r = n.rel
    p = RELPREP.get(r, '-')
    if r in ('k1', 'k2', 'k1s', 'mod') or p == '-':
        p = ''
    if n.root.startswith('$') and r in ('k7p', 'k7', 'k7t', 'krvn', 'rh', 'k2p'):
        if pronoun(n, 'obj') in ('here', 'there', 'when', 'where', 'how', 'why'):
            return ''
    if r == 'vkvn' and head_word(n) in ('kind', 'type', 'manner') and any(k.rel == 'dem' for k in n.kids):
        return 'in'                                  # 'isa waraha' = 'in this way'
    if r == 'k7t' and head_word(n) in ('day', 'days') and is_plural(n) and any(k.rel == 'dem' for k in n.kids):
        return 'in'                                  # 'una xinoM' = 'in those days'
    if r == 'k3' and not n.concept.startswith(('[', '$')) and head_word(n) == 'medium' and \
            any(k.rel == 'r6' for k in n.kids):
        return 'through'
    hv = n.sent.by.get(n.head)
    if r == 'k2p' and hv is not None and verb_lemma(hv).split()[0] in LISTS.get('direct_goal_verbs', set()):
        return ''                                    # 'reach X', 'enter X' take the goal directly
    if re.sub(r'_\d+$', '', n.root) in ('$yax', '$kim'):
        return ''                                    # relative / question word carries its own preposition
    hw = (head_word(n) if not n.concept.startswith('[') else construction_text(n, ctx)).split()
    hw = hw[-1].lower() if hw else ''
    if n.kind in ('conj', 'disjunct') and n.members and r in ('k7p', 'k7'):   # a place list takes its first item's preposition
        f0 = sorted([m for m in n.members if m.role.startswith('op')] or n.members, key=lambda m: _op_no(m.role))[0]
        hw0 = (head_word(f0) if not f0.concept.startswith('[') else construction_text(f0, ctx)).split()
        hw = hw0[-1].lower() if hw0 else hw
    if r in ('k7p', 'k7'):
        hws = (head_word(n) if not n.concept.startswith('[') else construction_text(n, ctx)).lower().split()
        hws += [word(x).lower() for x in n.kids if x.rel == 'mod' and not x.concept.startswith(('[', '$')) and word(x)]
        gv = n.sent.by.get(n.head)
        located = gv is not None and any(w in LISTS.get('location_verbs', set())
                                         for w in (word(gv) or '').split() + verb_lemma(gv).split()[:1])
        if hw in LISTS['on_heads'] or (located and hw in LISTS.get('on_heads_when_located', set())):
            p = 'on'                                 # 'nadI para sWiwa' = 'situated on river' (but 'floating in river')
        elif hw in LISTS['at_heads'] or any(w in LISTS['at_heads'] for w in hws):
            p = 'at'                                 # 'saMgama sWala para' = 'at confluence place'
        if r == 'k7p' and not n.concept.startswith(('[', '$')) and not is_name(n) and is_adverbial(word(n)):
            p = ''
        if r == 'k7' and hw in ('days', 'hours', 'minutes', 'months', 'years', 'day', 'hour', 'minute', 'month', 'year') \
                and any(k.rel == 'card' for k in n.kids) and not n.concept.startswith('['):
            p = 'in'                                 # '27 xina meM' = 'in 27 days'
    elif r == 'k7t' and n.sem == 'clocktime':
        p = 'at'                                     # '2 baje' = 'at 2'
    elif r == 'k7t' and hw in _MONTHS:
        p = 'on'                                     # '21 jUna ko' = 'on 21 June'
    elif r == 'k7t' and n.kind in ('conj', 'disjunct') and any(head_word(m).lower() in _MONTHS for m in n.members
                                                                 if not m.concept.startswith('[')):
        p = 'on'
    elif r == 'k7t' and 'kqw' in (n.gnp or '') and not n.concept.startswith('$') and any(k.rel == 'k1' for k in n.kids):
        p = 'on'                                     # 'hone para' = 'on X happening'
    elif r == 'k7t':
        txt = np(n, ctx, top=False).lower().split()
        if not txt:
            return ''
        if txt[0] in LISTS['none_time'] or hw in LISTS['none_time'] or word(n) in LISTS['none_time']                 or txt[0] in PREP_HEADS or txt[0] in ('at', 'in', 'on', 'by', 'for', 'from') \
                or txt[0] in LISTS['none_time_mods'] \
                or (not n.concept.startswith(('[', '$')) and not is_name(n) and is_adverbial(word(n))):
            p = ''
        elif 'whole' in txt[:2] or (any(t in LISTS['for_time'] for t in txt[:2]) and hw == 'time'):
            p = 'for'
        elif (hw in LISTS['duration_heads'] or hw + 's' in LISTS['duration_heads']) and \
                (any(k.rel in ('card', 'quant') or k.kind == 'span' for k in n.kids) or
                 (hw in LISTS['duration_heads'] and not any(k.rel == 'mod' for k in n.kids))) and not any(k.rel == 'dem' for k in n.kids) and \
                not any(word(x) in ('once', 'twice') or 'times' in (word(x) or '').split()
                        for x in (n.sent.by[n.head].kids if n.head in n.sent.by else [])) and \
                not set(txt) & {'before', 'after', 'ago', 'later'}:
            p = 'for'                                # 'eka mAha se' / 'kuCa xinoM se' = 'for one month' / 'for some days'
        elif hw in ('evening', 'morning') and not any(k.rel == 'r6' for k in n.kids):
            p = 'in'                                 # 'SAma meM baDZa jAye' = 'increases in evening'
        elif hw in LISTS['on_heads'] or n.kind == 'calendar' and any(re.fullmatch(r'\d{1,2}(st|nd|rd|th)?', t) for t in txt):
            p = 'on'
        elif hw in LISTS['at_heads'] or (hw == 'time' and (any(t in ('this', 'that', 'these', 'those', 'one', 'a') for t in txt)
                                                          or (any(k.rel == 'r6' for k in n.kids) and not n.concept.startswith('[')
                                                              and not any(k.rel == 'mod' for k in n.kids)))):
            p = 'at'
        else:
            p = 'in'
    elif r == 'k3' and n.head in n.sent.by and n.sent.by[n.head].rel in ('mod', 'rbks') and \
            (POS.get(n.sent.by[n.head].root) == 'v' or 'kqw' in (n.sent.by[n.head].gnp or '') or n.sent.by[n.head].rel == 'rbks'):
        p = 'by'
    elif r == 'k5' and hw in LISTS.get('duration_heads', set()) and is_plural(n):
        p = 'for'                                    # 'saxiyoM se' = 'for centuries'
    elif r == 'k5' and re.search(r'comp[ae]?rmore', n.gnp or ''):
        p = 'more than'
    elif r in ('k3', 'rh') and hw in LISTS['from_heads']:
        p = 'from'
    elif r == 'k3' and 'kqw' in (n.gnp or '') and not n.concept.startswith(('[', '$')):
        p = 'by'                                     # verbal noun as means: 'piMdaxAna karane se' = 'by offering'
    elif r == 'k3' and hw in MANNER_HEADS:
        p = 'in'                                     # 'vEjFAnika warIke se' = 'in scientific manner'
    elif r == 'k3':
        p = 'with'
        if hw in LISTS['by_heads'] or n.kind == 'cp' or is_verbal(n) or ctx.get('passive_agent') is n \
                or (hw.endswith('ing') and any(t.startswith(('<vblex><ger>', '<vblex><pprs>')) for t in morph.analyse(hw))):
            p = 'by'
        gv0 = n.sent.by.get(n.head)
        if gv0 is not None and gv0.kind == 'cp' and gv0.rel == 'main':
            vl0 = verb_lemma(gv0).split()
            if vl0 and len(vl0) == 1 and morph.analyse(vl0[0]) and \
                    all(t.startswith(('<vblex><pp>', '<adj>')) for t in morph.analyse(vl0[0])):
                p = 'by'                             # means of a passive-like cp: 'snAna se prApwi howI hE' = 'is attained by'
    if r == 'rblsk' and not is_verbal(n):
        p = 'at'
    if r == 'rask1' and 'samAveSI' in ' '.join(n.markers()):
        p = 'besides'                                # 'pORtika hone ke alAvA' = 'besides being nutritious'
    if r == 'krvn' and hw in ('percent', 'percentage', 'percentages'):
        p = 'by'                                     # '10 prawiSawa kama' = 'decreases by 10 percent'
    if r in ('k7', 'k7p') and hw == 'extent':
        p = 'to'                                     # 'kAPI haxa waka' = 'to considerable extent'
    if r == 'k2p' and hw in ('side', 'direction') and any(k.rel == 'r6' for k in n.kids) and not n.concept.startswith('['):
        return 'towards'
    if r == 'k2p' and not n.concept.startswith(('[', '$')) and not n.kids and \
            (is_adverbial(word(n)) or word(n) in ('forward', 'backward', 'back', 'ahead', 'away', 'home', 'up', 'down')):
        p = ''                                       # 'Age (kI ora)' = 'forward'
    if r == 'krvn' and not n.concept.startswith(('[', '$')) and not is_verbal(n) and POS.get(n.root) != 'v':
        if hw in LISTS['from_heads']:
            p = 'from'                               # 'Silpa kI xqRti se' = 'from view of sculpture'
        elif hw in MANNER_HEADS and any(k.rel == 'dem' for k in n.kids):
            p = 'in'                                 # 'is prakAra' = 'in this way'
        elif hw not in MANNER_HEADS and hw != 'time' and not is_adverbial(word(n)) and any(k.rel == 'mod' for k in n.kids):
            p = 'with'                               # 'sacce mana se' = 'with true heart'
    gov = n.sent.by.get(n.head) if n.head else None
    if gov is not None and r in ('k5', 'k3', 'k7', 'k4', 'k7p') and not gov.concept.startswith(('[', '$')):
        gw = (word(gov) or '').split()
        if gw and gw[-1] in GOVERNED:
            p = GOVERNED[gw[-1]]
            if p == '-':
                p = ''                               # 'jalaprapAwa se yukwa' = 'having waterfall'
    if gov is not None and (gov.kind == 'cp' or POS.get(gov.root) == 'v' or gov.tam):
        vl = verb_lemma(gov)
        vg = vl.split()
        key = (vl, r) if (vl, r) in VERB_GOVERNED else ((vg[0], r) if vg and (vg[0], r) in VERB_GOVERNED else None)
        if key:
            p = '' if VERB_GOVERNED[key] == '-' else VERB_GOVERNED[key]   # 'rule over X', 'gift X' (no 'to')
    if n.kind == 'span' or hw in PREP_HEADS or hw == 'away':
        p = ''
    return p


# ----------------------------------------------------------------------------- layer D : verb group
TRANSITIVE_ONLY = set(LISTS.get('transitive_only', set()))


def verb_lemma(n):
    """English verb lemma of a verb node; never empty (a malformed USR verb falls back to 'be')."""
    return _verb_lemma_raw(n).strip() or 'be'


def _verb_lemma_raw(n):
    if n.kind == 'cp':
        km = next((m for m in n.members if m.role == 'kriyAmUla'), None)
        vb = next((m for m in n.members if m.role == 'verbalizer'), None)
        if km and vb:
            lroot = vb.root.split('_')[0]
            cands = sorted(CP_INDEX.get('%s+%s' % (km.root.rsplit('_', 1)[0], lroot), []))
            # dictionary convention <kriyAmUla>+<light verb>_<n>: prefer the entry tagged with this USR sense
            hit = next((k for _, k in cands if km.root in SL.get(k, [])), None) or (cands[0][1] if cands else None)
            if hit and EN.get(hit, '-') != '-':
                return EN[hit]
            kw = construction_text(km, {}) if km.concept.startswith('[') else word(km)
            if lroot in ('kara', 'karavA', 'karA', 'ho', 'A', 'jA', 'pahuzca') and ' ' not in kw and kw:
                pl_ = morph.pp_lemmas(kw)                # 'samboXiwa karanA' = 'address' (the noun part is a verb form)
                if pl_ and lroot in ('kara', 'karavA', 'karA'):
                    return sorted(pl_)[0]
                if lroot not in ('kara', 'karavA', 'karA') and pl_ and kw.endswith('ed'):
                    return sorted(pl_)[0]
            if lroot in ('kara', 'karA', 'karavA', 'banA') and kw and ' ' not in kw and                     (POS.get(km.root) == 'a' or (morph.analyse(kw) and all(t.startswith('<adj>') for t in morph.analyse(kw)))):
                return 'make ' + kw                  # 'upalabXa karAnA' = 'make available'
            return '%s %s' % (LIGHT.get(lroot, 'do'), kw)
        return word(km) if km else 'do'
    w = word(n)
    if n.root.split('_')[0] in ('hE', 'WA'):
        return 'be'
    # idioms: verb + shade (vector) verb stored like complex predicates, e.g. Ko+jA_1 = 'get lost'
    for m in n.markers():
        sh = re.match(r'^\[shade:([^_\]]+)', m)
        if sh:
            cands = sorted(CP_INDEX.get('%s+%s' % (n.root.rsplit('_', 1)[0], sh.group(1)), []))
            hit = next((k for _, k in cands if n.root in SL.get(k, [])), None)   # explicit idiom entries only
            if hit and EN.get(hit, '-') != '-':
                return EN[hit]
    return w


def tam_is_passive(tam):
    return bool(re.match(r'^yA_(jAwA|gayA|jA)', tam or ''))


def tam_of(n):
    if n.kind == 'cp':
        vb = next((m for m in n.members if m.role == 'verbalizer'), None)
        return vb.tam if vb else ''
    return n.tam


def verb_group(s, ctx):
    v = s.main
    if v is None:
        return ''
    lem = ctx.get('lemma_override') or verb_lemma(v)
    if ctx.get('possession'):
        lem = 'have'
    tam = tam_of(v)
    t = TAM.get(tam, {'tense': 'present', 'aspect': 'simple', 'modal': '-'})
    tense, aspect, modal = t['tense'], t['aspect'], t['modal']
    if any(m.startswith('[shade:cuka') for m in v.markers() + [x for mm in v.members for x in mm.markers()]) \
            and aspect == 'simple':
        aspect = 'perfect'                           # 'ho cuke the' = 'had passed away' (completed)
    explicit_k1 = any(k.rel == 'k1' for k in (s.main.kids if s.main is not None else []))
    shade_passive = v.root.split('_')[0] == 'kara' and any(m.startswith('[shade:jA') for m in v.markers())
    passive = s.stype.startswith('pass') or (tam_is_passive(tam) and not explicit_k1) or shade_passive \
        or getattr(s, 'voice_override', '') == 'passive'   # 'CodZatI calI gaIM' with k1: active perfective
    if lem.split()[0] == 'prove' and aspect == 'perfect' and not any(k.rel in ('k1s', 'k2s', 'k2') for k in v.kids + [x for m in v.members for x in m.kids]):
        passive = True                               # 'yaha sAbiwa huA hE' = 'this has been proved'
    neg = ('negative' in s.stype and not getattr(s, '_in_rc', False)) or any(k.rel == 'neg' for k in v.kids)
    if modal == 'may' and tam in ('e_1', 'e_2') and ctx.get('question'):
        modal = 'should'
    if ctx.get('causative') and not passive:
        lem = 'get ' + morph.verb(lem.split()[0], 'pp') + ''.join(' ' + w for w in lem.split()[1:])
    words = lem.split()
    if words and words[0] in ('is', 'are', 'was', 'were', 'am', 'been', 'being'):
        words[0] = 'be'                              # dictionary gives a finite 'be' form ('ho_17' = 'is')
        lem = ' '.join(words)
    if words and words[0] not in ('be', 'get'):
        words[0] = morph.base_verb(words[0])        # 'happened' -> 'happen', 'fell' -> 'fall'
        lem = ' '.join(words)
    if words[0] != 'be' and len(words) == 1 and morph.analyse(words[0]) \
            and all(x.startswith('<adj>') for x in morph.analyse(words[0])):
        lem = 'be ' + lem                            # 'saksham ho' = 'be capable'
        words = lem.split()
    if v.kind != 'cp' and words[0] != 'be' and len(words) == 1 and             (POS.get(v.root.split('-')[0]) == 'a' or morph.is_predicative(words[0])):
        lem = 'be ' + lem
        words = lem.split()
    head, rest = words[0], ' '.join(words[1:])
    if head == 'be' and rest and aspect == 'perfect' and modal == '-':
        aspect = 'simple'
    no_obj = not any(k.rel == 'k2' for k in v.kids + [x for m in v.members for x in m.kids])
    has_clause_obj = any(x.disc and x.disc.startswith(s.sid + '.') and x.disc.endswith(':vAkyakarma')
                         for o in ALL_SENTS.values() if o is not s for x in o.nodes)
    if tam_of(v) in ('e_1', 'e_2') and not any(k.rel == 'k1' for k in v.kids):
        has_clause_obj = True                         # imperative: 'biMxu ko xeKeM' = 'look at the point'
    if any(k.rel == 'k1' and k.root.startswith(('$addressee', '$speaker')) for k in v.kids):
        has_clause_obj = True                         # a speech-act pronoun is the doer: 'Apa xeKa sakawe hEM' = 'you can see'
    if not passive and head in TRANSITIVE_ONLY and no_obj and not rest and not has_clause_obj:
        passive = True
        if aspect == 'perfect' and tense == 'present' and modal == '-':
            aspect = 'simple'                 # 'bana hai' -> 'is built' (resulting state)
    # generic-subject construction (no k1/k2): English impersonal passive 'it is said'
    if not passive and ctx.get('no_subject') and no_obj and head in LISTS.get('impersonal_verbs', set()) and not ctx.get('imperative') \
            and not ctx.get('question'):
        passive = True
        ctx['impersonal'] = True
    if ctx.get('imperative'):
        if modal in ('keep', 'start'):              # 'karawe raheM' = 'keep doing'
            return ('do not ' if neg else '') + modal + ' ' + morph.verb(head, 'ger') + (' ' + rest if rest else '')
        return ('do not ' if neg else '') + lem
    pl = ctx.get('subj_plural', False)
    p1 = ctx.get('subj_person1', False)
    sg3 = not pl and not p1

    def fin(form_present, form_past):
        return form_present if tense == 'present' else form_past

    if passive and head not in ('be', 'get'):
        pp = morph.verb(head, 'pp')
        main = (pp + ' ' + rest).strip()
        if ctx.get('causative_passive'):
            main = 'got ' + main                     # causative passive: 'had been got built'
        chain = ['be']
    else:
        main = None
        chain = []
    out = []
    if modal in ('can', 'should', 'may', 'would', 'must'):
        out.append(modal if tense != 'past' or modal != 'can' else 'could')
        if neg:
            out.append('not')
        if aspect == 'perfect' or tense == 'future' and aspect == 'perfect':
            out.append('have')
            out.append(morph.verb('be', 'pp') if chain else morph.verb(head, 'pp') + (' ' + rest if rest else ''))
            if chain:
                out.append(main)
        else:
            out.append('be' if chain else lem)
            if chain:
                out.append(main)
        return ' '.join(out)
    if modal == 'have to':
        out.append('will have' if tense == 'future' else ('has' if sg3 else 'have') if tense == 'present' else 'had')
        out.append('to')
        out.append(('be ' + main) if chain else lem)
        return ' '.join(out)
    if modal in ('keep', 'start'):                   # 'kama howI jAwI hE' = 'keeps decreasing', 'galane lagawI hEM' = 'start melting'
        if neg:
            out.append(fin('does' if sg3 else 'do', 'did') + ' not')
            out.append(modal)
        elif tense == 'future':
            out.append('will ' + modal)
        else:
            out.append(morph.verb(modal, ('pres3sg' if sg3 else 'pres') if tense == 'present' else 'past'))
        out.append(('being ' + main) if chain else (morph.verb(head, 'ger') + (' ' + rest if rest else '')))
        return ' '.join(out)
    if modal == 'begin':
        out.append('began to')
        out.append(('be ' + morph.verb(lem.split()[0], 'pp') + (' ' + ' '.join(lem.split()[1:]) if len(lem.split()) > 1 else ''))
                   if passive else lem)                 # 'kahA jAne lagA' = 'began to be called'
        return ' '.join(out)
    if tense == 'future':
        out.append('will')
        if neg:
            out.append('not')
        out.append(('be ' + main) if chain else lem)
        return ' '.join(out)
    if aspect == 'perfect':
        aux = ('has' if sg3 else 'have') if tense == 'present' else 'had'
        out.append(aux)
        if neg:
            out.append('not')
        out.append(('been ' + main) if chain else (morph.verb(head, 'pp') + (' ' + rest if rest else '')))
        return ' '.join(out)
    if aspect == 'habitual' and tense == 'past':
        out.append('used to')
        out.append(('be ' + main) if chain else lem)
        return ' '.join(out)
    if aspect == 'progressive':
        out.append(fin('is' if sg3 else ('am' if p1 and not pl else 'are'), 'was' if (sg3 or p1) else 'were'))
        if neg:
            out.append('not')
        out.append(('being ' + main) if chain else (morph.verb(head, 'ger') + (' ' + rest if rest else '')))
        return ' '.join(out)
    # simple
    if chain or head == 'be':
        be = fin('is' if sg3 else ('am' if p1 and not pl else 'are'), 'was' if (sg3 or p1) else 'were')
        out.append(be)
        if neg:
            out.append('not')
        out.append(main if chain else rest)
        return ' '.join(w for w in out if w)
    if neg:
        out.append(fin('does' if sg3 else 'do', 'did'))
        out.append('not')
        out.append(lem)
        return ' '.join(out)
    form = ('pres3sg' if sg3 else 'pres') if tense == 'present' else 'past'
    return (morph.verb(head, form) + (' ' + rest if rest else '')).strip()


# ----------------------------------------------------------------------------- layer E : clauses
def agent_noun(verb):
    """provide -> provider, give -> giver, protect -> protector (regular English agentive)."""
    if verb.endswith('e'):
        return verb + 'r'
    if verb.endswith(('ct', 'it')):
        return verb + 'or'
    return verb + 'er'


def nonfinite(n, ctx):
    """rpk / rsk / rvks / rbks / rt-with-verb clause: participle + object + other deps (Hindi order)."""
    lem = verb_lemma(n)
    if n.rel in ('k1s', 'k2s') and 'wawCIlAxi' in (n.gnp or '') and ' ' not in lem:
        obj = next((k for k in n.kids if k.rel == 'k2'), None)
        return agent_noun(lem) + ((' of ' + np(obj, ctx, top=False)) if obj is not None else '')   # 'provider of moksha'
    comp = next((k for k in n.kids if k.rel in ('k1s', 'k2s')), None)
    if lem.split()[0] == 'be' and n.rel in ('rsk', 'rpk') and comp is not None:
        neg0 = 'not ' if any(k.rel == 'neg' for k in n.kids) else ''
        return apply_markers(n, neg0 + 'being ' + np(comp, ctx, top=False))   # 'X kA na hokara' = 'not being X'
    if lem.split()[0] in ('be', 'become') and n.rel in ('rsk', 'rpk'):
        dep = next((k for k in n.kids if k.rel in ('k2', 'k7p', 'k7', 'k1', 'rp', 'k2p')), None)
        return ('via ' + np(dep, ctx, top=False)) if dep else ''
    words = lem.split()
    subj0 = next((k for k in n.kids if k.rel == 'k1'), None)
    if ((n.rel == 'k7t' and 'kqw' in (n.gnp or '')) or (n.rel == 'rh' and n.root.startswith('ho_5') and 'kqw' in (n.gnp or ''))
            or (n.rel == 'rblsk' and all(k.rel in ('k1', 'neg') for k in n.kids))) and subj0 is not None and n.kind != 'cp':
        rest0 = [k for k in n.kids if k is not subj0 and k.rel != 'neg']
        rest0 = sorted(rest0, key=lambda k: (0 if k.rel in ('k1s', 'k2s', 'k2') else 1, k.first_pos()))
        neg0 = 'not ' if any(k.rel == 'neg' for k in n.kids) else ''
        tail = []
        for k in rest0:
            pk = prep_for(k, ctx) if k.rel not in ('k1s', 'k2s', 'k2') else ''
            tail.append(((pk + ' ') if pk else '') + np(k, ctx, top=False))
        return apply_markers(n, ' '.join([np(subj0, ctx, top=False), neg0 + morph.verb(words[0], 'ger')] + words[1:] + tail))
    if words[0] in PREP_HEADS and n.kind != 'cp':
        dep = next((k for k in n.kids if k.rel in ('k2', 'k7p', 'k7', 'k1', 'k2p', 'rp')), None)
        return (words[0] + ' ' + np(dep, ctx, top=False)) if dep else words[0]
    if n.rel in ('rbks', 'rbk', 'mod') and words[0] == 'take' and any(k.rel == 'k2' for k in n.kids):
        o = next(k for k in n.kids if k.rel == 'k2')
        return apply_markers(n, 'with ' + np(o, ctx, top=False))   # 'X lie hue' = 'with X'
    if n.rel == 'rvks' and (tam_is_passive(n.tam) or (n.tam or '').startswith('yA_')):
        v = morph.verb(words[0], 'pp')               # 'maCalI meM pAyA jAne vAlA' = 'found in fish'
    elif n.rel in ('rbks', 'rbk') and words[0] in LISTS.get('stative_verbs', set()):
        v = morph.verb(words[0], 'ger')
    elif n.rel in ('rbks', 'rbk'):
        v = words[0] if morph.is_predicative(words[0]) else morph.verb(words[0], 'pp')
        if words[0] in LISTS.get('motion_verbs', set()):
            v = 'having ' + v
    elif n.rel in ('k1', 'k2', 'r6', 'k1s') or ('kqw' in (n.gnp or '') and n.rel not in ('rvks', 'rsk', 'rpk', 'rt', 'rh', 'mod')):
        v = morph.verb(words[0], 'ger')
    else:
        v = morph.verb(words[0], 'ger')
    v = ' '.join([v] + words[1:])
    obj = [k for k in n.kids if k.rel == 'k2']
    other = [k for k in n.kids if k.rel != 'k2' and k.rel not in ('neg',)]
    negated = any(k.rel == 'neg' for k in n.kids)
    if words and words[0] == 'be':
        other = sorted(other, key=lambda k: 0 if k.rel in ('k1s', 'k2s') else 1)   # 'being ema.teka. in geology'
    if n.rel in ('rvks', 'rbks', 'rbk', 'mod'):
        # English adjunct order inside a participle phrase: source/goal/place before manner, time and purpose
        order = ['k2p', 'k5', 'k7p', 'k7', 'k3', 'k5prk', 'krvn', 'k7t', 'rt', 'rh']
        other = sorted(other, key=lambda k: (order.index(k.rel) if k.rel in order else len(order), k.first_pos()))
    parts = [v]
    gov_k2 = VERB_GOVERNED.get((' '.join(words), 'k2')) or VERB_GOVERNED.get((words[0], 'k2'))
    for k in obj:
        if gov_k2 and gov_k2 != '-' and n.rel not in ('rbks', 'rbk'):
            parts.append(gov_k2 + ' ' + np(k, ctx, top=False))   # 'sunakara' = 'listening to X'
            continue
        if n.rel in ('rbks', 'rbk'):              # passive participle clause: 'one statue installed later'
            parts.insert(len(parts) - 1, np(k, ctx, top=False))
        else:
            parts.append(np(k, ctx, top=False))
    for k in other:
        if k.rel in NP_INTERNAL and k.rel not in ('mod',):
            continue
        fp = form_phrase(k, ctx)
        if fp:
            parts.append(fp)                         # 'canxrAkAra rUpa se banI' = 'formed in moon-shape form'
            continue
        p = prep_for(k, ctx)
        if k.rel == 'k2s' and words and words[0] == 'keep':
            p = ''                                   # 'muzha ko sAPa raKane' = 'keeping mouth clean'
        if n.kind == 'cp' and k.rel == 'k1' and words and words[-1] in GOVERNED:
            p = GOVERNED[words[-1]]                  # 'AkAra ke samAna honA' = 'being equal to shape'
        if k.rel == 'rh' and n.rel in ('rbks', 'rbk') and k.kind != 'cp':
            p = 'by'                                 # cause of a passive participle: 'jamAva se banI' = 'made by condensation'
        if k.rel == 'k3' and n.rel in ('rbks', 'rbk') and p == 'with':
            p = 'by'
        if k.rel == 'k1' and n.rel in ('rh', 'r6', 'k1', 'k2', 'k5', 'k7') and 'kqw' in (n.gnp or '') \
                and n.kind != 'cp' and not k.concept.startswith('$') and n.root.split('_')[0] != 'ho':
            p = 'of'                                 # subject of a verbal noun: 'pAnI ke girane se' = 'falling of water'
        if k.rel in ('k1', 'pk1') and n.rel in ('rbks', 'rbk'):
            p = 'by'
        if k.rel in ('k7p', 'k7') and words[0] in LISTS.get('motion_verbs', set()) and p == 'in':
            p = 'to'
        if k.rel in ('k7p', 'k7') and words[0] in LISTS.get('into_verbs', set()) and p in ('in', 'to'):
            p = 'into'                               # 'nicale hisse meM giranA' = 'falling into lower portion'
        if k.rel in ('k7p', 'k7', 'k2p') and words[0] in LISTS.get('direct_goal_verbs', set()):
            p = ''                                  # 'for reaching ganga mandira'
        if k.rel == 'rt' and is_verbal(k):
            p = ''
        parts.append((p + ' ' + np(k, ctx, top=False)).strip())
    text = ' '.join(x for x in parts if x)
    if negated and any(k.rel == 'neg' and re.sub(r'_\d+$', '', k.root) in ('bina', 'binA') for k in n.kids):
        text = 'without ' + text                     # 'upekRA kie bina' = 'without neglecting'
    elif negated:
        text = 'not ' + text                         # 'na hokara' = 'not being'
    if n.rel == 'rpk':
        # kar-participle: an active main clause with its own subject shares that subject -> bare 'V-ing'
        # ('leaving mountainous area', cp: 'having driven'); passive or subjectless main clause -> means 'by V-ing'
        m = n.sent.by.get(n.head)
        passive = n.sent.stype.startswith('pass') or (m is not None and tam_is_passive(tam_of(m)))
        has_subj = m is not None and any(k.rel in ('k1', 'pk1') for k in m.kids)
        if passive or not has_subj:
            text = 'by ' + text
        elif n.kind == 'cp':
            text = 'having ' + morph.verb(words[0], 'pp') + text[len(v):]
    elif n.rel == 'rt':
        text = 'for ' + text
    return apply_markers(n, text)


FRAME = {'k7t', 'rkl', 'rblak', 'rblpk', 'rblsk', 'krvn'}


MANNER_HEADS = {'form', 'way', 'manner', 'type', 'kind', 'fashion'}
DEGREE_WORDS = {'very', 'extremely', 'quite', 'so', 'too', 'most', 'more', 'much', 'highly'}


def manner_adverb(k):
    """krvn 'viSeRa rUpa se' -> 'specially': adjective + manner noun -> adverb (Apertium-free -ly rule)."""
    if k.rel != 'krvn' or word(k) not in MANNER_HEADS:
        return None
    mods = [x for x in k.kids if x.rel == 'mod']
    if len(mods) == 1 and k.kids == mods and mods[0].root.startswith('$kim'):
        return 'how'                                 # 'kisa prakAra' = 'how'
    if len(mods) != 1 or k.kids != mods or POS.get(mods[0].root) == 'n' or mods[0].concept.startswith('['):
        return None
    a = word(mods[0])
    if ' ' in a:
        return None
    if a.endswith('ly'):
        return a
    return (a[:-1] + 'ily') if a.endswith('y') else (a + 'ally') if a.endswith('ic') else (a[:-2] + 'ly') if a.endswith('le') else a + 'ly'


def form_phrase(k, ctx):
    """'X ke rUpa meM' = 'as X'; 'apaBraMSa rUpa meM' = 'in colloquial form'; 'X rUpa se' = 'in X form'."""
    if k.concept.startswith(('[', '$')) or word(k) != 'form' or k.rel not in ('krvn', 'k7', 'k7p', 'k3'):
        return None
    tgt = next((x for x in k.kids if x.rel == 'r6' or (x.rel == 'mod' and (x.concept.startswith('[') or is_name(x)))), None)
    if tgt is not None:
        t = np(tgt, ctx, top=False)
        if not tgt.concept.startswith('[') and ' ' not in t and is_adjective_word(t) and not is_name(tgt):
            return 'in ' + t + ' form'
        return 'as ' + t
    if k.rel == 'k3' and any(x.rel == 'mod' for x in k.kids):
        return 'in ' + np(k, ctx, top=False)
    return None


def chunk_text(k, ctx):
    if k.rel == 'r6pred':
        return 'of ' + np(k, ctx, top=False)
    fp = form_phrase(k, ctx)
    if fp:
        return apply_markers(k, fp)
    adv = manner_adverb(k)
    if adv:
        return apply_markers(k, adv)
    if k.rel == 'krvn' and not k.kids and not k.concept.startswith(('[', '$')) and ' ' not in word(k) \
            and not word(k).endswith('ly') \
            and ('xviwva' in (k.gnp or '')
                 or (not any(x.startswith('<adv>') for x in morph.analyse(word(k)))
                     and (POS.get(k.root) == 'a'
                          or (morph.analyse(word(k)) and all(x.startswith('<adj>') for x in morph.analyse(word(k))))))):
        w = word(k)                                  # manner adjective as adverb: 'XIre-XIre' = 'slowly'
        return apply_markers(k, (w[:-1] + 'ily') if w.endswith('y') else (w[:-2] + 'ly') if w.endswith('le')
                             else (w + 'y') if w.endswith('ll') else w + 'ly')
    if k.rel == 'intf' and not k.kids and word(k) == 'much':
        return apply_markers(k, 'very much')         # degree of a verb: 'bahuwa lubhAwA' = 'lures very much'
    if k.rel == 'k7t' and not k.concept.startswith(('[', '$')) and POS.get(k.root) == 'v' and 'kqw' in (k.gnp or ''):
        if any(x.rel == 'k1' for x in k.kids):
            return 'on ' + nonfinite(k, ctx)        # 'sUjana A jAne para' = 'on swelling coming'
        return 'while ' + nonfinite(k, ctx)          # 'Awe samaya' (time of a verbal form) = 'while coming'
    gv = k.sent.by.get(k.head)
    if k.rel == 'k2' and gv is not None and not k.concept.startswith(('[', '$')) \
            and (POS.get(k.root) == 'v' or any(x.startswith('<vblex>') for x in morph.analyse(word(k)))) \
            and morph.base_verb(verb_lemma(gv).split()[0]) in LISTS.get('infinitive_object_verbs', set()):
        t = nonfinite(k, ctx).split(' ', 1)          # 'jAnane kA prayAsa kiyA' = 'tried to know ...'
        return 'to ' + morph.verb(verb_lemma(k).split()[0], 'inf') + (' ' + t[1] if len(t) > 1 else '')
    if k.rel in ('rpk', 'rsk', 'rvks', 'rbks') or (k.rel == 'rt' and is_verbal(k)):
        t = nonfinite(k, ctx)
        return t
    p = prep_for(k, ctx)
    body = np(k, ctx)
    if not body:
        return ''
    if p == 'like' and body.endswith(' like'):
        body = body[:-5]
    if p == 'from' and re.match(r'^last \d+ (years|months|days|centuries|decades)', body.lower()):
        p = 'since'
    if p and not body.lower().startswith(p + ' '):
        lead = re.match(r'^((?:also|only|even|almost|about|nearly)\s+)+', body)
        if lead:
            return lead.group(0) + p + ' ' + body[lead.end():]
        return p + ' ' + body
    return body


SUFFIX = {}   # node id -> text appended to its chunk (frequency unit, standard of comparison)


_NOFILL = {'hE', 'ho', 'kara', 'jA', 'xe', 'le', 'raha', 'sakawA', 'Axi', 'nahIM', 'BI', 'hI', 'kevala', 'eka', 'yaha',
           'vaha', 'nAmaka', 'waraha', 'prakAra', 'Ora', 'A', 'mila', 'cala', 'rUpa', 'rupa', 'svayaM', 'anya', 'xUsarA',
           'saBI', 'kuCa', 'aneka', 'kaI', 'koI'}


def _lost_nodes(s, text):
    """Lexical (non-verb) USR nodes whose English word does not occur in the output."""
    low = text.lower()
    lost = []
    for n in s.nodes:
        c = n.concept
        if c.startswith(('[', '$', '@')) or re.match(r'^[\d.]+$', c) or n.role in ('verbalizer', 'kriyAmUla')                 or n.tam or n.rel == 'main' or POS.get(n.root) == 'v':
            continue
        if re.sub(r'_\d+$', '', c.split('-')[0]) in _NOFILL:
            continue
        cx = s.by.get(n.cx) if n.cx else None
        if cx is not None and cx.kind in ('ne', 'nc', 'compound'):
            continue                                 # names and compounds are checked as a whole
        try:
            w = (word(n) or '').lower()
        except Exception:
            w = ''
        keys = [t[:4] for t in re.findall(r'[a-z]+', w) if len(t) > 2]
        if keys and not any(k in low for k in keys):
            lost.append(n)
    return lost


def recover_missing(s, text):
    """Safety net: every USR content word must reach the output; render a lost subtree as its own chunk."""
    lost = _lost_nodes(s, text)
    if not lost:
        return text
    ids = {id(n) for n in lost}
    tops = []
    for n in lost:
        top = n
        h = s.by.get(top.head) if top.head else None
        while h is not None and id(h) in ids and h.rel != 'main' and not (h.tam or (h.rel or '').startswith('rc')):
            top = h
            h = s.by.get(top.head) if top.head else None
        # a lost construction member is shown through its construction
        if top.cx and s.by.get(top.cx) is not None and not s.by.get(top.cx).concept.startswith('[cp'):
            top = s.by.get(top.cx)
        if all(t is not top for t in tops):
            tops.append(top)
    extra = []
    tops = [t for t in tops if not (t.tam or (t.rel or '').startswith('rc') or t.kind == 'cp')]
    for t in tops:
        try:
            chunk = np(t, {}, top=False)
        except Exception:
            chunk = ''
        if chunk and chunk.lower() not in text.lower():
            extra.append('[%s]' % chunk)
    if not extra:
        return text
    m = re.search(r'\[[^\[\]]*\]_(ACTIVE|PASSIVE)\s*$', text)
    if m:
        return (text[:m.start()] + ' '.join(extra) + ' ' + text[m.start():]).strip()
    return (text + ' ' + ' '.join(extra)).strip()


def generate(s):
    if os.environ.get('USR2CHUNK_NONET'):
        return post_fix(generate_clauses(s))
    return post_fix(recover_missing(s, generate_clauses(s)))


_POST = [(r'\b(similar|equal|nearest|nearer|near|relative|opposite) of\b', r'\1 to'),   # 'pqWvI ke samAna' = 'similar to earth'
         (r'\bopposite (this|that|it)\b', r'opposite to \1'),
         (r'\b(distance|difference|ratio) among\b', r'\1 between'),          # 'sWAnoM ke bIca kI xUrI' = 'distance between places'
         (r'\[uniting\]', '[together]'),                                     # 'milakara' with a group subject = 'together'
         (r'\bcomplete way\b', 'completely'), (r'\bmorely\b', 'much'), (r'\bgoodly\b', 'well'), (r'\bonlinely\b', 'online'),
         (r'\bdifference in (\w+ and \w+)\b', r'difference between \1'),   # 'graha Ora wAre meM aMwara'
         (r'(difference\]\w* \[)in (these both|both)\]', r'\1between \2]'),
         (r'\babove from\b', 'above'),
         (r'\]_SUBJ \[((?:\w+ )?different (?:sizes|types|kinds|shapes)[^\]]*)\]', r']_SUBJ [of \1]'),   # 'viBinna prakAra ke' = 'of different types'
         (r'\[(\w+est)( to [^\]]+)?\] \[(\w+)\](?= \[(?:is|are|was|were)\b)', r'[\1 \3\2]'),   # 'sabase najaxIka wArA' = 'nearest star' (r'\bamong which\b', 'between which'),
         (r'\b(degrees (?:east|west|north|south)) from\b', r'\1 of'),          # '15 aMSa pUrva' = '15 degrees east of'
         (r'\[in (\d+ degrees)\]', r'[at \1]'), (r'\btoday night\b', 'tonight'), (r'\[at late night\]', '[late at night]'),
         (r'\bbecause of its as a result\b', 'as a result of this'),          # 'isake pariNAmasvarUpa'
         (r'^\[such\]_SUBJ \[', '[it]_SUBJ [so] ['),                         # 'EsA lagawA hE' = 'it seems so'
         (r'(\[so [^\]]+\]) \[so much\]', r'\1'),                             # 'iwanA badZA' has one 'so' (r'\[also ever\]', '[ever]'),
         (r'\b(information|knowledge) of about\b', r'\1 about'), (r'\bin relation of\b', 'in relation to'), (r'\bof around\b', 'around'),
         (r'\bbecause of whose reason\b', 'because of which'),                 # 'jisa kAraNa se' = 'because of which'
         (r'\[them\]_SUBJ', '[they]_SUBJ'), (r'\[him\]_SUBJ', '[he]_SUBJ'), (r'\[us\]_SUBJ', '[we]_SUBJ'),
         (r'(^|\[|\bof )(lakh|crore) (?=[a-z])', r'\1\2s of '),              # 'lAKoM wAre' = 'lakhs of stars'
         (r'\btheir some\b', 'some of them'), (r'\bwhose some\b', 'some of which')]


def post_fix(t):
    """Surface repairs that need the finished English: governed 'to', quantifier partitives, plural agreement with 'some'."""
    for a, b in _POST:
        t = re.sub(a, b, t)
    m = re.match(r'(.*?\[some(?: of (?:them|which))?\]_SUBJ.*\[(?:\w+ )?)(is|seems|has)\b(.*)$', t)
    if re.search(r'\bnot\b', t):
        t = t.replace('[from some]', '[from anyone]')   # 'kisI se nahIM' = 'not from anyone'
    m2 = re.match(r'(.*?\[much [^\]]*\]_SUBJ.*\[)are\b(.*)$', t)
    if m2:
        t = m2.group(1) + 'is' + m2.group(2)       # 'bahuwa sI jAnakArI' = 'much information is'
    if m and not re.search(r'\]_SUBJ.*\]_SUBJ', t):
        t = m.group(1) + {'is': 'are', 'seems': 'seem', 'has': 'have'}[m.group(2)] + m.group(3)   # 'kuCa XuMXale hEM' = 'some are dim'
    return t


def generate_clauses(s):
    v = s.main
    if v is None:
        return ''
    rc = next((n for n in s.nodes if n is not v and n.rel in ('rcsamAnaakAla', 'rcelab') and is_verbal(n)), None)
    if rc is not None and not getattr(s, '_in_rc', False):
        # 'X hE jo Y hE': the head clause is a finite verb tied to the relative pronoun; render it first
        host = s.by.get(rc.head)
        if host is not None and rc in host.kids:
            host.kids.remove(rc)
        s.main, s._in_rc = rc, True
        try:
            first = generate_clauses(s)
            s.main, s._in_rc = v, False
            rest = generate_main(s)              # the relative clause stays detached while the main clause is built
        finally:
            s.main, s._in_rc = v, False
            if host is not None:
                host.kids.append(rc)
        first = re.sub(r'_(ACTIVE|PASSIVE)$', '', first)   # one voice tag per sentence, on the final verb
        return (first + ' ' + rest).strip()
    return generate_main(s)


def generate_main(s):
    v = s.main
    if v is None:
        return ''
    passive = s.stype.startswith('pass') or (tam_is_passive(tam_of(v)) and not any(k.rel == 'k1' for k in v.kids))
    deps = [k for k in v.kids]
    # clause-level dependents also come from the cp's kriyAmUla and from a k1s predicate
    for m in v.members:
        deps += [k for k in m.kids]
    dist = next((k for k in deps if k.rel in ('k7p', 'k7', 'mod', 'krvn') and not k.concept.startswith('[')
                 and word(k) in ('distance', 'away')), None)
    if dist is not None:
        for k5 in [k for k in deps if k.rel == 'k5']:
            deps.remove(k5)
            dist.kids.append(k5)
            dist.kids.sort(key=lambda x: x.first_pos())
    voc = [k for k in s.nodes if k.rel == 'rad']
    for x in voc:
        if x in deps:
            deps.remove(x)
    pk1 = next((k for k in deps if k.rel in ('pk1', 'jk1')), None)
    k1 = next((k for k in deps if k.rel == 'k1'), None)
    k2 = next((k for k in deps if k.rel == 'k2'), None)
    if k1 is None and pk1 is None:
        for c in [k for k in deps if k.rel in ('rpk', 'rsk')]:
            sub = next((x for x in c.kids + [y for m in c.members for y in m.kids] if x.rel == 'k1'), None)
            if sub is not None:                      # Hindi kar-participle shares the main verb's subject
                (sub_parent := (c if sub in c.kids else next(m for m in c.members if sub in m.kids))).kids.remove(sub)
                sub.rel = 'k1'
                deps.append(sub)
                k1 = sub
                break
    if k1 is None and pk1 is None and k2 is not None and not passive and 'interrogative' not in s.stype \
            and 'imperative' not in s.stype and tam_of(v) not in ('e_1', 'e_2') \
            and (morph.base_verb(verb_lemma(v).split()[0]) in LISTS.get('impersonal_verbs', set())
                 or tam_of(v) in LISTS.get('obligation_tams', set())):    # obligation with no subject: 'X kA AnaMxa lenA ho' = 'X has to be enjoyed'
        passive = True                               # generic subject: 'ise ... kahte hEM' = 'this is called ...'
        s.voice_override = 'passive'
    if k1 is None and pk1 is None and k2 is not None and not passive and v.kind != 'cp' and \
            verb_lemma(v).split()[0] in ('known', 'called', 'named', 'considered', 'regarded', 'situated', 'located'):
        passive = True                               # dictionary gives a participle: 'X jAnA jAwA hE' = 'X is known'
    if k1 is None and pk1 is None and k2 is not None and not passive and \
            verb_lemma(v).split()[0] in ('become', 'be', 'remain', 'seem', 'appear', 'look'):
        k1, k2 = k2, None                            # 'X dekhte hi banta hai': the k2 is the grammatical subject
        k1.rel = 'k1'
    # possession: 'X ko Y hai' (k4 + copula) = 'X has Y'
    k4p = next((k for k in deps if k.rel in ('k4', 'k4a')), None)
    if k4p is not None and k1 is not None and v.root.split('_')[0] in ('hE', 'WA') and not passive \
            and not any(k.rel == 'k1s' for k in deps):
        k1.rel, k4p.rel = 'k2', 'k1'
        k1, k2 = k4p, k1
        ctx_possession = True
    else:
        ctx_possession = False
    # dative-subject verbs (X ko Y milnA = X gets Y): the experiencer k4/k4a is the English subject
    k4 = next((k for k in deps if k.rel in ('k4', 'k4a')), None)
    if k4 is not None and k1 is not None and pk1 is None and not passive and             verb_lemma(v).split()[0] in LISTS.get('dative_subject_verbs', set()):
        k1.rel, k4.rel = 'k2', 'k1'
        k1, k2 = k4, k1
    causative_passive = pk1 is not None and k2 is not None and (passive or tam_is_passive(tam_of(v)))
    if causative_passive:                     # 'X dvArA Y banavAyA gayA' = 'Y had been got built by X'
        subj, agent = k2, pk1
        passive = True
    elif pk1 is not None:                     # causative: causer is subject, causee 'by X', verb 'get V-ed'
        subj, agent = pk1, k1
    else:
        subj = k2 if (passive and k2 is not None) else k1
        agent = k1 if (passive and k2 is not None) else None
    # experiencer + 'ho' complex predicate: 'relave ko 8 biliyana kA PAyaxA howA hE' = 'relave gets advantage of 8 billion'
    lemma_override, extra_obj = None, None
    k4x = next((k for k in deps if k.rel in ('k4', 'k4a')), None)
    if v.kind == 'cp' and k4x is not None and not passive and pk1 is None:
        km = next((m for m in v.members if m.role == 'kriyAmUla'), None)
        vb = next((m for m in v.members if m.role == 'verbalizer'), None)
        if km is not None and vb is not None and vb.root.split('_')[0] == 'ho' and POS.get(km.root, 'n') == 'n':
            own_verb = verb_lemma(v) != '%s %s' % (LIGHT.get('ho', 'do'), word(km))
            if own_verb:                      # dictionary verb for the cp: 'unheM smaraNa huA' = 'they remembered'
                if k1 is not None:
                    k1.rel = 'k2'
            else:                             # no verb of its own: 'X ko PAyaxA howA hE' = 'X gets advantage'
                lemma_override = 'get'
                extra_obj = word(km) + ((' of ' + np(k1, {})) if k1 is not None else '')
                if k1 is not None:
                    deps.remove(k1)
            k4x.rel = 'k1'
            subj, agent = k4x, None
    ctx = {'passive_agent': agent, 'causative': pk1 is not None, 'possession': ctx_possession,
           'causative_passive': causative_passive, 'lemma_override': lemma_override,
           'question': 'interrogative' in s.stype or any(x.root.startswith('$kim') for x in s.nodes)}
    if subj is not None:
        ctx['subj_plural'] = is_plural(subj) or \
                             (subj.root.startswith('$') and 'pl' in (subj.gnp or '')) or \
                             (subj.kind == 'conj' and len(subj.members) > 1) or \
                             subj.root.startswith('$addressee')               # 'you want', 'you are'
        if subj.kind == 'disjunct' and subj.members:
            last = sorted(subj.members, key=lambda m: _op_no(m.role))[-1]
            ctx['subj_plural'] = is_plural(last)     # 'X or Y is'
        ctx['subj_person1'] = subj.root.startswith('$speaker')
        head_txt = np(subj, ctx).lower().split(' of ')[0].split()
        hw = head_txt[-1] if head_txt else ''
        if subj.kind == 'ne':
            hw = construction_text(subj, ctx).lower().split()[-1] if construction_text(subj, ctx) else hw
        elif not subj.concept.startswith(('[', '$')) and not is_name(subj):
            hw = head_word(subj).lower().split()[-1] if head_word(subj) else hw   # 'train running by two engines'
        if subj.kind == 'cp' or 'kqw' in (subj.gnp or ''):
            hw = ''                                  # a verbal-noun subject is singular: 'spending a day with students gives'
        if hw in ALREADY_PLURAL - {'etc', 'others', 'these', 'those'} or (
                hw.endswith('s') and morph.analyse(hw) and all(x.startswith('<n><pl>') for x in morph.analyse(hw))):
            ctx['subj_plural'] = True            # lexically plural (people, children)
    pred = [k for k in deps if k.rel in ('k1s', 'k2s')]
    name3 = next((k for k in deps if k.rel == 'k3' and word(k) == 'name' and not any(kk.rel == 'r6' for kk in k.kids)), None)
    named = next((k for k in pred if k.rel == 'k2s'), None)
    if name3 is not None and named is not None:
        named.rel = 'r6'                      # 'by name of X'
        named.head = name3.idx
        name3.kids.append(named)
        pred.remove(named)
        deps = [d for d in deps if d is not named]
    promoted = []
    for p in pred:   # a predicate keeps its dependents; distance phrases surface as their own chunks
        has_dist = any(not kk.concept.startswith('[') and word(kk) in ('distance', 'away') or kk.kind == 'dist'
                       for kk in p.kids)
        for kk in list(p.kids):
            if 'wawCIlAxi' in (p.gnp or '') and kk.rel == 'k2':
                continue                             # an agent noun keeps its object ('provider of moksha')
            if (kk.rel in VERBAL_DEP and kk.rel != 'rn') or (kk.rel == 'mod' and not kk.concept.startswith('[') and word(kk) in PREP_HEADS):
                promoted.append(kk)
                p.kids.remove(kk)
    if subj is not None and not subj.concept.startswith('$'):
        for kk in list(subj.kids):
            # Hindi genitive normally precedes its noun; one that FOLLOWS it in a copula clause is predicative
            subj_end = max([m.pos for m in subj.members] or [subj.pos]) if subj.concept.startswith('[') else subj.pos
            predicative_r6 = kk.rel == 'r6' and kk.first_pos() > subj_end and subj.kind in ('', 'ne') \
                and not any(x.rel in ('k1s', 'k2s') for x in deps)
            if kk.rel == 'rask1':                    # 'X ke sAWa Y' (associative) = '[Y]_SUBJ [along with X]'
                subj.kids.remove(kk)
                kk.head = v.idx
                deps.append(kk)
                continue
            if kk.rel == 'ru' or predicative_r6:
                subj.kids.remove(kk)
                kk.head = v.idx
                kk.rel = 'r6pred' if kk.rel == 'r6' else kk.rel
                deps.append(kk)
    # a pronoun cannot take a genitive: an r6 on a personal/demonstrative pronoun argument is predicative
    # ('ise 7vIM SawAbxI kA niSciwa kiyA gayA' = 'this ... of 7th century AD has been determined')
    for a in [x for x in deps if x.rel in ('k1', 'k2') and re.sub(r'_\d+$', '', x.root) in ('$wyax', '$speaker', '$addressee')]:
        for kk in [y for y in a.kids if y.rel == 'r6' and not y.root.startswith('$')]:
            a.kids.remove(kk)
            kk.head, kk.rel = v.idx, 'r6pred'
            deps.append(kk)
    chunks = []   # (sortkey, text, tag, is_frame)
    sp = subj.first_pos() if subj is not None else 10 ** 6
    # frequency: 'sAla meM eka bAra' = 'once a year' -- a bare time unit joins the frequency adverb
    units = {'year': 'a year', 'month': 'a month', 'week': 'a week', 'day': 'a day'}
    freq = [k for k in deps if k.rel in ('k7t', 'krvn') and re.search(r'(once|twice|times)', np(k, ctx))]
    freq = [k for k in deps if k.rel in ('k7t', 'krvn') and set(np(k, ctx).split()) & {'once', 'twice', 'times'}]
    for u in [k for k in deps if k.rel == 'k7t' and not k.kids and not k.concept.startswith(('[', '$'))
              and word(k) in units]:
        if freq:
            SUFFIX[id(freq[0])] = ' ' + units[word(u)]
            deps.remove(u)
    comparative = any(re.search(r'comp[ae]?rmore', x.gnp or '') for x in s.nodes)
    # standard of comparison: a 'se' (k5) phrase joins the comparative word as 'than X'
    if verb_lemma(v).split()[0] not in LISTS.get('motion_verbs', set()):
        def synthetic_comp(x):
            w = head_word(x) if not x.concept.startswith(('[', '$')) else ''
            if not w or ' ' in w or w in ('clear', 'evident', 'obvious', 'known', 'different', 'free', 'separate', 'safe'):
                return False                     # 'ciwra se spaRta' = 'clear from figure' (source, not comparison)
            c = morph.adj(w, 'comp')
            return bool(c) and not c.startswith('more ') and c != w
        comp = next((x for x in deps if x.rel != 'k5' and not x.concept.startswith('$') and (
            re.search(r'comp[ae]?rmore', x.gnp or '') or (not x.concept.startswith('[') and word(x) in ('more', 'less'))
            or (x.rel in ('k1s', 'k2s') and v.root.split('_')[0] in ('hE', 'WA') and POS.get(x.root) in ('a', 'x', None)
                and synthetic_comp(x)))), None)   # copula only: 'janma se aMXI' is not a comparison
        std = [x for x in deps if x.rel == 'k5' and not re.search(r'comp[ae]?rmore', x.gnp or '')]
        if comp is not None and len(std) == 1:
            x = std[0]
            deps.remove(x)
            if comp.rel in ('k1s', 'k2s') and not re.search(r'comp[ae]?rmore', comp.gnp or ''):
                comp.gnp = (comp.gnp if comp.gnp not in (None, '-') else '') + 'compermore'
            if comp in pred:
                pred.remove(comp)               # 'lower than X' is one chunk before the verb (comp is already in deps)
            SUFFIX[id(comp)] = ' than ' + (pronoun(x, 'obj').replace('it', 'that') if x.root.startswith('$') else np(x, ctx))
            comparative = True
    for k in deps + promoted:
        if k in pred or k.rel in ('neg', 'main'):
            continue
        if k is agent:
            t = 'by ' + np(k, ctx)
        else:
            t = chunk_text(k, ctx)
        if not t:
            continue
        t += SUFFIX.get(id(k), '')
        if comparative and k.rel == 'k7t' and t in ('before', 'earlier'):
            t = 'than ' + t                          # comparison with an earlier time: 'than before'
        if k is subj:
            chunks.append(((1, 0), t, '_SUBJ'))
            continue
        frame = (re.sub(r'_\d+$', '', k.root) in ('$yax', '$kim') and k is not subj)             or (k.rel == 'krvn' and any(x.rel == 'mod' and x.root.startswith('$kim') for x in k.kids)) \
            or (k.rel in ('rh', 'k3', 'k7', 'k7p', 'k5') and k is not subj and
                any(x.rel in ('r6', 'mod') and re.sub(r'_\d+$', '', x.root) == '$yax' for x in k.kids)) \
            or (k.rel == 'krvn' and t in LISTS.get('sentence_adverbs', set())) or k.rel == 'vkvn'   # '[in fact] [X]_SUBJ ...'
        single_adverb = k.rel == 'krvn' and not k.kids and not k.concept.startswith(('[', '$')) and len(t.split()) == 1
        chunks.append(((0, k.first_pos()) if frame else (2.9 if single_adverb else 2, k.first_pos()), t, ''))
    if extra_obj:
        chunks.append(((2.95, 10 ** 5), extra_obj, ''))   # 'advantage of almost 8 billion' right before 'gets'
    for p in pred:
        t = np(p, ctx)
        vwords = [morph.base_verb(w) for w in verb_lemma(v).split()]
        as_verb = not any(w in LISTS.get('no_as_verbs', set()) for w in vwords)   # make/define: bare complement
        participial = len(t.split()) == 1 and (POS.get(p.root) == 'v' or
                                               any(x.startswith('<vblex><pp>') for x in morph.analyse(t)))
        if p.rel == 'k2s' and not t.startswith('as ') and as_verb and not participial:   # 'is supposed built'
            lead = re.match(r'^((?:also|only|even)\s+)+', t)
            t = (lead.group(0) + 'as ' + t[lead.end():]) if lead else 'as ' + t
        chunks.append(((3, p.first_pos()), t, ''))
    chunks.sort(key=lambda c: c[0])
    conn = ['[oh %s]' % np(x, ctx) for x in voc]
    if v.disc and ':' in v.disc:
        d = DISCOURSE.get(v.disc.split(':', 1)[1], '')
        if d and d != '-':
            conn.append('[%s]' % d)
        elif v.disc.endswith(':AvaSyakawApariNAma') and not _has_relative(s):
            conn.append('[if]')                      # condition clause 'yaxi ... cAhe' = 'if ...'
    if any(x.disc and x.disc.startswith(s.sid + '.') and x.disc.endswith(':AvaSyakawApariNAma') and not _has_relative(o)
           for o in ALL_SENTS.values() if o is not s for x in o.nodes):
        conn.insert(0, '[then]')                     # result clause 'wo ...' = 'then ...'
    ctx['imperative'] = (tam_of(v) in ('e_1', 'e_2') or tam_of(v).endswith('_e_1')) and (bool(voc) or subj is None) and not ctx.get('question')
    ctx['no_subject'] = subj is None
    vg = verb_group(s, ctx)
    if (passive or ctx.get('impersonal')) and subj is None and not any(t == '_SUBJ' for _, _, t in chunks) \
            and not ctx.get('imperative') and not ctx.get('question') \
            and verb_lemma(v).split()[0] in LISTS.get('impersonal_verbs', set()):
        vg = 'it ' + vg               # impersonal passive: 'it is said'
    tag = '_PASSIVE' if s.stype.startswith('pass') else '_ACTIVE'
    chunks = [(a_, 'a little' if t_.strip() == 'little' else t_, g_) for a_, t_, g_ in chunks]   # 'WodZA sA' = 'a little'
    if subj is not None and subj.root.startswith('$speaker') and 'pl' in (subj.gnp or '') and tam_of(v) in ('e_1', 'e_2') \
            and not ctx.get('question'):
        chunks = [c_ for c_ in chunks if c_[2] != '_SUBJ']
        vg = 'let us ' + verb_lemma(v)               # 'Aie jAnawe hEM / jAneM' = 'let us know'
    if ctx.get('question') and subj is None and tam_of(v) in ('e_1', 'e_2', 'nA_cAhie_1') and \
            any(k.root.startswith('$kim') and k.rel == 'k2' for k in v.kids) and not ctx.get('imperative'):
        vg = 'should be ' + morph.verb(verb_lemma(v).split()[0], 'pp')   # 'kyA kareM' = 'what should be done'
    out = conn + ['[%s]%s' % (re.sub(r'\s+', ' ', t).strip(), tag_) for _, t, tag_ in chunks]
    out.append('[%s]%s' % (vg, tag))
    return pair_distances(' '.join(out))


_DIST = r'(?:[\w.]+ )*?(?:kilometres?|metres?|km)'


def pair_distances(text):
    """'[28 kilometres and 46 kilometres away from A and B]' = '[28 kilometres away from A and 46 kilometres away from B]'."""
    text = re.sub(r'\[from ([^\]]+?) and ([^\]]+?)\] \[(%s) and (%s)( away)?\]' % (_DIST, _DIST),
                  lambda m: '[%s from %s and %s from %s]' % ((m.group(3) + (m.group(5) or ''), m.group(1), m.group(4) + (m.group(5) or ''), m.group(2))), text)
    text = re.sub(r'\[(at distance of )?(%s) and (%s) from ([^\]]+?) from ([^\]]+?)\]' % (_DIST, _DIST),
                  lambda m: '[%s%s from %s and %s from %s]' % (m.group(1) or '', m.group(2), m.group(4), m.group(3), m.group(5)), text)
    def _pair(m):
        a, b = re.sub(r'^at ', '', m.group(2)), m.group(3)
        if m.group(1) or m.group(4) == ' distance' or m.group(2).startswith('at '):
            return '[at distance of %s from %s and %s from %s]' % (a, m.group(5), b, m.group(6))
        if m.group(4) == ' away':
            return '[%s away from %s and %s away from %s]' % (a, m.group(5), b, m.group(6))
        return '[%s from %s and %s from %s]' % (a, m.group(5), b, m.group(6))
    return re.sub(r'\[(at distance of )?(%s) and (%s)( away| distance)? from ([^\]]+?) and ([^\]]+?)\]' % (_DIST, _DIST),
                  _pair, text)


def _has_relative(s):
    """A clause with a relative/correlative pronoun ('jo', 'jaba') is not a plain 'if' condition."""
    return any(re.sub(r'_\d+$', '', x.root) in ('$yax', '$kim') for x in s.nodes)


def main(argv):
    usr_path = argv[1]
    load_dict()
    sents = read_usrs(usr_path)
    ALL_SENTS.update({x.sid: x for x in sents})
    for s in sents:
        try:
            print('%s: %s' % (s.sid, generate(s)))
        except Exception as e:   # never lose a sentence silently
            print('%s: [ERROR %s]' % (s.sid, type(e).__name__))


if __name__ == '__main__':
    main(sys.argv)
