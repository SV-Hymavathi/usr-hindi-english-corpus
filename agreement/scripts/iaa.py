"""Inter-annotator agreement for two USR annotations of the same sentences.
Nodes are aligned within each sentence by (concept root, order of occurrence); a node with no partner counts as a
disagreement for every field. Heads are compared through the alignment (A's head maps to B's head)."""
import re, collections, sys, os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

HERE = os.path.dirname(os.path.abspath(__file__))
A_F = os.path.join(HERE, '..', 'Annotator 1 tourism .xlsx')
B_F = os.path.join(HERE, '..', sys.argv[1] if len(sys.argv) > 1 else 'Annotator 2 tourism (1).xlsx')
OUT = os.path.join(HERE, '..', 'IAA_tourism_250_independent.xlsx')


def sid_of(v):
    return str(int(v)) if isinstance(v, float) else str(v).strip()


def parse(usr):
    nodes, stype = [], ''
    for line in str(usr or '').splitlines():
        line = line.strip().strip('"').strip()
        if not line or line.startswith(('<', '#')):
            continue
        if line.startswith('%'):
            stype = line
            continue
        c = line.split()
        if len(c) < 9 or not re.fullmatch(r'\d+', c[1]):
            continue
        concept = c[0]
        tam = ''
        if '-' in concept and not concept.startswith('['):
            m = re.match(r'^(.*?_\d+)-(.+)$', concept)
            if m:
                concept, tam = m.group(1), m.group(2)
        root = re.sub(r'_\d+$', '', concept)
        root = re.sub(r'_\d+$', '', root) if root.startswith('[') else root
        head, rel = (c[4].split(':', 1) + [''])[:2] if ':' in c[4] else ('-', '-')
        cx_head, cx_role = (c[8].split(':', 1) + [''])[:2] if ':' in c[8] else ('-', c[8])
        disc = c[5]
        disc_rel = disc.split(':', 1)[1] if ':' in disc else disc
        nodes.append(dict(idx=c[1], concept=concept, root=root, tam=tam, sem=c[2], gnp=c[3], head=head, rel=rel,
                          disc=disc_rel, spk=c[6], scope=c[7], cxh=cx_head, cxr=cx_role))
    return nodes, stype


def load(path):
    ws = openpyxl.load_workbook(path).active
    d = {}
    for r in list(ws.iter_rows(values_only=True))[1:]:
        if r[4] is None and r[2] is None:
            continue
        m = re.search(r'<sent_id=\s*([^>\s]+)\s*>', str(r[4] or ''))
        sid = m.group(1) if m else (sid_of(r[2]) if r[2] is not None else None)    # trust the id written inside the USR
        if sid is None or not r[4]:
            continue
        hin = re.search(r'#\s*([^\n]+)', str(r[4]))
        d[sid] = (hin.group(1).strip() if hin else r[3], parse(r[4]))
    return d


def align(na, nb):
    """pair nodes with the same root, in order; constructions ([ne_1] ...) by type and order"""
    key = lambda n: re.sub(r'_\d+\]$', ']', n['root']) if n['root'].startswith('[') else n['root']
    pool = collections.defaultdict(list)
    for n in nb:
        pool[key(n)].append(n)
    pairs, ua = [], []
    for n in na:
        if pool[key(n)]:
            pairs.append((n, pool[key(n)].pop(0)))
        else:
            ua.append(n)
    ub = [n for v in pool.values() for n in v]
    return pairs, ua, ub


def kappa(x, y):
    n = len(x)
    if not n:
        return float('nan')
    po = sum(a == b for a, b in zip(x, y)) / n
    ca, cb = collections.Counter(x), collections.Counter(y)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


A, B = load(A_F), load(B_F)
ids = [i for i in A if i in B]
FIELDS = ['concept (root+sense)', 'sense (same root)', 'TAM', 'semantic category', 'GNP', 'head (UAS)',
          'head+relation (LAS)', 'relation (head agrees)', 'discourse relation', 'speaker view', 'scope',
          'construction membership']
