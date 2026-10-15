#!/usr/bin/env python3
"""Experiment 1 – final error analysis for ALL systems and ALL three domains in one workbook.

  python3 final_analysis.py   ->  exp3_final_error_analysis.xlsx

Uses the same layer checks as layered_analysis.py (USR-guided, confirmed by the gold reference, no LLM judge).
Sheets
  Summary              per system x domain and overall: BLEU, chrF++, % sentences with an error, errors per layer;
                       best value in green, worst in red; ranking of systems
  Error sub-types      every kind of mistake, counted per system (all domains) and per domain
  Shared errors        sentences where all 3 LLMs (and where all 5 systems) made the same kind of mistake
  Shared summary       how many errors are shared by all LLMs / all systems / unique to one system, per layer
  L1a ... L8           one tab per layer: every error of that layer (domain, system, sentence, sub-type, detail)
  All sentences        every sentence, all system outputs and their errors side by side
"""
import collections, os, sys, re
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
import sacrebleu

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = open(os.path.join(HERE, 'layered_analysis.py'), encoding='utf-8').read().split('# ---------------- run ----------------')[0]
LLMS = ['groq_gpt-oss-120b', 'mistral_ministral-14b', 'ollama_gemma3-4b']
MT = ['usr2chunk_literal']          # baseline: generator chunks as a literal sentence
ORDER = LLMS + MT
NICE = {'usr2chunk_literal': 'Generator chunks (literal, no LLM)', 'groq_gpt-oss-120b': 'Groq gpt-oss-120b', 'mistral_ministral-14b': 'Mistral ministral-14b', 'ollama_gemma3-4b': 'Gemma3 4b (Ollama)',
        'google_translate': 'Google Translate', 'indictrans2_local': 'IndicTrans2 (local)'}
DOMS = ['tourism', 'health', 'geography']

recs, sent, refs, NS = [], {}, {}, None
for d in DOMS:
    sys.argv = ['x', '--domain', d]
    ns = {'__file__': os.path.join(HERE, 'layered_analysis.py'), '__name__': 'la', '__doc__': ''}
    exec(SRC, ns)
    NS = ns
    for it in ns['items']:
        i, ref = it['id'], it['reference']
        hin = ns['hindi'].get(i, it['hindi'])
        refs[(d, i)] = (hin, ref)
        for s in ORDER:
            if s not in ns['SYS']:
                continue
            out = ns['SYS'][s].get(i, '')
            R = ns['analyse'](it, hin, ref, out)
            sent[(d, i, s)] = (out, R)
            for t, sub, det in R:
                recs.append((d, s, i, t, sub, det))
    print(d, 'done', len(ns['items']), 'sentences, systems:', [s for s in ORDER if s in ns['SYS']])
TABS, ERROR_TABS = NS['TABS'], NS['ERROR_TABS']
SYSS = [s for s in ORDER if any(k[2] == s for k in sent)]
N = {d: sum(1 for k in refs if k[0] == d) for d in DOMS}

# ---------------- scores ----------------
score = {}
for d in DOMS + ['ALL']:
    ds = DOMS if d == 'ALL' else [d]
    keys = [k for k in refs if k[0] in ds]
    for s in SYSS:
        hyp = [sent[(k[0], k[1], s)][0] for k in keys]; ref = [refs[k][1] for k in keys]
        err_sents = {(k[0], k[1]) for k in keys if any(t in ERROR_TABS for t, _, _ in sent[(k[0], k[1], s)][1])}
        lay = collections.Counter()
        for k in keys:
            for t in {t for t, _, _ in sent[(k[0], k[1], s)][1]}:
                lay[t] += 1
        score[(d, s)] = dict(n=len(keys), bleu=sacrebleu.corpus_bleu(hyp, [ref]).score,
                             chrf=sacrebleu.corpus_chrf(hyp, [ref], word_order=2).score,
                             err=100.0 * len(err_sents) / len(keys), lay=lay)

HDR = PatternFill('solid', fgColor='305496'); GREEN = PatternFill('solid', fgColor='C6EFCE'); RED = PatternFill('solid', fgColor='FFC7CE')
SEC = Font(bold=True, size=12)
wb = openpyxl.Workbook(); sm = wb.active; sm.title = 'Summary'


def header(ws, row):
    ws.append(row)
    for c in ws[ws.max_row]:
        c.font = Font(bold=True, color='FFFFFF'); c.fill = HDR; c.alignment = Alignment(wrap_text=True, vertical='center')


def mark(ws, first_row, last_row, col, higher_better):
    vals = [(r, ws.cell(r, col).value) for r in range(first_row, last_row + 1) if isinstance(ws.cell(r, col).value, (int, float))]
    if len(vals) < 2:
        return
    best = max(vals, key=lambda x: x[1]) if higher_better else min(vals, key=lambda x: x[1])
    worst = min(vals, key=lambda x: x[1]) if higher_better else max(vals, key=lambda x: x[1])
    ws.cell(best[0], col).fill = GREEN; ws.cell(worst[0], col).fill = RED


