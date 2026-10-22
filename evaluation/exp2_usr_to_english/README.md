# Experiment 2: generation of English from the USR by LLMs

Data of the paper *Can Large Language Models Generate Faithfully from a Pāṇinian Meaning Representation?
A Layer-by-Layer Study on Hindi USR* (Sirisipalli, Sukhada, Paul and Jha).

| File | Content |
|---|---|
| `exp2_input.tsv` | the 2,071 USRs given to the models (domain, id, USR; line breaks written as `\n`) |
| `exp2_input_gloss.tsv` | the same USRs with the English gloss of every concept (`xarSana_23=visit`), condition E2c; the light verb of a complex predicate carries the English of the whole predicate (`build_gloss.py`) |
| `usr_guidelines.md` | the guide given in conditions E2b and E2c |
| `config.json` | models, settings and the prompts of the three conditions |
| `outputs/` | the 18,639 outputs: 3 models x 3 conditions (`_raw` = E2a, `_guide` = E2b, `_gloss` = E2c) |
| `exp2_final_error_analysis.xlsx` | scores and layer-by-layer flags of every output (one sheet per layer) |
| `human_verification/` | the two annotators' judgements of 359 flagged errors (72 judged by both), the key (system, condition, layer of each item) and `score_nle_verification.py`, which computes precision and agreement |

The experiment used the USRs before the final validation pass of the corpus (116 of the 2,071 USRs were corrected
afterwards, mostly in one row); `exp2_input.tsv` holds the versions that the models received.
