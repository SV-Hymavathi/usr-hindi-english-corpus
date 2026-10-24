# Telugu USRs

The first 250 USR units of the tourism corpus were translated into Telugu; every translation was checked and, where
needed, corrected by a native speaker. A Telugu USR was built for each unit: it keeps the structure of the Hindi USR
and replaces the Hindi layers with Telugu ones (Telugu concepts in case-sensitive WX with sense numbers, Telugu TAM
labels and particles).

| File | Content |
|---|---|
| `te250_translations.tsv` | id, Hindi, English reference, machine Telugu, checked Telugu (gold), changed, check status |
| `te_usr_250.txt` | the 250 Telugu USRs (the `#` line is the checked Telugu sentence) |
| `te_dictionary.tsv` | the 586 Telugu concepts: WX concept, Telugu, English sense, aligned Hindi concept |
| `te250_results.txt` | English chunks from the Hindi and from the Telugu USR for every unit, with the gold chunks |
| `RESULTS.md` | summary: identical output for 240/250; exact match 219/250 (Hindi) and 211/250 (Telugu) |
| `build/` | alignment files and scripts used to build the Telugu USRs (documentation; they use the project's internal paths) |

The Telugu rule layer of the generator is in `../usr2chunk/`: `generate_te2en.py`, `tables/te/` and
`data/te/concept-te-en.dat`. `generate.py` and the English tables are the same as for Hindi.

Generate English chunks from the Telugu USRs (Linux or WSL, with `lt-proc` installed):

```bash
cd ../usr2chunk
python3 generate_te2en.py data/te/te_usr_250.txt
```