sm.append(['Experiment 3: generator chunks -> fluent sentence, 3 LLMs + literal baseline x 3 domains (tourism %d, health %d, geography %d sentences)' % tuple(N[d] for d in DOMS)])
sm['A1'].font = Font(bold=True, size=14)
sm.append(['Green = best, red = worst in each block and column. Errors are USR-guided and reference-confirmed (no LLM judge); '
           'L1c synonyms are acceptable variants and are not counted as errors.'])
for d in ['ALL'] + DOMS:
    sm.append([])
    sm.append([('ALL DOMAINS (%d sentences)' % sum(N.values())) if d == 'ALL' else '%s (%d sentences)' % (d.upper(), N[d])])
    sm.cell(sm.max_row, 1).font = SEC
    header(sm, ['System', 'Type', 'BLEU', 'chrF++', '% sentences with an error'] + ['%s (sentences)' % t for t in TABS])
    r0 = sm.max_row + 1
    for s in SYSS:
        sc = score[(d, s)]
        sm.append([NICE[s], 'LLM' if s in LLMS else 'baseline', round(sc['bleu'], 2), round(sc['chrf'], 2), round(sc['err'], 1)] +
                  [sc['lay'][t] for t in TABS])
    r1 = sm.max_row
    mark(sm, r0, r1, 3, True); mark(sm, r0, r1, 4, True); mark(sm, r0, r1, 5, False)
    for k, t in enumerate(TABS):
        mark(sm, r0, r1, 6 + k, t == 'L1c Synonyms')
sm.append([])
sm.append(['RANKING (all domains)']); sm.cell(sm.max_row, 1).font = SEC
header(sm, ['Rank', 'By chrF++ (higher = better)', 'chrF++', 'By BLEU', 'BLEU', 'By fewest sentences with errors', '% with error'])
byc = sorted(SYSS, key=lambda s: -score[('ALL', s)]['chrf'])
byb = sorted(SYSS, key=lambda s: -score[('ALL', s)]['bleu'])
bye = sorted(SYSS, key=lambda s: score[('ALL', s)]['err'])
for k in range(len(SYSS)):
    sm.append([k + 1, NICE[byc[k]], round(score[('ALL', byc[k])]['chrf'], 2), NICE[byb[k]], round(score[('ALL', byb[k])]['bleu'], 2),
               NICE[bye[k]], round(score[('ALL', bye[k])]['err'], 1)])
sm.append([])
sm.append(['Best overall: %s.  Worst overall: %s (by chrF++; check BLEU and error rate in the ranking above).' % (NICE[byc[0]], NICE[byc[-1]])])
sm.cell(sm.max_row, 1).font = Font(bold=True)
sm.column_dimensions['A'].width = 26; sm.column_dimensions['B'].width = 24
for c in range(3, 6 + len(TABS)):
    sm.column_dimensions[get_column_letter(c)].width = 13

# ---------------- sub-types ----------------
st = wb.create_sheet('Error sub-types')
header(st, ['Layer', 'Error sub-type'] + ['%s (all)' % NICE[s] for s in SYSS] + ['%s %s' % (NICE[s].split()[0], d[:4]) for d in DOMS for s in SYSS])
cnt = collections.Counter((t, sub, s, d) for d, s, i, t, sub, det in recs)
subs = sorted({(t, sub) for d, s, i, t, sub, det in recs}, key=lambda x: (TABS.index(x[0]), x[1]))
r0 = st.max_row + 1
for t, sub in subs:
    st.append([t, sub] + [sum(cnt[(t, sub, s, d)] for d in DOMS) for s in SYSS] + [cnt[(t, sub, s, d)] for d in DOMS for s in SYSS])
for r in range(r0, st.max_row + 1):
    vals = [st.cell(r, 3 + k).value for k in range(len(SYSS))]
    if max(vals) > 0 and st.cell(r, 1).value != 'L1c Synonyms':
        for k, v in enumerate(vals):
            if v == max(vals):
                st.cell(r, 3 + k).fill = RED
            if v == min(vals):
                st.cell(r, 3 + k).fill = GREEN
st.column_dimensions['A'].width = 22; st.column_dimensions['B'].width = 42
for c in range(3, 3 + len(SYSS) * 4):
    st.column_dimensions[get_column_letter(c)].width = 11

# ---------------- shared errors ----------------
by_sent = collections.defaultdict(lambda: collections.defaultdict(list))     # (d,i) -> (t,sub) -> [(s,det)]
for d, s, i, t, sub, det in recs:
    if t in ERROR_TABS:
        by_sent[(d, i)][(t, sub)].append((s, det))
