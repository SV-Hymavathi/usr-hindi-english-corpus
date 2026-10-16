# Reviewer guide: running usr2chunk and checking the results

Time needed: about 15 minutes. Everything runs offline; no model or API is used.

## 1. Requirements (Linux, or WSL on Windows)

```bash
sudo apt update
sudo apt install python3 lttoolbox      # lttoolbox provides lt-proc (English morphology)
```

Python 3.8+ with the standard library is enough.

## 2. Go to the tool

```bash
git clone https://github.com/SV-Hymavathi/usr-hindi-english-corpus.git
cd usr-hindi-english-corpus/usr2chunk
chmod +x run.sh
```

(On Windows/WSL, a folder on the Windows Desktop is reached as `/mnt/c/Users/<name>/Desktop/...`.
If `run.sh` reports `\r`, run `sed -i 's/\r$//' run.sh` once.)

## 3. Tests

```bash
./run.sh test
```

Checks the English morphology and a regression lock of 441 sentences. The last line should read
`regression: 441/441 locked sentences still exact`.

## 4. Reproduce Table 9 of the paper

```bash
./run.sh eval
```

Expected output:

```
dev      (post-edited gold):  exact 406/449 = 90.4%   chunk F1 0.955
held-out (post-edited gold):  exact  88/112 = 78.6%   chunk F1 0.892
tourism new 549:              exact 468/549 = 85.2%   chunk F1 0.892
health 402:                   exact 322/402 = 80.1%   chunk F1 0.924
geography 558:                exact 447/558 = 80.1%   chunk F1 0.929
```

Tourism = 406 + 88 + 468 = 962/1,110 (86.7%); all domains = 1,731/2,070 (83.6%).
The held-out tourism set (112 USRs) was never inspected during development.

## 5. Look at the output of a few sentences

```bash
./run.sh examples/sample_10.txt
cat out/sample_10.chunks.txt
```

Each line is `sentence id: [chunk]_SUBJ [chunk] ... [verb]_ACTIVE|_PASSIVE`, for example

```
Sent_1: [moksha]_SUBJ [by visit of saptapuris] [gets]_ACTIVE
```

Compare with the gold chunks and the English reference of the same sentence in `../corpus/tourism.jsonl`
(fields `gold_chunks`, `reference`).

## 6. Check that the output comes from the USR only

The generator never reads the Hindi sentence (the `#` line). Three quick checks:

1. **Delete the Hindi line.** Copy one block of `examples/sample_10.txt` into `my.txt`, delete its `#` line, and run
   `./run.sh my.txt`. The output is unchanged.
2. **Change the tense in the USR.** In Sent_1, change `mila_22-wA_hE_1` (habitual present) to `mila_22-yA_1` (simple past)
   and run again: `[gets]` becomes `[got]`.
3. **Change the number.** Remove `pl` from the `[ne_1]` row (column 4): the plural of *saptapuris* disappears.

Any USR file in the same format can be run with `./run.sh <file>`; `./run.sh <file> <gold.tsv> <ids.txt>`
also scores it against a gold file.

## 7. Check the USRs themselves

```bash
python3 validate_usr.py ../corpus/usr_text/health_402.txt out/health_issues.csv
```

Reports missing heads, dependency cycles, missing main verbs and concepts not in the dictionary.
The released USRs pass all checks.

## 8. Where the English knowledge is

- `data/concept-to-mrs-rels.dat`: the concept dictionary (concept with sense number -> English word, MRS predicate);
  the full dictionary is also in `../dictionary/`.
- `tables/en/*.tsv`: the nine English tables (prepositions per relation, TAM, connectives, particles, word lists).
  Editing a table row changes the output without changing any code.

## 9. Other numbers in the paper

- Inter-annotator agreement (Tables 5 and 5b): `../agreement/` (annotations, results, scripts).
- Reference quality, chunks written without a draft, the language-model use case and the corpus statistics:
  `../evaluation/` (each folder has its data and script).
