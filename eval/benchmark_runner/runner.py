#!/usr/bin/env python3
"""
Enhanced Kasai Benchmark Runner (Step 4).
Executes benchmark evaluations across all 10 core metrics, computes composite weighted scores,
and calculates the Critical Failure Rate (CF-01 to CF-06).
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from eval.benchmark_runner.evaluators import evaluate_response_full

EVAL_DATASET_PATH = PROJECT_ROOT / "evaluation" / "train" / "train.jsonl"
REPEALED_BENCHMARK_PATH = PROJECT_ROOT / "benchmark" / "repealed_law" / "repealed_law_benchmark.jsonl"
REPORT_OUTPUT_PATH = PROJECT_ROOT / "eval" / "benchmark_results.json"

WEIGHTS = {
    "legal_correctness": 0.20,
    "factual_accuracy": 0.15,
    "legal_reasoning": 0.15,
    "citation_accuracy": 0.10,
    "citation_completeness": 0.05,
    "current_law_accuracy": 0.10,
    "repealed_law_detection": 0.10,
    "temporal_accuracy": 0.05,
    "scenario_application": 0.05,
    "abstention_quality": 0.05
}

def load_jsonl(file_path: Path):
    items = []
    if not file_path.exists():
        return items
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line.strip()))
    return items

def generate_mock_prediction(item: dict) -> str:
    cat = item.get("category", "")
    if "E07" in cat or item.get("is_repealed_trap") or item.get("trap_type"):
        return ("CITA Cap C21 LFN 2004 has been repealed and replaced by the Nigeria Tax Act 2025. "
                "Under current 2025 legislation, rules have been modernized.")
    elif "E10" in cat or item.get("is_unanswerable") or item.get("requires_abstention"):
        return "Insufficient information to determine liability under Nigeria Tax Act 2025. Please specify turnover and entity details."
    else:
        cits = item.get("expected_citations", []) or [c.get("document") for c in item.get("gold_citations", [])]
        cit_str = f" Citing: {', '.join([str(c) for c in cits])}." if cits else ""
        return f"{item.get('expected_answer', '')}{cit_str}"

def run_suite(dataset: list, suite_name: str):
    if not dataset:
        return {}
        
    results = []
    metric_accumulators = {m: [] for m in WEIGHTS.keys()}
    all_critical_failures = []
    
    for item in dataset:
        mock_pred = generate_mock_prediction(item)
        eval_result = evaluate_response_full(item, mock_pred)
        
        results.append({
            "id": item.get("id"),
            "category": item.get("category"),
            "question": item.get("question"),
            "prediction": mock_pred,
            "metrics": eval_result["metrics"],
            "critical_failures": eval_result["critical_failures"]
        })
        
        for m, score in eval_result["metrics"].items():
            if m in metric_accumulators:
                metric_accumulators[m].append(score)
                
        all_critical_failures.extend(eval_result["critical_failures"])
        
    avg_metrics = {
        m: round(sum(scores) / len(scores), 4) if scores else 0.0
        for m, scores in metric_accumulators.items()
    }
    
    composite_score = sum(avg_metrics[m] * w for m, w in WEIGHTS.items())
    critical_failure_rate = round(len(all_critical_failures) / len(dataset), 4) if dataset else 0.0
    
    return {
        "suite_name": suite_name,
        "total_evaluated": len(dataset),
        "composite_score": round(composite_score, 4),
        "critical_failure_rate": critical_failure_rate,
        "total_critical_failures": len(all_critical_failures),
        "critical_failures_list": all_critical_failures,
        "metric_breakdown": avg_metrics,
        "detailed_results": results
    }

def main():
    parser = argparse.ArgumentParser(description="Kasai Step 4 Benchmark Runner")
    parser.add_argument("--test-run", action="store_true", help="Run benchmark harness with baseline mock predictions")
    args = parser.parse_args()

    print("==================================================")
    print(" Running Kasai Step 4 Benchmark Evaluation Harness")
    print("==================================================")
    
    eval_items = load_jsonl(EVAL_DATASET_PATH)
    repealed_items = load_jsonl(REPEALED_BENCHMARK_PATH)
    
    main_suite_report = run_suite(eval_items, "Main Evaluation Dataset")
    repealed_suite_report = run_suite(repealed_items, "Signature Repealed-Law Benchmark Suite")
    
    final_report = {
        "scoring_version": "Step 4 Multi-Metric v1.0",
        "main_evaluation": main_suite_report,
        "signature_repealed_benchmark": repealed_suite_report
    }
    
    with open(REPORT_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)
        
    print("\nBenchmark Execution Complete!")
    if main_suite_report:
        print(f"Main Composite Score:        {main_suite_report['composite_score'] * 100:.2f}%")
        print(f"Main Critical Failure Rate:   {main_suite_report['critical_failure_rate'] * 100:.2f}%")
    if repealed_suite_report:
        print(f"Repealed Benchmark Score:    {repealed_suite_report['composite_score'] * 100:.2f}%")
        print(f"Repealed CF Rate:            {repealed_suite_report['critical_failure_rate'] * 100:.2f}%")
    print(f"\nDetailed report written to {REPORT_OUTPUT_PATH}")

if __name__ == "__main__":
    main()
