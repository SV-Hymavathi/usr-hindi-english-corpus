# A Multi-Domain Hindi Corpus of Universal Semantic Representations (USR) with English References and Gold Chunks, and the usr2chunk Generator

This repository accompanies the paper *A Multi-Domain Hindi Corpus of Universal Semantic Representations with English References and Gold Chunks, and a Table-Driven Generator from USR to English* (Veera Hymavathi Sirisipalli, Satyaprakash Jha, Sukhada and Soma Paul).

## Contents

| Folder | What it contains |
|---|---|
| `corpus/` | 2,071 gold USRs: `tourism.jsonl` (1,111), `health.jsonl` (402), `geography.jsonl` (558). Each record has `id`, `domain`, `hindi`, `usr`, `reference` (English), `gold_chunks` and `generator_chunks`. `usr_text/` has the same USRs in USR text format. `geography_corrected_sentence_pairs.tsv` lists the corrected geography sentence pairs with the reason for each correction. `validator_corrections_log.tsv` lists the corrections made in the final structural-validation pass. `splits/` gives a recommended train / dev / test split (1,590 / 177 / 304 USRs; the test set contains the 112 tourism USRs never inspected during development). |
| `dictionary/` | `concept_dictionary_full.dat`: the complete Hindi concept dictionary used by the generator (concept, sense, English, MRS predicate). `dictionary_additions.dat`: concept senses and complex-predicate entries added during annotation (sense numbers 90–99), in the format of the shared Hindi concept dictionary (`cl hl sl el mrsc`). |
| `agreement/` | `tourism_250/`: the two independent annotations of the first 250 tourism sentences and the agreement results. `health_geography_100/`: the independent second annotation of 100 health and geography sentences and its agreement with the corpus USRs. `scripts/`: the agreement scripts. |
| `usr2chunk/` | The rule-based generator from USR to English chunks: code, the nine English knowledge tables (`tables/en/`), Apertium transducers, examples, regression tests and the evaluation data. |
| `telugu/` | Telugu translations of the first 250 tourism units (checked by a native speaker), the 250 Telugu USRs, the Telugu–English concept dictionary (586 concepts) and the English generated from Telugu and Hindi USRs (paper, Section 7). The Telugu rule layer of the generator is `usr2chunk/generate_te2en.py` with `usr2chunk/tables/te/`. |
| `evaluation/` | `reference_quality/`: expert ratings of 150 English references. `chunks_without_draft/`: 100 chunk sequences written without any draft (draft-bias check). `use_case_llm_rewrite/`: language-model rewrites of the generator chunks (Section 9). `statistics/`: scripts for corpus statistics, COMET/BERTScore and significance tests. |

## Quick start

```bash
cd usr2chunk
./run.sh test     # morphology and regression tests
./run.sh eval     # reproduces Table 9 (exact match and chunk F1 for all data sets)
./run.sh examples/health_402.txt    # generate chunks for any USR file
```

Requirements: Linux (or WSL on Windows), Python 3.8+, and Apertium's `lt-proc` (`sudo apt install apertium lttoolbox`),
which is used with the bundled English transducers in `usr2chunk/data/apertium_eng/`.

## USR format

Each USR row has nine columns: concept, index, semantic category, morpho-semantics (GNP), head:relation,
discourse relation, speaker's view, scope, construction. The last line gives the sentence type. Concepts are in WX
transliteration with dictionary sense numbers (e.g. `xarSana_23`). See the paper, Section 3, for details.

## Sources

Tourism and health sentences come from the ILCI Hindi–English parallel corpora (Jha 2010; Choudhary and Jha 2014),
geography sentences from the NCERT Class 6 Social Science (Geography) textbook. The source texts belong to their providers.

## Licence

Annotations (USRs, references, gold chunks, dictionary additions, agreement data): CC BY-NC-SA 4.0 (`LICENSE-DATA`).
Code (`usr2chunk`, scripts): MIT (`LICENSE-CODE`).

## Citation

Please cite the paper if you use this resource (citation to be added on publication).
