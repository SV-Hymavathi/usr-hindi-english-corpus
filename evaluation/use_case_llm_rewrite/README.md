# Experiment 3 – generator chunks → one fluent English sentence

Input: the rule-based generator's (usr2chunk) chunks for all 2,071 USRs (tourism 1,111, health 402, geography 558),
file `exp3_input.tsv` (domain, ID, chunks). The LLMs only see the chunks (not the Hindi, not the reference).
Models: Groq `openai/gpt-oss-120b`, Mistral `ministral-14b-latest`, Ollama `gemma3:4b` (same as Experiment 1, temperature 0).
Keys: read from `../exp1/keys.json` (nothing to add). Baseline: `outputs/usr2chunk_literal.tsv` = the chunks written as a sentence.

## Prompt (fixed for every sentence and model; see config.json)
System: You are an English language editor ... You never change the meaning: you do not add, remove, replace or explain any information.
User: rewrite the chunks as ONE grammatical, fluent sentence. MAY reorder, add articles / function words, fix word forms.
MUST NOT add information, remove information, replace words, change/translate/replace names, change numbers,
change voice / tense / negation / sentence type, drop the connective, use markdown / notes / alternatives.

## Run (WSL)
    cd evaluation/use_case_llm_rewrite
    python3 run_exp3.py              # all three models in parallel; Ctrl+C any time
    python3 run_exp3.py --status     # progress
    python3 collect_exp3.py          # -> exp3_outputs.xlsx (one sheet per model)
Next day: run `python3 run_exp3.py` again; each model continues where it stopped (daily limits as in Experiment 1).

## Analysis (when the models have finished)
    python3 final_analysis.py        # -> exp3_final_error_analysis.xlsx
Same layer-by-layer analysis as Experiment 1 (scores against the gold reference, best/worst, shared errors, one tab per layer),
with the literal generator sentence as the baseline system.
