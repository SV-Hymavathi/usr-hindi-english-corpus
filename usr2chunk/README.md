# usr2chunk: USR to English chunk generator (release v1.0, 2026-10)

`usr2chunk` reads Hindi **USRs** (Universal Semantic Representations) and writes **English chunks**:

```
96: [more police force]_SUBJ [from point of view of security] [in gadha mukteshvara] [than before] [has been deployed]_PASSIVE
```

- It reads **only the USR rows**. The `#` Hindi sentence line is never used for generation, so the same tool works for USRs made from any source language.
- It has **no sentence-specific code**. Every rule is written in terms of USR relations, features, markers and constructions. Every English-specific fact (word choice, prepositions, tense forms, connectives, word lists) lives in a data table or in the concept dictionary.

---

## 1. Installation

The tool runs on Linux, or on Windows through WSL (Ubuntu).

| Requirement | Install |
|---|---|
| Python 3.8+ (standard library only) | `sudo apt install python3` |
| Apertium `lt-proc` (English morphology) | `sudo apt install lttoolbox` |

The English transducers (`data/apertium_eng/*.bin`) and the concept dictionary (`data/concept-to-mrs-rels.dat`) are bundled, so nothing else needs to be downloaded.

```bash
cd usr2chunk
chmod +x run.sh
./run.sh test                     # checks morphology and the regression lock (should print OK)
```

### Windows (new machine), step by step

1. In PowerShell (as administrator): `wsl --install -d Ubuntu`, restart, and create the Ubuntu user when asked.
2. In the Ubuntu window: `sudo apt update && sudo apt install -y python3 lttoolbox`
3. Copy the `usr2chunk` folder anywhere, e.g. `C:\tools\usr2chunk`.
4. In Ubuntu: `cd /mnt/c/tools/usr2chunk && sed -i 's/\r$//' run.sh && chmod +x run.sh`
   (the `sed` removes Windows line endings in case the folder was copied through Windows).
5. Run `./run.sh test`, then `./run.sh eval`. The eval numbers should match section 5.

### Linux

Install `python3` and `lttoolbox` with your package manager, unpack the folder, and run `./run.sh test`.

`generate.py` finds the dictionary and the Apertium files relative to its own folder (`data/`), so the folder can be moved anywhere. To use a different dictionary, set `USR2CHUNK_DICT=/path/to/concept-to-mrs-rels.dat`.

---

## 2. Running

```bash
./run.sh examples/sample_10.txt          # 10 tourism USRs  -> out/sample_10.chunks.txt
./run.sh examples/health_402.txt         # 402 health USRs
./run.sh examples/geography_558.txt      # 558 geography (NCERT) USRs
./run.sh examples/geography_558.txt eval/gold_geography.tsv eval/ids_geography.txt   # generate + score
./run.sh my_usrs.txt                     # any USR file
./run.sh my_usrs.txt gold.tsv ids.txt    # generate and score against your own gold
./run.sh eval                            # score every bundled set (tourism, health, geography)
python3 usr.py examples/sample_10.txt 96 # show how one sentence is parsed (tree view)
```

Every run writes two files:
- `out/<name>.chunks.txt`: one line per sentence, `sid: [chunk]_SUBJ [chunk] ... [verb group]_ACTIVE|_PASSIVE`.
  - A sentence that crashes is written as `sid: [ERROR <type>]`, and the other sentences still run.
- `out/<name>.usr_issues.csv`: USR structure problems (missing heads, cycles, a wrong number of columns, …). These are worth fixing in the USR before reading the output.

### Input format

The input is the standard USR text format, one block per sentence:

```
<sent_id=96>
#सुरक्षा के लिहाज से गढ़ मुक्तेश्वर में पहले के मुकाबले पुलिस फोर्स ज्यादा लगाई गई है ।
surakRA_2 1 - - 36:r6 - - - -
lihAja_8 36 - - 14:rh - - - -
...
lagA_2-yA_gayA_hE_1 14 - - 0:main - - - -
%pass_affirmative
</sent_id>
```

Each row has 9 columns: `concept idx semantic gnp head:relation discourse speaker-view scope construction`.

### Gold / score format

- Gold: `sid<TAB>[chunk]_SUBJ [chunk] ... [verb]_ACTIVE`.
- `ids.txt`: one sentence id per line.
- `score.py` reports exact match (case- and space-insensitive) and chunk precision, recall and F1.

---

## 3. What is inside

| Path | What it is |
|---|---|
| `generate.py` | The generator (layers A to F, below) |
| `morph.py` | English inflection through Apertium, with rule-based fallback |
| `tables/en/*.tsv` | **All English-specific knowledge** (edit these, not the code) |
| `data/concept-to-mrs-rels.dat` | Concept dictionary (Hindi concept → English word) |
| `data/apertium_eng/` | Apertium English generator and analyser |
| `examples/` | `sample_10.txt`, `tourism_all_561.txt` (dev + held-out), `tourism_new_549.txt`, `health_402.txt`, `geography_558.txt` |
| `eval/` | Gold files and id lists: tourism dev/held-out (`gold_tourism_dev.tsv`, `gold_tourism_heldout.tsv`, `split_*.txt`), `gold_new549.tsv`, `gold_health.tsv`, `gold_geography.tsv` |
| `tests/` | Morphology tests and the regression lock (sentences that must not change) |
| `validate_usr.py` | USR structure checker |
| `usr.py` | Prints how a sentence is parsed |
| `docs/idioms_and_fixed_expressions.xlsx` | Every idiom / fixed expression the tool handles (Hindi, USR pattern, English, where it is implemented) and how to add new ones |

### Generator layers (`generate.py`)

