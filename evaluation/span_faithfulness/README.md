# Span-level faithfulness (missing, added and wrong information)

Analysis of the counts and words of missing, added and wrong information that the two annotators recorded for the 1,200 outputs in
`../human_evaluation_study2/ratings.tsv` (columns `ann1_missing_count`, `ann1_missing_words`, ..., `ann2_wrong_words`; "3+" is counted as 3).

- `scripts/spans.py`: rates per configuration, same-model pairs (Hindi vs USR input), agreement of the annotators -> `results/spans.json`
- `scripts/analysis2.py`: cost of each item in the scores, fluent but unfaithful outputs, error labels, severity, domains, sentence length, Holm correction -> `results/analysis2.json` (needs the Hindi sentences for sentence length; set the path at the top)
- `scripts/pooled.py`: the three LLMs pooled (450 pairs), McNemar tests for critical errors and clean outputs -> `results/pooled.json`

Run `spans.py` first. Python 3 standard library only.