pairs_all = collections.defaultdict(list)            # field -> list of (a, b) labels over aligned nodes
tot_a = tot_b = matched = 0
sent_rows, stype_pairs, rel_conf = [], [], collections.Counter()
exact_sent = 0
for i in ids:
    hin, (na, sa) = A[i]
    _, (nb, sb) = B[i]
    tot_a += len(na); tot_b += len(nb)
    pairs, ua, ub = align(na, nb)
    matched += len(pairs)
    amap = {a['idx']: b['idx'] for a, b in pairs}
    sent_dis = []
    for a, b in pairs:
        f = {}
        f['concept (root+sense)'] = (a['concept'], b['concept'])
        if not a['root'].startswith('['):
            f['sense (same root)'] = (a['concept'], b['concept'])
        if a['tam'] or b['tam']:
            f['TAM'] = (a['tam'] or '-', b['tam'] or '-')
        f['semantic category'] = (a['sem'], b['sem'])
        f['GNP'] = (a['gnp'], b['gnp'])
        hb = amap.get(a['head'], '?' + a['head']) if a['head'] not in ('0', '-') else a['head']
        f['head (UAS)'] = (hb, b['head'])
        f['head+relation (LAS)'] = (hb + ':' + a['rel'], b['head'] + ':' + b['rel'])
        if hb == b['head']:
            f['relation (head agrees)'] = (a['rel'], b['rel'])
            if a['rel'] != b['rel']:
                rel_conf[(a['rel'], b['rel'])] += 1
        f['discourse relation'] = (a['disc'], b['disc'])
        f['speaker view'] = (a['spk'], b['spk'])
        f['scope'] = (a['scope'], b['scope'])
        ch = amap.get(a['cxh'], '?' + a['cxh']) if a['cxh'] != '-' else '-'
        f['construction membership'] = (ch + ':' + a['cxr'], b['cxh'] + ':' + b['cxr'])
        for k, v in f.items():
            pairs_all[k].append(v)
            if v[0] != v[1]:
                sent_dis.append('%s %s: %s | %s' % (a['concept'], k, v[0], v[1]))
    for n in ua:
        sent_dis.append('only annotator 1: %s' % n['concept'])
    for n in ub:
        sent_dis.append('only annotator 2: %s' % n['concept'])
    stype_pairs.append((sa, sb))
    if sa != sb:
        sent_dis.append('sentence type: %s | %s' % (sa, sb))
    ok = not sent_dis
    exact_sent += ok
    sent_rows.append([i, hin, len(na), len(nb), len(pairs), 'yes' if ok else 'no', len(sent_dis), '\n'.join(sent_dis)])

# ---- workbook
wb = openpyxl.Workbook()
ws = wb.active; ws.title = 'Summary'
HDR = PatternFill('solid', fgColor='305496')
ws.append(['Inter-annotator agreement: tourism USRs (two annotators)']); ws['A1'].font = Font(bold=True, size=14)
ws.append([])
ws.append(['Sentences compared', len(ids)])
ws.append(['Nodes: annotator 1 / annotator 2', '%d / %d' % (tot_a, tot_b)])
ws.append(['Aligned node pairs (same concept root)', matched])
p, r = matched / tot_a, matched / tot_b
ws.append(['Node alignment F1 (concept-root level)', round(2 * p * r / (p + r), 4)])
ws.append(['Sentences with identical USR', exact_sent, '%.1f%%' % (100.0 * exact_sent / len(ids))])
ws.append(['Sentence type (%affirmative, %pass_...) agreement',
           '%.1f%%' % (100.0 * sum(a == b for a, b in stype_pairs) / len(stype_pairs)),
           'kappa %.3f' % kappa([a for a, _ in stype_pairs], [b for _, b in stype_pairs])])
ws.append([])
ws.append(['Field (over aligned nodes)', 'Items', 'Observed agreement', "Cohen's kappa"])
for c in ws[ws.max_row]:
    c.font = Font(bold=True, color='FFFFFF'); c.fill = HDR
for k in FIELDS:
    v = pairs_all[k]
    if not v:
        continue
    ws.append([k, len(v), '%.1f%%' % (100.0 * sum(a == b for a, b in v) / len(v)), round(kappa([a for a, _ in v], [b for _, b in v]), 3)])
ws.append([])
for t in ['Alignment: nodes are paired within a sentence by concept root in order of occurrence; constructions by type.',
          'UAS/LAS: a head agrees when annotator 1\'s head, mapped through the alignment, is annotator 2\'s head.',
          '"relation (head agrees)" measures label agreement only where both chose the same head.',
          'Kappa = Cohen\'s kappa (chance-corrected); for fields with one dominant value (scope, speaker view) kappa can be low even when observed agreement is high.']:
    ws.append([t])
ws.column_dimensions['A'].width = 55
for c in 'BCD':
    ws.column_dimensions[c].width = 20

s2 = wb.create_sheet('Relation confusions')
s2.append(['Annotator 1 relation', 'Annotator 2 relation', 'Count'])
for (a, b), n in rel_conf.most_common():
    s2.append([a, b, n])
for c in s2[1]:
    c.font = Font(bold=True, color='FFFFFF'); c.fill = HDR
s3 = wb.create_sheet('Per sentence')
s3.append(['Sentence ID', 'Hindi', 'Nodes A1', 'Nodes A2', 'Aligned', 'Identical', 'Disagreements', 'Details (A1 | A2)'])
for r in sent_rows:
    s3.append(r)
for c in s3[1]:
    c.font = Font(bold=True, color='FFFFFF'); c.fill = HDR
for w, col in zip([10, 50, 9, 9, 9, 9, 12, 90], 'ABCDEFGH'):
    s3.column_dimensions[col].width = w
for row in s3.iter_rows(min_row=2):
    for c in row:
        c.alignment = Alignment(wrap_text=True, vertical='top')
wb.save(OUT)

print('sentences', len(ids), 'identical', exact_sent, 'nodes', tot_a, tot_b, 'aligned', matched)
for k in FIELDS:
    v = pairs_all[k]
    if v:
        print('%-28s %5d  %.1f%%  kappa %.3f' % (k, len(v), 100.0 * sum(a == b for a, b in v) / len(v), kappa([a for a, _ in v], [b for _, b in v])))
print('top relation confusions', rel_conf.most_common(8))
