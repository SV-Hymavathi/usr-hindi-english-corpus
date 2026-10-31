# Paired human evaluation: the same language models from the Hindi sentence and from the USR

150 sentences (50 per domain) were given to three language models (gpt-oss-120b, Gemma 3 4B, Ministral 14B) twice: as the
Hindi sentence (translation) and as the English phrase chunks that the usr2chunk generator derives from the gold USR
(rewrite into one sentence). Google Translate and IndicTrans2 translated the Hindi sentence as reference points. The 1,200
outputs were shuffled and rated blind and independently by two trained annotators.

| File | Contents |
|---|---|
| `ratings.tsv` | every output with its system and input, and both annotators' ratings |
| `results/paired_human_evaluation.json` | agreement, ratings and error groups per configuration, paired tests |
| `scripts/j2_stats.py` | the script that computed the results (paths refer to the authors' working copy) |

Ratings (1-5): comprehensibility, judged from the output alone before the Hindi and the reference were shown; adequacy,
judged against the Hindi sentence; fluency. Error type: the most serious error, one of 15 types (`none (correct)` if the
output is correct). Sentence ids refer to `corpus/`; the Hindi sentence and the reference are in the corpus files.
