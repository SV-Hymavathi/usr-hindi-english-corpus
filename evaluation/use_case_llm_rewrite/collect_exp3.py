#!/usr/bin/env python3
"""Collect Experiment 1 outputs into exp3_outputs.xlsx: one sheet per system (Domain, ID, Hindi, Output),
plus an 'All systems' sheet side by side and a 'Progress' sheet. Safe to run at any time."""
import os, json
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, 'config.json'), encoding='utf-8'))
rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(HERE, 'exp3_input.tsv'), encoding='utf-8') if l.count('\t') == 2]
HDR = PatternFill('solid', fgColor='305496')


def style(ws, widths):
    for c in ws[1]:
        c.font = Font(bold=True, color='FFFFFF'); c.fill = HDR
    for i, w in enumerate(widths):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i + 1)].width = w
    for r in ws.iter_rows(min_row=2):
        for c in r:
            c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.freeze_panes = 'C2'


outs = {}
for n in CFG['systems']:
    f = os.path.join(HERE, 'outputs', n + '.tsv')
    if os.path.exists(f):
        outs[n] = {tuple(l.rstrip('\n').split('\t')[:2]): l.rstrip('\n').split('\t', 2)[2]
                   for l in open(f, encoding='utf-8') if l.count('\t') >= 2}
wb = openpyxl.Workbook()
pg = wb.active; pg.title = 'Progress'
pg.append(['System', 'tourism', 'health', 'geography', 'Total done', 'Of'])
for n, o in outs.items():
    c = {d: sum(1 for r in rows if r[0] == d and (r[0], r[1]) in o) for d in ('tourism', 'health', 'geography')}
    pg.append([n, c['tourism'], c['health'], c['geography'], sum(c.values()), len(rows)])
style(pg, [26, 10, 10, 10, 12, 8])
al = wb.create_sheet('All systems')
al.append(['Domain', 'ID', 'Generator chunks'] + list(outs))
for d, i, h in rows:
    al.append([d, i, h] + [o.get((d, i), '') for o in outs.values()])
style(al, [10, 9, 50] + [45] * len(outs))
for n, o in outs.items():
    ws = wb.create_sheet(n[:31])
    ws.append(['Domain', 'ID', 'Generator chunks', 'Output'])
    for d, i, h in rows:
        ws.append([d, i, h, o.get((d, i), '')])
    style(ws, [10, 9, 55, 60])
wb.save(os.path.join(HERE, 'exp3_outputs.xlsx'))
print('exp3_outputs.xlsx written:', ', '.join('%s %d' % (n, len(o)) for n, o in outs.items()))
