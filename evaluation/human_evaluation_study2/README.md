# Paired human evaluation, second study: 150 further sentences

The same design as `../human_evaluation/` on 150 further sentences of the corpus (104 tourism, 19 health, 27 geography;
five also occur in the first study). Google Translate, IndicTrans2 and three language models (gpt-oss-120b, Gemma 3 4B,
Ministral 14B) translated the Hindi sentence; the same three language models also wrote the sentence from the English
chunks of its USR, with a writing prompt with examples. The 1,200 outputs were shuffled and rated blind and independently
by the same two trained annotators.

| File | Contents |
|---|---|
| `ratings.tsv` | every output with its system and input, and both annotators' judgements |
| `scripts/study2_stats.py` | the script that computed the agreement, configuration means and paired tests (paths refer to the authors' working copy) |

Judgements per annotator: comprehensibility (1-5, from the output alone), adequacy (1-5, against the Hindi), fluency (1-5),
main error type (one of 15), severity of the main error (none, minor, major, critical), and three faithfulness counts
(missing, added and wrong information) with the words concerned. Sentence ids refer to `corpus/`.
