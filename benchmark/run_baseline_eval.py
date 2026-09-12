"""
Kasai Phase 3 -- Baseline Evaluation pipeline.

Runs the SAME 100 (starter: 25) benchmark questions against every candidate
model, then scores each answer, then produces model_comparison.md and
baseline_results.json as described in the Kasai task doc.

USAGE
-----
Step 1 -- generate raw answers from every candidate model (needs GPU/CPU +
          the models downloaded locally, or edit generate_answers() to call
          an API instead of loading weights locally):

    python run_baseline_eval.py generate --models models.yaml --questions benchmark_questions.json

Step 2 -- score the raw answers. Two options, no API key required for either
          unless you choose the LLM-judge one:

  2a. MANUAL scoring (recommended -- a human who knows Nigerian tax law is a
      better judge than an LLM guessing at unverified references):

      python run_baseline_eval.py export-scoring --questions benchmark_questions.json
      # -> writes scoring_template.csv. Open it in Sheets/Excel, fill in the
      #    "score" column (0-100) for every row after reading the answer.
      python run_baseline_eval.py import-scores --csv scoring_template.csv

  2b. LLM-judge scoring (uses the Anthropic API -- set ANTHROPIC_API_KEY):

      python run_baseline_eval.py judge --questions benchmark_questions.json

Step 3 -- turn the scored results into model_comparison.md:

    python run_baseline_eval.py report

Each step reads/writes plain JSON so you can inspect, fix, or manually
re-score anything between steps (e.g. if a citation reference answer turns
out to be wrong once you verify it against your Certified True Copies).

Directory layout this script produces:
    raw_answers/<model_name>.json   -- one file per model, all Q&A pairs
    baseline_results.json           -- per-model, per-category aggregate scores
    model_comparison.md             -- final markdown table for the deliverable
"""

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

QUESTIONS_DEFAULT = "benchmark_questions.json"
MODELS_DEFAULT = "models.yaml"
RAW_DIR = Path("raw_answers")
RESULTS_PATH = Path("baseline_results.json")
REPORT_PATH = Path("model_comparison.md")

CATEGORIES = ["legal_accuracy", "citation", "current_law", "repealed_law", "reasoning"]


def load_questions(path):
    with open(path) as f:
        data = json.load(f)
    return data["questions"]


def load_models_config(path):
    with open(path) as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# STEP 1: generate raw answers from each candidate model
# ---------------------------------------------------------------------------

def generate_answers(models_cfg_path, questions_path):
    """
    Loads each model with transformers and generates an answer for every
    question. Requires: pip install transformers accelerate bitsandbytes torch

    NOTE: 7B (and 4B quantized) models need a real GPU. If you don't have
    one available, swap the model-loading block below for a call to
    whatever inference endpoint you're actually using (a hosted API,
    Ollama, vLLM server, etc.) -- the rest of the pipeline (judge, report)
    doesn't care how the answers were produced, only that raw_answers/*.json
    follows the same shape.
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    cfg = load_models_config(models_cfg_path)
    questions = load_questions(questions_path)
    gen_cfg = cfg.get("generation", {})
    max_new_tokens = gen_cfg.get("max_new_tokens", 300)
    temperature = gen_cfg.get("temperature", 0.2)

    RAW_DIR.mkdir(exist_ok=True)

    for model_spec in cfg["models"]:
        name = model_spec["name"]
        hf_id = model_spec["hf_id"]
        quantize = model_spec.get("quantize", False)
        out_path = RAW_DIR / f"{name}.json"
        if out_path.exists():
            print(f"[skip] {name}: raw_answers/{name}.json already exists")
            continue

        print(f"[load] {name} ({hf_id}) quantize={quantize}")
        load_kwargs = {"device_map": "auto"}
        if quantize:
            load_kwargs["load_in_4bit"] = True
        else:
            load_kwargs["torch_dtype"] = torch.bfloat16

        try:
            tokenizer = AutoTokenizer.from_pretrained(hf_id)
            model = AutoModelForCausalLM.from_pretrained(hf_id, **load_kwargs)
        except Exception as e:
            print(f"[error] failed to load {name}: {e}", file=sys.stderr)
            continue

        answers = []
        for q in questions:
            prompt = q["question"]
            messages = [{"role": "user", "content": prompt}]
            # return_dict=True is required on recent transformers versions --
            # without it, apply_chat_template can return a plain tensor OR a
            # BatchEncoding depending on version, which breaks .shape below.
            inputs = tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                return_tensors="pt",
                return_dict=True,
            ).to(model.device)

            with torch.no_grad():
                output_ids = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=temperature,
                    do_sample=temperature > 0,
                )
            input_len = inputs["input_ids"].shape[-1]
            answer_ids = output_ids[0][input_len:]
            answer_text = tokenizer.decode(answer_ids, skip_special_tokens=True).strip()

            answers.append({
                "id": q["id"],
                "category": q["category"],
                "question": prompt,
                "model_answer": answer_text,
            })
            print(f"  {q['id']} done")

        with open(out_path, "w") as f:
            json.dump({"model": name, "hf_id": hf_id, "answers": answers}, f, indent=2)
        print(f"[saved] {out_path}")

        del model
        torch.cuda.empty_cache() if torch.cuda.is_available() else None


# ---------------------------------------------------------------------------
# STEP 2: score raw answers against reference answers with an LLM judge
# ---------------------------------------------------------------------------

JUDGE_PROMPT_TEMPLATE = """You are scoring an AI model's answer to a Nigerian tax law question for a research benchmark.