sh = wb.create_sheet('Shared errors')
header(sh, ['Domain', 'ID', 'Shared by', 'Layer', 'Error sub-type', 'Hindi', 'Gold reference'] + ['%s output' % NICE[s] for s in SYSS] +
       ['Details per system'])
shared_cnt = collections.Counter()
for (d, i), errs in by_sent.items():
    for (t, sub), lst in errs.items():
        who = {s for s, _ in lst}
        all_llm = set(LLMS) <= who
        all_sys = set(SYSS) <= who
        shared_cnt[(t, 'all systems' if all_sys else 'all 3 LLMs' if all_llm else 'one system only' if len(who) == 1 else '2-4 systems')] += 1
        if all_llm:
            hin, ref = refs[(d, i)]
            sh.append([d, i, 'all systems' if all_sys else 'all 3 LLMs', t, sub, hin, ref] + [sent[(d, i, s)][0] for s in SYSS] +
                      ['; '.join('%s: %s' % (NICE[s].split()[0], det) for s, det in lst if det)])
for c, w in zip(range(1, 9 + len(SYSS)), [10, 8, 14, 20, 30, 40, 40] + [38] * len(SYSS) + [50]):
    sh.column_dimensions[get_column_letter(c)].width = w
ss = wb.create_sheet('Shared summary')
header(ss, ['Layer', 'Errors made by all systems', 'by all 3 LLMs (not all MT)', 'by 2-4 systems', 'by one system only'])
for t in ERROR_TABS:
    ss.append([t, shared_cnt[(t, 'all systems')], shared_cnt[(t, 'all 3 LLMs')], shared_cnt[(t, '2-4 systems')], shared_cnt[(t, 'one system only')]])
ss.append([])
ss.append(['Counted per sentence and error sub-type: e.g. if every system has "tense" wrong in the same sentence, that is one shared error.'])
ss.column_dimensions['A'].width = 24
for c in 'BCDE':
    ss.column_dimensions[c].width = 22

# ---------------- layer tabs ----------------
VERD = '"real error,acceptable variant,reference problem,not an error"'
from openpyxl.worksheet.datavalidation import DataValidation
for t in TABS:
    ws = wb.create_sheet(t[:31])
    header(ws, ['Domain', 'System', 'ID', 'Hindi', 'Gold reference', 'Output', 'Sub-type', 'Detail', 'Human verdict', 'Human note'])
    rows = sorted([r for r in recs if r[3] == t], key=lambda r: (r[4], DOMS.index(r[0]), r[2], ORDER.index(r[1])))
    for d, s, i, tt, sub, det in rows:
        hin, ref = refs[(d, i)]
        ws.append([d, NICE[s], i, hin, ref, sent[(d, i, s)][0], sub, det, '', ''])
    if rows:
        dv = DataValidation(type='list', formula1=VERD, allow_blank=True); ws.add_data_validation(dv); dv.add('I2:I%d' % (len(rows) + 1))
    for c, w in zip('ABCDEFGHIJ', [10, 20, 8, 38, 38, 38, 26, 40, 15, 22]):
        ws.column_dimensions[c].width = w

al = wb.create_sheet('All sentences')
header(al, ['Domain', 'ID', 'Hindi', 'Gold reference'] + [x for s in SYSS for x in (NICE[s] + ' output', NICE[s] + ' errors')])
for (d, i), (hin, ref) in refs.items():
    row = [d, i, hin, ref]
    for s in SYSS:
        out, R = sent[(d, i, s)]
        row += [out, '; '.join('%s: %s%s' % (t.split()[0], sub, (' (' + det + ')') if det else '') for t, sub, det in R if t in ERROR_TABS)]
    al.append(row)
for k, w in enumerate([10, 8, 38, 38] + [36, 32] * len(SYSS), 1):
    al.column_dimensions[get_column_letter(k)].width = w

df = wb.create_sheet('Layer definitions')
for line in NS['__doc__'].strip().splitlines() if NS.get('__doc__') else SRC.split('"""')[1].strip().splitlines():
    df.append([line])
df.column_dimensions['A'].width = 130
for ws in wb.worksheets[1:]:
    if ws.title in ('Layer definitions', 'Shared summary', 'Error sub-types'):
        continue
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'C2'
st.freeze_panes = 'C2'
out = os.path.join(HERE, 'exp3_final_error_analysis.xlsx')
wb.save(out)
print(out)
for d in ['ALL'] + DOMS:
    print(d, ' | '.join('%s chrF %.1f BLEU %.1f err %.1f%%' % (NICE[s].split()[0], score[(d, s)]['chrf'], score[(d, s)]['bleu'], score[(d, s)]['err']) for s in SYSS))
for t in ERROR_TABS:
    print('%-24s all5 %4d  all3LLM %4d  2-4 %4d  one %4d' % (t, shared_cnt[(t, 'all systems')], shared_cnt[(t, 'all 3 LLMs')],
                                                             shared_cnt[(t, '2-4 systems')], shared_cnt[(t, 'one system only')]))