| Layer | Job |
|---|---|
| A reader | USR rows → tree. Resolves named entities, conj/disjunct, complex predicates (cp), measures, spans, calendars and compounds. Re-attaches dependents of construction members to the construction. |
| B noun phrase | Determiners, quantifiers, modifiers, the "of" chain (`A kA B` → `B of A`), participle post-modifiers, appositions, particles, plurals, comparatives |
| C case marking | Relation → preposition, refined by word lists (on/at/among/by/from/into, time words, verb-governed prepositions) |
| D verb group | TAM → tense/aspect/modal; voice (passive, causative "got V-ed", impersonal); agreement; complex-predicate verbs from the dictionary |
| E clause | Subject choice (k1; k2 in passive; experiencer; causer), "by"-agent, predicates, non-finite clauses (kar-participle, purpose, cause), comparison standard ("than X"), connectives |
| F order | Connective → relative/question word → subject → adjuncts (Hindi order) → predicate → verb |

### The tables (`tables/en/`)

| File | Contents |
|---|---|
| `relations.tsv` | Default preposition for each USR relation (k3 = with, k5 = from, k5prk = with, k2as = along with, …) |
| `prep_lists.tsv` | Word lists that refine prepositions and agreement: on_heads, at_heads, from_heads, duration_heads, into_verbs, location_verbs, direct_goal_verbs, impersonal_verbs, obligation_tams, degree_adjectives, sentence_adverbs, postnominal_heads, … |
| `tam.tsv` | Hindi TAM → English tense/aspect/modal (e.g. `yA_WA_1` = past perfect "had done", `wA_hogA` …) |
| `markers.tsv` | Particles (hI = "X only", BI = "also X", kevala/mAwra/sirPa = "only X") |
| `discourse.tsv` | Discourse relation label → English connective (samuccaya = and, viroXI = but, viroXI_xyowaka = whereas, …) |
| `verb_governed.tsv` | Verb + relation → preposition (rule + k7 = over, take pride + k7 = on, listen + k2 = to, gift + k4 = none) |
| `governed.tsv` | Adjective → preposition (related to, equal to) |
| `verbalizers.tsv` | Light verbs of complex predicates |

### Concept dictionary conventions (`data/concept-to-mrs-rels.dat`)

- Rows: `concept concept <USR-sense-ids> english_N mrs-relation`. The last row for a key wins.
- **Complex predicates:** key `<kriyAmUla>+<light verb>_<n>` (e.g. `smaraNa+ho_1` = remember).
- **Whole compounds / pairs:** key `<member1>+<member2>` (e.g. `kenxraSAsiwa_1+praxeSa_1` = union territory).
- **Idioms:** verb + shade verb (e.g. `Ko+jA_1` = get lost).
- `+` inside the English joins words (`over+time`).

---

## 4. Conventions the output follows (decided with the project lead)

| Topic | Rule |
|---|---|
| Source of truth | The USR is authoritative. Word choice comes from the dictionary sense in the USR. Names and ^-words without a sense number are transliterated. |
| Plural | Only USR `pl` (or a count > 1) makes a plural, including on names. `respect` is honorific, not plural. |
| Compounds | `6-waw`/`6_waw`/`6-tat` → "head of modifier" ("building of temple"); every other compound or noun modifier → "modifier head" |
| Predicative "of" | Only when the USR has an r6 |
| Deixis | proximal → this/here, distal → that/there |
| Material | k5prk → "with" ("built with sand stone") |
| Dates | "16th august 1956" |
| Distance | "N kilometres away from X" / "at distance of N from X" in one chunk |
| Relatives | जिसमें = "in which", जहाँ = "where" |
| kar-participle (rpk) | passive or no subject → "by V-ing"; active with a subject → "V-ing" / "having V-ed" (complex predicate) |
| Tense | `kiyA thA` = "had done"; presumptive `hogA` = "may have"; present perfect stays perfect |
| Discourse | The connective comes from the USR discourse label |
| Adverbs | Single-word adverbs go right before the verb; "in fact" and similar go first |
| Apposition | Persons: name first, then comma ("shreyamshakumara, younger brother of …"); two place names keep the Hindi order |

---

## 5. Results (`./run.sh eval`)

| Set | USRs | Exact match |
|---|---|---|
| Tourism dev | 449 | **90.2%** |
| Tourism held-out (never used to write rules) | 112 | 78.6% |
| Tourism new set | 549 | **86.3%** |
| Health | 402 | **80.3%** |
| Geography (NCERT) | 558 | **80.1%** |

Gold files are post-edited to the conventions in section 4 (no articles, literal case prepositions, connective from the discourse label).
A per-sentence breakdown with error types and reasons is in `usr2chunk_results_all_domains.xlsx`, delivered next to this folder.

### Writing USRs for a new domain (what was done for health and geography)

- Split the source text into complete sentences. Split long sentences at clause boundaries and link the parts with discourse relations.
- Take every concept sense from `data/concept-to-mrs-rels.dat`. Reuse an existing sense whenever its English fits; add a new sense (`_96` …) only for a meaning the dictionary lacks.
- Write abbreviations as `@` words (`@o.Ara.esa` → ORS) and mark passives with `%pass_affirmative` / `%pass_negative`.

## 6. Extending to new data

1. Run `./run.sh new.txt`.
2. Fix what `out/new.usr_issues.csv` reports in the USR.
3. Wrong English word → fix or add the **dictionary** row (do not hard-code it).
4. Wrong preposition, tense or connective → add a row to the relevant **table**.
5. A new construction → add a general rule in `generate.py`, then run `./run.sh test` so the locked sentences do not change.

To add another output language, copy `tables/en/` to `tables/<lang>/`, give it its own morphology module and dictionary column, and keep layers A, E and F.
