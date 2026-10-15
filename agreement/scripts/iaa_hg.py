"""Agreement for the health + geography second annotation (LRE): annotator 2's USRs written from scratch for 100 random
sentences vs the corpus USRs. Same alignment and kappa as iaa.py (tourism). Discourse is scored separately: the sentences
were given without their neighbours, so annotator 2 could not give the head sentence/index and wrote the relation in English
(e.g. unknown_sent_id:unknown_index:result); we compare the relation label after mapping the English names to USR labels.
Cross-sentence coreference could not be annotated without context and is excluded."""
import re, collections, os, sys, json
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'iaa.py'), encoding='utf-8').read()
exec(src[src.index('def sid_of'):src.index('A, B = load(A_F)')])          # parse, align, kappa
EX = os.path.join(HERE, '..', 'usr2chunk_tool', 'usr2chunk', 'examples')
SHEET = 'second_annotation.xlsx'  # annotator 2 USRs in column D
OUT = os.path.join(HERE, '..', 'IAA_health_geography_100.xlsx')
FULL = len(sys.argv) > 1 and sys.argv[1] == 'revised'
EN2USR = {'conjunction': 'samuccaya', 'result': 'pariNAma', 'temporal': 'samAnakAla', 'contrast': 'viroXI',
          'condition': 'AvaSyakawApariNAma', 'reason': 'kAryakAraNa', 'concession': 'vyaBicAra'}


def blocks(text):
    d = {}
    for b in re.split(r'(?=<sent_id=)', text):
        m = re.match(r'<sent_id=\s*([^>\s]+)', b)
        if m: d[m.group(1)] = b
    return d


def disc_labels(block, annot):
    out = set()
    for l in block.splitlines():
        c = l.split()
        if len(c) < 9 or l.lstrip().startswith(('#', '<', '%')) or c[5] == '-': continue
        for part in c[5].split(','):
            lab = part.split(':')[-1]
            if lab == 'coref' and not FULL: continue
            out.add(EN2USR.get(lab, lab + ('?' if annot else '')) if not FULL else part)
    return out


G = {}
for f in ('health_402', 'geography_558'):
    G.update(blocks(open(os.path.join(EX, f + '.txt'), encoding='utf-8').read()))
REV = len(sys.argv) > 1 and sys.argv[1] == 'revised'
if REV:
    SHEET = SHEET.replace('A_second_annotation_health50_geography50.xlsx', 'A2_revision_with_english_reference.xlsx')
    OUT = OUT.replace('.xlsx', '_final.xlsx')
ws = openpyxl.load_workbook(SHEET)['Revise'] if REV else openpyxl.load_workbook(SHEET).active
COL = 6 if REV else 3
B = {}; dom = {}; asked = []
for r in list(ws.iter_rows(values_only=True))[1:]:
    if not r[0]: continue
    asked.append(r[0])
    for sid, b in blocks(str(r[COL] or '')).items():
        B[sid] = b; dom[sid] = r[1]
# segmentation: the sheet asked for one sentence; did annotator 2 split it the same way as the corpus?
seg_same = 0; seg_rows = []
for a in asked:
    mine = sorted(s for s in B if re.sub(r'[a-z]$', '', s) == re.sub(r'[a-z]$', '', a))
    if a in B: seg_same += 1
    else: seg_rows.append((a, mine))
ids = [s for s in B if s in G]
FIELDS = ['concept (root+sense)', 'sense (same root)', 'TAM', 'semantic category', 'GNP', 'head (UAS)',
          'head+relation (LAS)', 'relation (head agrees)', 'speaker view', 'scope', 'construction membership']
