"""J3: causes of disagreement between the two judgements, from the reasons written in the joint adjudication
(adjudication_disagreements.xlsx). Each reason is assigned to one cause by keyword rules, checked in this order:
  context      the decision needs the surrounding text, or the source is ambiguous
  not_source   the claimed device is not present in the Hindi sentence itself (false alarm of the extraction rules)
  other_form   the output expresses the meaning by another word or construction (plural implied by a numeral,
               negation by 'impossible', purpose by a lexical verb, 'it' for 'this')
  lost         the device or its meaning is missing from the output
  other        anything else (including empty reasons)
-> j3_disagreement_causes.json (counts by layer and decision, with examples)"""
import collections, json, os, re
import openpyxl
HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(os.path.expanduser('~'), 'Desktop', 'annotator_tasks', '3_J3_second_annotation')
RULES = [
    ('context', r'context|ambigu'),
    ('not_source', r'(no|not)\b[^.]{0,40}\b(present|there|in)\b[^.]{0,15}\b(hindi|source|input)|hindi (itself|also|source is also|does not|is also)|'
                   r'not in (the )?(hindi|source|input)|source (does not|is also)|no (discourse )?(connective|purpose|cause|negation|particle|plural)\b'),
    ('other_form', r'retain|same|preserv|lexical|impl(y|ie|icit)|equivalen|\bapt\b|also correct|explicit|marked|idiom|convey|express|means|tells|'
                   r'refers|correct|captur|right|fine|acceptable|kept|present in (the )?output|gives|shows?|represent|singular|plural meaning|'
                   r'question mark (is )?present|indicates|is plural|presents plural|makes the meaning|is (also )?in (the )?(past|present)|'
                   r'also in (past|present)|working as|is (a )?(discourse )?connective|in fact|similar|re+tains|marks|sense|meaning of|superlative'),
    ('lost', r'miss|omit|lost|not (been )?(transla|trasnla|transal)|transalted into|translated into|not comes|not come|dropped|absent|'
             r'not (present|there) in (the )?output|error|wrong|changed|chang|should be|statement'),
]
ws = openpyxl.load_workbook(os.path.join(D, 'adjudication_disagreements.xlsx'))['Disagreements']
h = [c.value for c in ws[1]]
iL, iC, iD, iR = (h.index(x) for x in ('Layer', 'Claimed error', 'AGREED DECISION', 'Reason'))
C = collections.defaultdict(collections.Counter); EX = collections.defaultdict(list); tot = collections.Counter()
for r in ws.iter_rows(min_row=2, values_only=True):
    if not r[0]: continue
    reason = str(r[iR] or '').lower()
    cause = 'no reason' if reason in ('', 'none') else next((c for c, p in RULES if re.search(p, reason)), 'other')
    dec = 'error' if str(r[iD]).startswith('1') else 'not an error'
    C[r[iL]][(cause, dec)] += 1; tot[(cause, dec)] += 1
    if len(EX[(r[iL], cause)]) < 3 and r[iR]: EX[(r[iL], cause)].append((str(r[iC])[:90], str(r[iR])[:160], dec))
out = {'total': {'%s|%s' % k: v for k, v in tot.items()}, 'by_layer': {L: {'%s|%s' % k: v for k, v in c.items()} for L, c in C.items()},
       'examples': {'%s|%s' % k: v for k, v in EX.items()}}
json.dump(out, open(os.path.join(HERE, 'j3_disagreement_causes.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
for L, c in C.items():
    print(L, dict(sorted(c.items())))
print('TOTAL', dict(sorted(tot.items())))
