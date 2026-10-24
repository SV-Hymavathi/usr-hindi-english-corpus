# A Multi-Domain Hindi Corpus of Universal Semantic Representations (USR) with English References and Gold Chunks, and the usr2chunk Generator

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23559461.svg)](https://doi.org/10.5281/zenodo.23559461)

This repository contains 2,071 Hindi sentences from three domains (tourism, health and school geography) with gold Universal Semantic Representations (USRs), expert English references and gold English chunks, together with usr2chunk, a rule-based generator from USR to English, and the data and scripts of its evaluation.

## Contents

| Folder | What it contains |
|---|---|
| `corpus/` | 2,071 gold USRs: `tourism.jsonl` (1,111), `health.jsonl` (402), `geography.jsonl` (558). Each record has `id`, `domain`, `hindi`, `usr`, `reference` (English), `gold_chunks` and `generator_chunks`. `usr_text/` has the same USRs in USR text format. `geography_corrected_sentence_pairs.tsv` lists the corrected geography sentence pairs with the reason for each correction. `validator_corrections_log.tsv` lists the corrections made in the final structural-validation pass. `splits/` gives a recommended train / dev / test split (1,590 / 177 / 304 USRs; the test set contains the 112 tourism USRs never inspected during development). |
| `dictionary/` | `concept_dictionary_full.dat`: the complete Hindi concept dictionary used by the generator (concept, sense, English, MRS predicate). `dictionary_additions.dat`: concept senses and complex-predicate entries added during annotation (sense numbers 90–99), in the format of the shared Hindi concept dictionary (`cl hl sl el mrsc`). |
| `agreement/` | `tourism_250/`: the two independent annotations of the first 250 tourism sentences and the agreement results. `health_geography_100/`: the independent second annotation of 100 health and geography sentences and its agreement with the corpus USRs. `scripts/`: the agreement scripts. |
| `usr2chunk/` | The rule-based generator from USR to English chunks: code, the nine English knowledge tables (`tables/en/`), Apertium transducers, examples, regression tests and the evaluation data. |
| `telugu/` | Telugu translations of the first 250 tourism units (checked by a native speaker), the 250 Telugu USRs, the Telugu–English concept dictionary (586 concepts) and the English generated from Telugu and Hindi USRs. The Telugu rule layer of the generator is `usr2chunk/generate_te2en.py` with `usr2chunk/tables/te/`. |
| `evaluation/` | `reference_quality/`: expert ratings of 150 English references. `chunks_without_draft/`: 100 chunk sequences written without any draft (draft-bias check). `use_case_llm_rewrite/`: language-model rewrites of the generator chunks. `exp2_usr_to_english/`: inputs, outputs, layer-by-layer flags and human verification of LLMs generating English from the USR (Experiment 2). `wordlevel_check/`: expert verification of every automatically detected name, number and word-sense error of five MT systems and LLMs in the health and geography sentences, with the dictionary check and a value-based number check. `statistics/`: scripts for corpus statistics, COMET/BERTScore and significance tests. |

## Quick start

```bash
cd usr2chunk
./run.sh test     # morphology and regression tests
./run.sh eval     # reproduces the evaluation (exact match and chunk F1 for all data sets)
./run.sh examples/health_402.txt    # generate chunks for any USR file
```

Requirements: Linux (or WSL on Windows), Python 3.8+, and Apertium's `lt-proc` (`sudo apt install apertium lttoolbox`),
which is used with the bundled English transducers in `usr2chunk/data/apertium_eng/`.

## USR format

Each USR row has nine columns: concept, index, semantic category, morpho-semantics (GNP), head:relation,
discourse relation, speaker's view, scope, construction. The last line gives the sentence type. Concepts are in WX
transliteration with dictionary sense numbers (e.g. `xarSana_23`).

## Sources

Tourism and health sentences come from the ILCI Hindi–English parallel corpora (Jha 2010; Choudhary and Jha 2014),
geography sentences from the NCERT Class 6 Social Science (Geography) textbook. The source texts belong to their providers.

## Licence and terms of use

**Data** (USRs, English references, gold chunks, dictionary additions, agreement data, evaluation data):
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) (`LICENSE-DATA`). This means:

- **Research and teaching use only.** Commercial use of the data, including training or improving commercial
  products or services, is not permitted without written permission from the authors.
- **Attribution is required.** Every publication, thesis, report, software or dataset that uses this data, in full or
  in part, must cite it as given below and acknowledge the authors.
- **Share alike.** Data derived from this resource (e.g. extended or converted USRs) must be released under the same
  licence.

**Code** (`usr2chunk`, scripts): MIT (`LICENSE-CODE`).

The Hindi source sentences come from the ILCI corpora and the NCERT Class 6 geography textbook; they remain the property
of their providers and are subject to their terms.

For commercial licensing or other permissions, contact Veera Hymavathi Sirisipalli
(sirisipallivhymavathi.rs.hss24@itbhu.ac.in).

## How to cite

Please cite the resource as:

> Veera Hymavathi Sirisipalli, Sukhada and Soma Paul. 2026. *USR Hindi-English Corpus: Universal
> Semantic Representations with English references and gold chunks, and the usr2chunk generator.* Zenodo.
> https://doi.org/10.5281/zenodo.23559461

```bibtex
@misc{sirisipalli2026usrcorpus,
  author       = {Sirisipalli, Veera Hymavathi and Sukhada and Paul, Soma},
  title        = {{USR Hindi-English Corpus: Universal Semantic Representations with English references and gold chunks, and the usr2chunk generator}},
  year         = {2026},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.23559461},
  url          = {https://doi.org/10.5281/zenodo.23559461},
  note         = {Licensed under CC BY-NC-SA 4.0}
}
```

GitHub's "Cite this repository" button (from
`CITATION.cff`) gives the same citation.

## Contributors

Satyaprakash Jha (Indian Institute of Technology (Banaras Hindu University), ORCID 0009-0008-2865-5320) contributed
to the data collection.