res = {}
for D in ('health', 'geography', 'all'):
    pa = collections.defaultdict(list); ta = tb = mt = ident = 0; st = []; conf = collections.Counter(); rows = []
    disc = []
    for i in ids:
        if D != 'all' and dom[i] != D: continue
        na, sa = parse(G[i]); nb, sb = parse(B[i])
        ta += len(na); tb += len(nb)
        pairs, ua, ub = align(na, nb); mt += len(pairs)
        amap = {a['idx']: b['idx'] for a, b in pairs}; dis = []
        for a, b in pairs:
            f = {'concept (root+sense)': (a['concept'], b['concept'])}
            if not a['root'].startswith('['): f['sense (same root)'] = (a['concept'], b['concept'])
            if a['tam'] or b['tam']: f['TAM'] = (a['tam'] or '-', b['tam'] or '-')
            f['semantic category'] = (a['sem'], b['sem']); f['GNP'] = (a['gnp'], b['gnp'])
            hb = amap.get(a['head'], '?' + a['head']) if a['head'] not in ('0', '-') else a['head']
            f['head (UAS)'] = (hb, b['head']); f['head+relation (LAS)'] = (hb + ':' + a['rel'], b['head'] + ':' + b['rel'])
            if hb == b['head']:
                f['relation (head agrees)'] = (a['rel'], b['rel'])
                if a['rel'] != b['rel']: conf[(a['rel'], b['rel'])] += 1
            f['speaker view'] = (a['spk'], b['spk']); f['scope'] = (a['scope'], b['scope'])
            ch = amap.get(a['cxh'], '?' + a['cxh']) if a['cxh'] != '-' else '-'
            f['construction membership'] = (ch + ':' + a['cxr'], b['cxh'] + ':' + b['cxr'])
            for k, v in f.items():
                pa[k].append(v)
                if v[0] != v[1]: dis.append('%s %s: %s | %s' % (a['concept'], k, v[0], v[1]))
        dis += ['only corpus: %s' % n['concept'] for n in ua] + ['only annotator 2: %s' % n['concept'] for n in ub]
        st.append((sa, sb))
        if sa != sb: dis.append('sentence type: %s | %s' % (sa, sb))
        dg, da = disc_labels(G[i], False), disc_labels(B[i], True)
        if dg or da:
            disc.append((i, ' '.join(sorted(dg)) or '-', ' '.join(sorted(da)) or '-'))
            if dg != da: dis.append('discourse: %s | %s' % (' '.join(sorted(dg)) or '-', ' '.join(sorted(da)) or '-'))
        ident += not [d for d in dis if not d.startswith('discourse')]
        rows.append([i, dom[i], len(na), len(nb), len(pairs), len(dis), '\n'.join(dis)])
    p, r = mt / ta, mt / tb
    res[D] = dict(n=len(rows), nodes=(ta, tb), aligned=mt, align_f1=2 * p * r / (p + r), identical=ident,
                  stype=(sum(a == b for a, b in st) / len(st), kappa([a for a, _ in st], [b for _, b in st])),
                  fields={k: (len(v), sum(a == b for a, b in v) / len(v), kappa([a for a, _ in v], [b for _, b in v])) for k, v in pa.items()},
                  disc=disc, conf=conf.most_common(8), rows=rows)

wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Summary'
ws.append(['Agreement: second annotator (from scratch) vs corpus USRs, 50 health + 50 geography sentences'])
ws.append(['Segmentation: annotator 2 kept the corpus segmentation for %d of %d sentences' % (seg_same, len(asked))])
ws.append([])
ws.append(['Field', 'health items', 'health obs.', 'health kappa', 'geography items', 'geography obs.', 'geography kappa', 'all items', 'all obs.', 'all kappa'])
for k in FIELDS:
    row = [k]
    for D in ('health', 'geography', 'all'):
        v = res[D]['fields'].get(k)
        row += [v[0], round(v[1], 3), round(v[2], 3)] if v else ['', '', '']
    ws.append(row)
ws.append(['sentence type'] + sum([['', round(res[D]['stype'][0], 3), round(res[D]['stype'][1], 3)] for D in ('health', 'geography', 'all')], []))
ws.append(['USRs compared'] + sum([[res[D]['n'], '', ''] for D in ('health', 'geography', 'all')], []))
ws.append(['node alignment F1'] + sum([['', round(res[D]['align_f1'], 3), ''] for D in ('health', 'geography', 'all')], []))
ws.append(['identical USRs (discourse excluded)'] + sum([[res[D]['identical'], '', ''] for D in ('health', 'geography', 'all')], []))
s = wb.create_sheet('Discourse'); s.append(['Sentence', 'Corpus label(s)', 'Annotator 2 label(s), English mapped to USR'])
for x in res['all']['disc']: s.append(list(x))
s = wb.create_sheet('Per sentence'); s.append(['ID', 'Domain', 'Nodes corpus', 'Nodes A2', 'Aligned', 'Disagreements', 'Details (corpus | annotator 2)'])
for r in res['all']['rows']: s.append(r)
wb.save(OUT)
for D in ('health', 'geography', 'all'):
    x = res[D]; print('==', D, 'USRs', x['n'], 'nodes', x['nodes'], 'aligned', x['aligned'], 'alignF1 %.3f' % x['align_f1'],
                     'identical', x['identical'], 'stype %.3f k %.3f' % x['stype'])
    for k in FIELDS:
        if k in x['fields']: print('   %-26s %4d  %.1f%%  k %.3f' % (k, x['fields'][k][0], 100 * x['fields'][k][1], x['fields'][k][2]))
    print('   confusions', x['conf'])
print('segmentation same', seg_same, 'of', len(asked), seg_rows)
d = res['all']['disc']; print('discourse items', len(d), 'agree', sum(a == b for _, a, b in d)); [print('  ', x) for x in d]
json.dump({D: {k: v for k, v in res[D].items() if k != 'rows'} for D in res}, open(os.path.join(HERE, 'iaa_hg_results%s.json' % ('_final' if REV else '')), 'w'), indent=1, default=str)
