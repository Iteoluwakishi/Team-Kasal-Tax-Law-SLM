# Kasai Baseline Evaluation Pipeline

Implements Phase 3 of the task doc: run the same benchmark against several
candidate models before picking one.

## Setup

```
pip install transformers accelerate bitsandbytes torch anthropic pyyaml
export ANTHROPIC_API_KEY=your_key_here   # only needed for the judge step
```

Some models (Gemma, Llama) are gated on Hugging Face -- log in with
`huggingface-cli login` and accept each model's license on its HF page first.

If you don't have a GPU for the 4B/7B models, either:
- run those two on Colab / a rented GPU instance, or
- point `generate_answers()` at a hosted inference endpoint instead of
  loading weights locally (the rest of the pipeline doesn't care how the
  answers were produced).

## Files

- `models.yaml` -- the five candidate models (1B -> 3B -> 3.8B -> 4B -> 7B),
  edit freely to add/remove candidates.
- `benchmark_questions.json` -- **starter set of 25 questions**, tagged by
  category (legal_accuracy, citation, current_law, repealed_law, reasoning).
  Every reference_answer/citation marked "DRAFT -- verify" needs checking
  against your Certified True Copies before you trust the score it produces.
  Expand this to 100 questions before finalizing results, pulling from your
  cleaned PITA/CITA/VAT/CGT/PPT/Stamp Duties corpus and the 2025 reform Acts.
- `run_baseline_eval.py` -- the pipeline, in three steps.

## Run it

```
python run_baseline_eval.py generate --models models.yaml --questions benchmark_questions.json
python run_baseline_eval.py judge --questions benchmark_questions.json
python run_baseline_eval.py report
```

This produces the three Phase 3/4 deliverables:
- `raw_answers/<model>.json` -- every model's raw answers (working data, keep for the record)
- `baseline_results.json`
- `model_comparison.md`

## After this

Once you have real (verified) numbers in `model_comparison.md`, move to
Phase 4: write `model_selection_report.md` justifying the pick on
performance + efficiency + deployability together, not top score alone
(see the doc's 7B-vs-3B example). Then Phase 5 training prep follows the
same doc -- LoRA/QLoRA config, small 100-500 example test run before
training on the full dataset.
