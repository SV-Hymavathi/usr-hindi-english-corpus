# LLM judges

Ratings of the 2,359 distinct rated outputs (both studies) by three LLM judges, run through the Groq API at temperature 0:
gpt-oss-120b (`openai/gpt-oss-120b`, low reasoning effort) and Qwen3.8 27B (`qwen/qwen3.8-27b`, no reasoning) with the English reference,
and Qwen3.8 27B without the reference. Each judge saw the Hindi sentence, (the reference,) and the output, and returned adequacy on the
annotators' 1-5 scale and yes/no for added, omitted and changed information.

- `judge_ratings.tsv`: one row per output (domain, id, system, input) with the four answers of each judge
- `scripts/run_judge.py`: the prompt and the API calls (`python3 run_judge.py gptoss|qwen|qwen_noref`); API keys are read from a local
  `keys.json` that is not part of the release
- `scripts/judge_analysis.py`: agreement with the annotators and the metrics, error detection, input route, self-preference,
  system level, selection, reference anchoring -> `results/judge_analysis.json`. It reads the segment-level human ratings and metric
  scores of `../metric_meta_evaluation/` and `../human_evaluation_study2/ratings.tsv`; set the paths at the top of the script.
