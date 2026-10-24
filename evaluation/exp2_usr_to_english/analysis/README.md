# Analysis of Experiment 2 (LLMs generating English from the USR)

Scripts and results of the Experiment 2 analysis (layer-by-layer study of LLMs reading the USR). No LLM is used in any of them.

| File | What it computes |
|---|---|
| `layered_analysis.py` | The layer-by-layer error checks (lexical, morphology, relations, discourse, speaker's view, sentence type, adequacy, output form). |
| `nle_extended_analysis.py` → `nle_extended_results.json` | chrF++/BLEU with 95% bootstrap intervals, paired bootstrap and McNemar tests, results without the 116 USRs changed after the run and without the 246 inputs with the gloss `kara_1=hand`, errors by layer for all routes, cross-model agreement, error sub-types per run, error rate by USR size and by domain. |
| `nle_phenomena.py` → `nle_phenomena.json` | Loss rate of each phenomenon over the sentences in which the USR records it and the reference expresses it. |
| `nle_label_leak.py` → `nle_label_leak.json` | Outputs that turn the construction label `begin` or relation labels into words. |
| `nle_gloss_check.py` | Inputs in which the verbalizer `kara_1` is glossed `hand`, and outputs that contain a spurious `hand`. |
| `nle_data_stats.py` → `nle_data_stats.json` | Per-domain statistics of the inputs. |
| `resources/` | Dictionary English of the concepts, TAM table, discourse table and culture-specific concepts used by the checks. |

The scripts were run in the experiment layout `experiments/{inputs,exp1,exp2,exp3}`: `inputs/` holds the USRs as given to
the models with their references (the versions in `../exp2_input.tsv`), `exp2/outputs/` the outputs in `../outputs/`,
`exp3/outputs/` the content-plan outputs in `../../use_case_llm_rewrite/`, and `exp1/outputs/` the direct translations.
