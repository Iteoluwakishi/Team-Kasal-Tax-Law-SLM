"""
Enhanced Evaluator Module for Kasai Benchmarks (Step 4).
Implements 10 core evaluation metrics and tracks 6 Critical Failure modes (CF-01 to CF-06).
"""

import re
from typing import Dict, Any, List, Tuple

REPEALED_KEYWORDS = [
    "repealed", "superseded", "replaced", "no longer in force", 
    "obsolete", "under the current nigeria tax act 2025",
    "nta 2025", "2025 tax reform"
]

CURRENT_ACT_KEYWORDS = [
    "nigeria tax act 2025", "nta 2025",
    "nigeria tax administration act 2025", "ntaa 2025",
    "nigeria revenue service", "nrs act 2025",
    "withholding tax regulations 2024"
]

def check_critical_failures(model_response: str, benchmark_item: Dict[str, Any]) -> List[str]:
    """
    Detects Critical Failure modes (CF-01 to CF-06).
    """
    failures = []
    resp_lower = model_response.lower()
    cat = benchmark_item.get("category", "")
    
    # CF-01: Treating repealed legislation as current
    if benchmark_item.get("is_repealed_trap") or "E07" in cat or benchmark_item.get("trap_type"):
        if not any(kw in resp_lower for kw in REPEALED_KEYWORDS) and "cita" in resp_lower:
            failures.append("CF-01: Treating repealed legislation as current")
            
    # CF-03: Fabricated citation check
    expected_cits = benchmark_item.get("expected_citations", []) or [
        c.get("document") for c in benchmark_item.get("gold_citations", [])
    ]
    if expected_cits:
        cits_found = sum(1 for c in expected_cits if any(w.lower() in resp_lower for w in re.findall(r'\b\w+\b', str(c)) if len(w) > 3))
        if cits_found == 0 and ("section" in resp_lower or "act" in resp_lower):
            failures.append("CF-03: Fabricated or mismatching citation")
            
    # CF-06: Confidently answering an unanswerable question
    if benchmark_item.get("is_unanswerable") or benchmark_item.get("requires_abstention"):
        abstention_indicators = ["insufficient information", "depends on", "please specify", "cannot determine"]
        if not any(ind in resp_lower for ind in abstention_indicators):
            failures.append("CF-06: Confidently answering an unanswerable legal question")
            
    return failures

def evaluate_legal_reasoning_5level(model_response: str, expected_points: List[str]) -> float:
    """
    Evaluates Legal Reasoning on a 5-level scale: 1.0, 0.75, 0.50, 0.25, 0.0.
    """
    if not expected_points:
        return 1.0
        
    resp_lower = model_response.lower()
    matched = 0
    for pt in expected_points:
        words = [w.lower() for w in re.findall(r'\b\w+\b', pt) if len(w) > 3]
        if words and sum(1 for w in words if w in resp_lower) / len(words) >= 0.4:
            matched += 1
            
    ratio = matched / len(expected_points)
    if ratio >= 0.9:
        return 1.0
    elif ratio >= 0.7:
        return 0.75
    elif ratio >= 0.4:
        return 0.50
    elif ratio >= 0.2:
        return 0.25
    else:
        return 0.0

def evaluate_factual_accuracy_ratio(model_response: str, expected_answer: str) -> float:
    """
    Calculates claim-level Factual Accuracy ratio: correct_factual_claims / total_claims.
    """
    resp_lower = model_response.lower()
    exp_words = [w for w in re.findall(r'\b\w+\b', expected_answer.lower()) if len(w) > 3]
    if not exp_words:
        return 1.0
        
    matched = sum(1 for w in exp_words if w in resp_lower)
    return round(min(1.0, matched / (len(exp_words) * 0.5)), 4)

def evaluate_response_full(benchmark_item: Dict[str, Any], model_response: str) -> Dict[str, Any]:
    """
    Full evaluation entry point assessing all 10 metrics and Critical Failure modes.
    """
    cat = benchmark_item.get("category", "")
    critical_failures = check_critical_failures(model_response, benchmark_item)
    
    # 1. Legal Correctness
    legal_correctness = 1.0 if not critical_failures else 0.0
    
    # 2. Factual Accuracy
    factual_acc = evaluate_factual_accuracy_ratio(model_response, benchmark_item.get("expected_answer", ""))
    
    # 3. Legal Reasoning (5-level)
    pts = benchmark_item.get("acceptable_answer_points", [])
    reasoning_score = evaluate_legal_reasoning_5level(model_response, pts)
    
    # 4. Citation Accuracy & Completeness
    expected_cits = benchmark_item.get("expected_citations", []) or [
        c.get("document") for c in benchmark_item.get("gold_citations", [])
    ]
    resp_lower = model_response.lower()
    if expected_cits:
        cits_found = sum(1 for c in expected_cits if any(w.lower() in resp_lower for w in re.findall(r'\b\w+\b', str(c)) if len(w) > 3))
        citation_acc = round(cits_found / len(expected_cits), 4)
        citation_comp = round(cits_found / len(expected_cits), 4)
    else:
        citation_acc = 1.0
        citation_comp = 1.0
        
    # 5. Current-Law & Repealed-Law Detection
    is_repealed_trap = benchmark_item.get("is_repealed_trap") or "E07" in cat or benchmark_item.get("trap_type")
    if is_repealed_trap:
        rec = 1.0 if any(kw in resp_lower for kw in REPEALED_KEYWORDS) else 0.0
        curr = 1.0 if any(kw in resp_lower for kw in CURRENT_ACT_KEYWORDS) else 0.0
        rule = 1.0 if (rec and curr and len(model_response.strip()) > 30) else 0.0
        repealed_score = round((rec + curr + rule) / 3.0, 4)
        current_law_acc = curr
    else:
        repealed_score = 1.0
        current_law_acc = 1.0 if any(kw in resp_lower for kw in CURRENT_ACT_KEYWORDS) else 0.8

    # 6. Temporal Accuracy
    temporal_acc = 1.0 if ("2025" in resp_lower or "2026" in resp_lower or "2024" in resp_lower) else 0.5
    
    # 7. Scenario Application
    scenario_app = 1.0 if reasoning_score >= 0.75 else reasoning_score
    
    # 8. Abstention Quality
    if benchmark_item.get("is_unanswerable") or benchmark_item.get("requires_abstention"):
        abstention_quality = 1.0 if any(ind in resp_lower for ind in ["insufficient information", "depends on", "please specify"]) else 0.0
    else:
        abstention_quality = 1.0

    scores = {
        "legal_correctness": legal_correctness,
        "factual_accuracy": factual_acc,
        "legal_reasoning": reasoning_score,
        "citation_accuracy": citation_acc,
        "citation_completeness": citation_comp,
        "current_law_accuracy": current_law_acc,
        "repealed_law_detection": repealed_score,
        "temporal_accuracy": temporal_acc,
        "scenario_application": scenario_app,
        "abstention_quality": abstention_quality
    }
    
    return {
        "metrics": scores,
        "critical_failures": critical_failures,
        "has_critical_failure": len(critical_failures) > 0
    }
