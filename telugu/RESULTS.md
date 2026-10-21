# Telugu USR -> English chunks: results on 250 tourism units (21 Oct 2026)

Run: `python3 dryrun_te_vs_hi.py checked --real` (WSL, Apertium lt-proc), usr2chunk with the Telugu rule layer.

| | units | % |
|---|---|---|
| Telugu USR output = Hindi USR output | 240/250 | 96.0 |
| Exact match with gold chunks, from Hindi USRs | 219/250 | 87.6 |
| Exact match with gold chunks, from Telugu USRs | 211/250 | 84.4 |

- Telugu gold: 250 native-speaker-checked translations (`te250_gold.tsv`); Sent_30 correction held (wrong sentence).
- Telugu concept dictionary: 586 concepts (`usr2chunk/data/te/te_dictionary.tsv`), case-sensitive WX roots from the Telugu script.
- The 10 differences are translation choices in the Telugu gold, not tool errors: pAvanI → "holy" (Sent_12, 27, 39, 45a),
  name fusions gaṅgamma / ammavāru / śrīrāmacandruḍu (Sent_14, 18, 24), nirmiṃcu "build" (Sent_33),
  prāntaṃ "area" (Sent_35), nivasiṃcu "living" (209).
- Confirmed from the full output (`te250_real_run.txt`): exactly these 10. Eight of them account for the 219 → 211 gap
  (Sent_12, 18, 24, 27, 33, 35, 39, 209); Sent_14 and 45a were already non-exact from the Hindi USR.
  No sentence is exact from Telugu but not from Hindi. All other non-exact sentences have identical Telugu and Hindi
  output, i.e. they are shared generator issues, not Telugu-specific.

General rules of the Telugu layer (no sentence-specific code):
1. Telugu roots derived from the script (te2wx); one sense number per distinct English meaning.
2. Name/phrase fusions (te_name_fusions.tsv).
3. Light verbs (USR role verbalizer) and rule-keyed function concepts (tables/te/function_hi.tsv) map back to the generator's inventory.
4. Complex-predicate entries copied per Telugu root; entries of different Hindi kriyāmūlas sharing a Telugu root are renumbered and sense-tagged.
5. Whole-compound dictionary entries copied when every member has a Telugu concept.
6. Concepts mapped back by the rule layer keep their shared dictionary entry when a Telugu concept has the same spelling.
7. Numerals are kept as they are.
