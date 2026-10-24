# Reproducing the scores

All scripts read the released data in `../inputs/` (gold references) and the system outputs in `../exp1/outputs`,
`../exp2/outputs`, `../exp3/outputs` (one line per sentence: `domain<TAB>id<TAB>output`).

| Script | Produces | Command |
|---|---|---|
| `dataset_stats.py` | Corpus statistics and sentence lengths; reads `../../corpus/` | `python dataset_stats.py` |
| `significance.py` | Paired bootstrap tests (Koehn 2004), BLEU and chrF++ with 95% CIs, all system pairs, all domains | `python significance.py --samples 1000 --seed 12345` |
| `semantic_metrics.py` | COMET (wmt22-comet-da) and BERTScore F1 (roberta-large, rescaled) | see below |
| `../iaa/iaa.py` | USR inter-annotator agreement | `python iaa.py "Annotator 2 tourism (1).xlsx"` |
| `../human_eval/score_human_eval.py` | Human evaluation agreement and per-system results | `python score_human_eval.py` |

Requirements: Python 3.10+, `pip install sacrebleu==2.6.0 numpy openpyxl`.

## COMET and BERTScore (WSL / Linux, CPU is enough)
    cd evaluation/statistics
    python3 -m venv ~/semenv
    ~/semenv/bin/pip install "unbabel-comet>=2.2" bert-score openpyxl sacrebleu
    ~/semenv/bin/python semantic_metrics.py --metric bertscore
    ~/semenv/bin/python semantic_metrics.py --metric comet
    ~/semenv/bin/python semantic_metrics.py --report
The first run downloads the models (COMET about 2.3 GB, roberta-large about 1.4 GB). Each system takes roughly
5–15 minutes on a CPU; finished systems are cached in `semantic_cache/`, so the commands can be stopped and rerun.
Run it again after Experiment 2 finishes to add those systems.