Question ({category}): {question}

Reference answer / citation (may be a draft the team is still verifying): {reference}

Model's answer: {model_answer}

Score the model's answer from 0 to 100 on correctness and completeness relative to the reference.
If the reference answer is itself marked "DRAFT -- verify", use your own knowledge of Nigerian tax law
to judge correctness, and note in "notes" that the reference needs human verification.

Respond ONLY with JSON in this exact shape, nothing else:
{{"score": <int 0-100>, "notes": "<one short sentence>"}}
"""


def judge_answers(questions_path):
    """
    Uses the Anthropic API as an LLM judge to score every raw answer.
    Requires: pip install anthropic ; export ANTHROPIC_API_KEY=...
    """
    import anthropic

    client = anthropic.Anthropic()
    questions_by_id = {q["id"]: q for q in load_questions(questions_path)}

    if not RAW_DIR.exists():
        print("No raw_answers/ directory found -- run the 'generate' step first.", file=sys.stderr)
        sys.exit(1)

    results = {}  # model_name -> category -> list of scores

    for raw_file in sorted(RAW_DIR.glob("*.json")):
        with open(raw_file) as f:
            data = json.load(f)
        model_name = data["model"]
        results[model_name] = {c: [] for c in CATEGORIES}

        for ans in data["answers"]:
            q = questions_by_id[ans["id"]]
            prompt = JUDGE_PROMPT_TEMPLATE.format(
                category=q["category"],
                question=q["question"],
                reference=q.get("reference_answer", "N/A"),
                model_answer=ans["model_answer"],
            )
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            text = resp.content[0].text.strip()
            try:
                parsed = json.loads(text)
                score = parsed["score"]
            except Exception:
                print(f"[warn] could not parse judge output for {ans['id']} ({model_name}): {text}")
                score = None

            if score is not None:
                results[model_name][ans["category"]].append(score)
            print(f"  scored {model_name} / {ans['id']} -> {score}")

    # aggregate to per-category averages
    aggregated = {}
    for model_name, by_cat in results.items():
        aggregated[model_name] = {}
        for cat, scores in by_cat.items():
            aggregated[model_name][cat] = round(sum(scores) / len(scores), 1) if scores else None

    with open(RESULTS_PATH, "w") as f:
        json.dump(aggregated, f, indent=2)
    print(f"[saved] {RESULTS_PATH}")


# ---------------------------------------------------------------------------
# STEP 2 (no API key): manual scoring via a spreadsheet
# ---------------------------------------------------------------------------

SCORING_CSV_PATH = Path("scoring_template.csv")


def export_for_manual_scoring(questions_path):
    """
    Builds one CSV with every model's answer to every question, plus a blank
    'score' column, so a human can open it in Sheets/Excel and score by hand.
    """
    import csv

    questions_by_id = {q["id"]: q for q in load_questions(questions_path)}

    if not RAW_DIR.exists():
        print("No raw_answers/ directory found -- run the 'generate' step first.", file=sys.stderr)
        sys.exit(1)

    rows = []
    for raw_file in sorted(RAW_DIR.glob("*.json")):
        with open(raw_file) as f:
            data = json.load(f)
        model_name = data["model"]
        for ans in data["answers"]:
            q = questions_by_id[ans["id"]]
            rows.append({
                "model": model_name,
                "id": ans["id"],
                "category": q["category"],
                "question": q["question"],
                "reference_answer": q.get("reference_answer", ""),
                "citation": q.get("citation", ""),
                "model_answer": ans["model_answer"],
                "score": "",       # <-- fill this in, 0-100
                "notes": "",       # <-- optional
            })

    with open(SCORING_CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"[saved] {SCORING_CSV_PATH} ({len(rows)} rows to score)")
    print("Open it in Sheets/Excel, fill in 'score' for every row, save as CSV, "
          "then run: python run_baseline_eval.py import-scores --csv scoring_template.csv")


def import_scores(csv_path):
    """
    Reads a filled-in scoring CSV (from export_for_manual_scoring) and
    aggregates it into baseline_results.json, same shape as the judge step
    produces, so 'report' works identically either way.
    """
    import csv
    from collections import defaultdict

    by_model_cat = defaultdict(lambda: defaultdict(list))
    skipped = 0

    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            score_str = row.get("score", "").strip()
            if not score_str:
                skipped += 1
                continue
            try:
                score = float(score_str)
            except ValueError:
                print(f"[warn] non-numeric score for {row['model']}/{row['id']}: {score_str!r}")
                skipped += 1
                continue
            by_model_cat[row["model"]][row["category"]].append(score)

    if skipped:
        print(f"[note] {skipped} row(s) had no/invalid score and were skipped -- "
              f"finish scoring them for a complete picture.")

    aggregated = {}
    for model_name, by_cat in by_model_cat.items():
        aggregated[model_name] = {}
        for cat in CATEGORIES:
            scores = by_cat.get(cat, [])
            aggregated[model_name][cat] = round(sum(scores) / len(scores), 1) if scores else None

    with open(RESULTS_PATH, "w") as f:
        json.dump(aggregated, f, indent=2)
    print(f"[saved] {RESULTS_PATH}")


# ---------------------------------------------------------------------------
# STEP 3: build the markdown comparison table
# ---------------------------------------------------------------------------

def build_report():
    if not RESULTS_PATH.exists():
        print("No baseline_results.json found -- run the 'judge' step first.", file=sys.stderr)
        sys.exit(1)

    with open(RESULTS_PATH) as f:
        results = json.load(f)

    header = "| Model | Legal Accuracy | Citation | Current Law | Repealed Law | Reasoning |"
    sep = "|---|---|---|---|---|---|"
    rows = [header, sep]
    for model_name, cats in results.items():
        row = f"| {model_name} " + " ".join(
            f"| {cats.get(c, '-')}% " for c in CATEGORIES
        ) + "|"
        rows.append(row)

    md = (
        "# Model Comparison -- Kasai Phase 3 Baseline\n\n"
        "Scores are LLM-judge estimates (0-100) against draft reference answers.\n"
        "**Any reference answer still marked \"DRAFT -- verify\" in benchmark_questions.json "
        "means these scores need re-checking once the team confirms ground truth against "
        "Certified True Copies.**\n\n"
        + "\n".join(rows)
        + "\n\nThese numbers are a starting point (25-question set), not final results. "
        "Expand to 100 verified questions before writing model_selection_report.md.\n"
    )
    REPORT_PATH.write_text(md)
    print(f"[saved] {REPORT_PATH}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="step", required=True)

    gen = sub.add_parser("generate", help="Generate raw answers from each candidate model")
    gen.add_argument("--models", default=MODELS_DEFAULT)
    gen.add_argument("--questions", default=QUESTIONS_DEFAULT)

    judge = sub.add_parser("judge", help="Score raw answers with an LLM judge (needs ANTHROPIC_API_KEY)")
    judge.add_argument("--questions", default=QUESTIONS_DEFAULT)

    export_sc = sub.add_parser("export-scoring", help="Export a CSV for manual scoring (no API key needed)")
    export_sc.add_argument("--questions", default=QUESTIONS_DEFAULT)

    import_sc = sub.add_parser("import-scores", help="Aggregate a filled-in manual scoring CSV")
    import_sc.add_argument("--csv", default=str(SCORING_CSV_PATH))

    sub.add_parser("report", help="Build model_comparison.md from baseline_results.json")

    args = parser.parse_args()
    if args.step == "generate":
        generate_answers(args.models, args.questions)
    elif args.step == "judge":
        judge_answers(args.questions)
    elif args.step == "export-scoring":
        export_for_manual_scoring(args.questions)
    elif args.step == "import-scores":
        import_scores(args.csv)
    elif args.step == "report":
        build_report()


if __name__ == "__main__":
    main()
