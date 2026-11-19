# Meta-evaluation of automatic metrics against the human judgements

Every output rated in `../human_evaluation/` (study S1, 1,184 fully rated outputs) and `../human_evaluation_study2/`
(study S2, 1,200 outputs), with both annotators' judgements and five automatic metrics computed against the corpus reference:
chrF++ (word order 2) and sentence BLEU (effective order) in sacreBLEU; BERTScore F1 (roberta-large, baseline-rescaled);
COMET (Unbabel/wmt22-comet-da, reference-based, reads the Hindi source); MetricX-24 (google/metricx-24-hybrid-large-v2p6,
reference-based; an error score, lower is better).

| File | Contents |
|---|---|
| `segment_scores.tsv` | one row per rated output: study, sentence, system, input route, output, human judgements, five metric scores |
| `results/meta_eval.json` | segment-level Kendall tau (with bootstrap CI), AUCs, system means, scores by error type |
| `results/meta_eval2.json` | pairwise accuracy, scores at equal adequacy, regression on adequacy and fluency |
| `results/meta_eval3.json` | agreement with single annotators, direction-dependent pairwise accuracy with bootstrap tests (per study and pooled) |
| `scripts/` | the scripts that computed the scores and results (paths refer to the authors' working copy) |

The text in `output` is exactly the text that the annotators rated and that the metrics scored.
