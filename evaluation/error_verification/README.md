# Double-annotated verification of grammatical and pragmatic translation errors

Five systems (Google Translate, IndicTrans2, gpt-oss-120b, Gemma 3 4B, Ministral 14B) translated the 2,071 Hindi sentences
of the corpus. Rules over the gold USR, the reference and the output proposed error candidates for tense, aspect, modality
and number (L2), semantic relations (L3), discourse connectives (L4), the speaker's view: focus particles, deixis and
honorifics (L5), and sentence type (L6). Every candidate was judged twice, independently and blind, by two trained
annotators against the Hindi sentence; disagreements were decided jointly by both annotators under the supervision of an
expert, with a recorded reason. Candidates concerning negation were decided by the expert.

| File | Contents |
|---|---|
| `candidates.tsv` | 1,251 candidates: domain, sentence id, system, layer, error type, Hindi, reference, output, claimed error |
| `judgements.tsv` | first and second judgement, final label and the source of the final label |
| `adjudication.tsv` | 359 adjudicated disagreements: decision and the reason recorded by the annotators (verbatim) |
| `results/` | precision by layer and system, agreement, error rates with Wilson intervals and McNemar tests, causes of disagreement |
| `scripts/` | the scripts that computed the results (paths refer to the authors' working copy) |

Labels: `error` = the claimed error is right for the output; `not an error` = the output expresses the element (also by
another word or construction) or the claim does not apply. Sentence ids refer to `corpus/`. Two candidates have no final
label. Changes of voice (427 candidates) are not included; they were analysed separately.
