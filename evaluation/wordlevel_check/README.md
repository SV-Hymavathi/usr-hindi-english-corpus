# Word-level check: health and geography

Expert verification of every automatically detected word-level candidate (names, numbers, word senses) in the Experiment 1 outputs of five systems (Google Translate, IndicTrans2, gpt-oss-120b, Ministral 14B, Gemma 3 4B) on the 960 health and geography sentences.

| File | Content |
|---|---|
| expert_verdicts.tsv | the 292 candidates with Hindi, reference, output, the rule that flagged them and the expert verdict (yes = real error) |
| wl_items.tsv | the 99 confirmed errors and whether the route from the USR (chunks; chunks + each LLM) keeps the intended item |
| sense_categories.tsv | group of each confirmed sense error (wrong sense, domain term, near-synonym) |
| wl_results.json | precision per rule, errors per system and domain, shared errors, dictionary check |
| number_check.py, number_check.json | value-based number check on the 50 number candidates |
| stats.py | Wilson intervals and Fisher exact tests |
| second_check_partA_agreement.tsv | a second annotator's verdicts on 100 of the 292 candidates, next to the expert's (agreement) |
| second_check_partB_unflagged.tsv | the second annotator's verdicts on 150 random cases that the rules did not flag (meaning lost or changed?); five rows also served as guideline examples |
