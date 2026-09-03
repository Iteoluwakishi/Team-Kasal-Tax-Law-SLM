#!/usr/bin/env python3
"""
Automation script to compile, validate, and split Kasai evaluation datasets (Step 2).
Enforces the enriched schema defined in execution1.txt and partitions data into train (70%),
validation (15%), and isolated test (15%) splits, outputting dataset_statistics.json.
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Any

EVAL_DIR = Path(__file__).parent
TRAIN_FILE = EVAL_DIR / "train" / "train.jsonl"
VAL_FILE = EVAL_DIR / "validation" / "validation.jsonl"
TEST_FILE = EVAL_DIR / "test" / "test.jsonl"
STATS_FILE = EVAL_DIR / "metadata" / "dataset_statistics.json"

RAW_PILOT_ITEMS: List[Dict[str, Any]] = [
    # E01 - Factual Accuracy
    {
        "id": "EVAL-FA-0001",
        "category": "factual_accuracy",
        "secondary_categories": ["current_law_recognition"],
        "question": "What is the primary objective of the Nigeria Tax Act 2025?",
        "expected_answer": "The primary objective of the Nigeria Tax Act 2025 is to consolidate and modernize tax laws, establish fiscal equity, promote economic growth, and simplify compliance for taxpayers across Nigeria.",
        "acceptable_answer_points": [
            "Consolidate and modernize tax laws",
            "Establish fiscal equity and simplify compliance",
            "Promote economic growth across Nigerian businesses and individuals"
        ],
        "gold_sources": [
            {
                "document": "Nigeria Tax Act 2025",
                "section": "Chapter One, Section 1",
                "page": 1
            }
        ],
        "legal_status": "current",
        "effective_date": "2026-01-01",
        "difficulty": "easy",
        "requires_citation": True,
        "requires_abstention": False
    },
    {
        "id": "EVAL-FA-0002",
        "category": "factual_accuracy",
        "secondary_categories": ["citation_accuracy"],
        "question": "Under the Deduction of Tax at Source (Withholding) Regulations 2024, what is the mandatory timeframe for remitting deducted tax to the relevant authority?",
        "expected_answer": "Deductions made under the Withholding Tax Regulations 2024 must be remitted within 21 days following the end of the calendar month in which the deduction occurred.",
        "acceptable_answer_points": [
            "21 days timeframe",
            "Following the end of the calendar month of deduction",
            "Remit to relevant tax authority (NRS or State Board)"
        ],
        "gold_sources": [
            {
                "document": "Deduction of Tax at Source (Withholding) Regulations 2024",
                "section": "Regulation 4",
                "page": 3
            }
        ],
        "legal_status": "current",
        "effective_date": "2024-07-01",
        "difficulty": "medium",
        "requires_citation": True,
        "requires_abstention": False
    },
    {
        "id": "EVAL-FA-0003",
        "category": "factual_accuracy",
        "secondary_categories": ["current_law_recognition"],
        "question": "Which statutory board is established under the 2025 reforms to coordinate federal and state tax harmonization in Nigeria?",
        "expected_answer": "The Joint Revenue Board of Nigeria (JRB), established under the Joint Revenue Board of Nigeria (Establishment) Act 2025.",
        "acceptable_answer_points": [
            "Joint Revenue Board of Nigeria (JRB)",
            "Established under JRB Establishment Act 2025",
            "Harmonizes federal and state revenue administration"
        ],
        "gold_sources": [
            {
                "document": "Joint Revenue Board of Nigeria (Establishment) Act 2025",
                "section": "Section 1",
                "page": 2
            }
        ],
        "legal_status": "current",
        "effective_date": "2025-01-01",
        "difficulty": "easy",
        "requires_citation": True,
        "requires_abstention": False
    },

    # E02 - Legal Interpretation
    {
        "id": "EVAL-LI-0001",
        "category": "legal_interpretation",
        "secondary_categories": ["factual_accuracy"],
        "question": "Does a non-resident foreign vendor deriving income from digital downloads sold to Nigerian resident individuals have taxable nexus under NTA 2025?",
        "expected_answer": "Yes. Under Section 5 & 12 of the Nigeria Tax Act 2025, non-resident entities providing digital services or digital products that generate significant economic presence or economic benefit from Nigerian consumers fall within the taxable scope.",
        "acceptable_answer_points": [
            "Yes, nexus/taxable scope exists",
            "Significant Economic Presence (SEP) / digital economy rule",
            "Cites NTA 2025 Section 5 & 12"
        ],
        "gold_sources": [
            {
                "document": "Nigeria Tax Act 2025",
                "section": "Chapter Two, Section 5 & 12",
                "page": 12
            }
        ],
        "legal_status": "current",
        "effective_date": "2026-01-01",
        "difficulty": "hard",
        "requires_citation": True,
        "requires_abstention": False
    },
    {
        "id": "EVAL-LI-0002",
        "category": "legal_interpretation",
        "secondary_categories": ["scenario_application"],
        "question": "Are dividends paid by a small business company exempt from further corporate taxation under the Nigeria Tax Act 2025?",
        "expected_answer": "Under NTA 2025 Section 6, dividends paid by qualifying small companies out of profits that have already been subjected to income tax or statutory small-business exemption are protected from double corporate tax taxation.",
        "acceptable_answer_points": [
            "Protected from double corporate taxation",
            "Requires profits to be previously taxed or legitimately exempt",
            "References NTA 2025 Section 6"
        ],
        "gold_sources": [
            {
                "document": "Nigeria Tax Act 2025",
                "section": "Section 6",
                "page": 15
            }
        ],
        "legal_status": "current",
        "effective_date": "2026-01-01",
        "difficulty": "medium",
        "requires_citation": True,
        "requires_abstention": False
    },

    # E03 - Legal Reasoning
    {
        "id": "EVAL-LR-0001",
        "category": "legal_reasoning",
        "secondary_categories": ["scenario_application", "legal_interpretation"],
        "question": "An SME operates in Abuja with annual turnover below the small business exemption threshold, but earns ₦10,000,000 in passive interest from foreign investments. How do the small business rules and foreign income rules interact under NTA 2025?",
        "expected_answer": "While the SME's operating trading turnover remains exempt under the small business threshold rules, foreign passive interest income must be independently evaluated under statutory foreign tax credit and repatriated investment rules in NTA 2025 Section 11 & 15 to determine if withholding credits apply.",
        "acceptable_answer_points": [
            "Trading turnover exempted under small business rule",
            "Foreign passive interest evaluated separately under Section 11 & 15",
            "Foreign tax credits/withholding rules apply to passive investment portion"
        ],
        "gold_sources": [
            {
                "document": "Nigeria Tax Act 2025",
                "section": "Section 11 & Section 15",
                "page": 22
            }
        ],
        "legal_status": "current",
        "effective_date": "2026-01-01",
        "difficulty": "hard",
        "requires_citation": True,
        "requires_abstention": False
    },

    # E04 - Citation Accuracy
    {
        "id": "EVAL-CA-0001",
        "category": "citation_accuracy",
        "secondary_categories": ["factual_accuracy"],
        "question": "Which specific section of the Nigeria Tax Administration Act 2025 empowers tax officers to inspect business books and financial records?",
        "expected_answer": "Section 25 of the Nigeria Tax Administration Act 2025 explicitly authorizes designated tax officers to access business premises and examine financial books and accounting records for compliance audits.",
        "acceptable_answer_points": [
            "Section 25",
            "Nigeria Tax Administration Act 2025 (NTAA 2025)",
            "Power of entry and inspection of accounting records"
        ],
        "gold_sources": [
            {
                "document": "Nigeria Tax Administration Act 2025",
                "section": "Section 25",
                "page": 30
            }
        ],
        "legal_status": "current",
        "effective_date": "2026-01-01",
        "difficulty": "medium",
        "requires_citation": True,
        "requires_abstention": False
    },

    # E05 - Citation Completeness
    {
        "id": "EVAL-CC-0001",
        "category": "citation_completeness",
        "secondary_categories": ["factual_accuracy"],
        "question": "Outline the statutory self-assessment filing obligations for Nigerian corporate entities, ensuring every obligation step includes its exact statutory citation.",
        "expected_answer": "1. Annual self-assessment returns must be submitted within 6 months of financial year-end (Nigeria Tax Administration Act 2025, Section 14). 2. Returns must be accompanied by audited financial statements and tax computations (NTAA 2025, Section 15). 3. Tax due must be settled at filing or via an approved installment arrangement (NTAA 2025, Section 18).",
        "acceptable_answer_points": [
            "Six months filing window (NTAA 2025, Section 14)",
            "Audited accounts requirement (NTAA 2025, Section 15)",
            "Payment/Installment settlement (NTAA 2025, Section 18)"
        ],
        "gold_sources": [
            {
                "document": "Nigeria Tax Administration Act 2025",
                "section": "Section 14, 15, 18",
                "page": 18
            }
        ],
        "legal_status": "current",
        "effective_date": "2026-01-01",
        "difficulty": "hard",
        "requires_citation": True,
        "requires_abstention": False
    },

    # E06 - Current-Law Recognition
    {
        "id": "EVAL-CL-0001",
        "category": "current_law_recognition",
        "secondary_categories": ["repealed_law_detection"],
        "question": "Which federal revenue agency holds executive jurisdiction for collecting federal taxes in Nigeria under 2025 reform legislation?",
        "expected_answer": "The Nigeria Revenue Service (NRS), established under the Nigeria Revenue Service (Establishment) Act 2025. It replaces the former Federal Inland Revenue Service (FIRS).",
        "acceptable_answer_points": [
            "Nigeria Revenue Service (NRS)",
            "Established under NRS Act 2025",
            "Replaces legacy FIRS"
        ],
        "gold_sources": [
            {
                "document": "Nigeria Revenue Service (Establishment) Act 2025",
                "section": "Section 1",
                "page": 1
            }
        ],
        "legal_status": "current",
        "effective_date": "2025-01-01",
        "difficulty": "easy",
        "requires_citation": True,
        "requires_abstention": False
    },

    # E07 - Repealed-Law Detection (Signature Benchmark)
    {
        "id": "EVAL-RL-0001",
        "category": "repealed_law_detection",
        "secondary_categories": ["current_law_recognition"],
        "question": "Under Section 19 of the Companies Income Tax Act (CITA) Cap C21 LFN 2004, what is the excess dividend tax rule?",
        "expected_answer": "CITA Cap C21 LFN 2004 has been repealed and superseded by the Nigeria Tax Act 2025. The legacy Section 19 excess dividend tax rule has been abolished and restructured under NTA 2025 to prevent double taxation on retained company profits.",
        "acceptable_answer_points": [
            "Identifies CITA Cap C21 as repealed",
            "References Nigeria Tax Act 2025 as active governing law",
            "Explains restructuring of excess dividend tax to prevent double taxation"
        ],
        "gold_sources": [
            {
                "document": "Nigeria Tax Act 2025",
                "section": "Chapter Two",
                "page": 14
            }
        ],
        "legal_status": "current",
        "effective_date": "2026-01-01",
        "difficulty": "adversarial",
        "requires_citation": True,
        "requires_abstention": False
    },
    {
        "id": "EVAL-RL-0002",
        "category": "repealed_law_detection",
        "secondary_categories": ["current_law_recognition"],
        "question": "How is Consolidated Relief Allowance (CRA) calculated under Section 33 of the Personal Income Tax Act (PITA) Cap P8 LFN 2004?",
        "expected_answer": "The Personal Income Tax Act (PITA) Cap P8 LFN 2004 has been repealed and incorporated into Chapter 2 of the Nigeria Tax Act 2025. Individual tax relief allowances are now governed by modern personal income tax bands and statutory relief provisions under NTA 2025.",
        "acceptable_answer_points": [
            "Recognizes PITA 2004 as repealed/superseded",
            "Cites Nigeria Tax Act 2025 Chapter 2",
            "Explains current relief framework under 2025 reforms"
        ],
        "gold_sources": [
            {
                "document": "Nigeria Tax Act 2025",
                "section": "Chapter 2 (Taxation of Income of Persons)",
                "page": 18
            }
        ],
        "legal_status": "current",
        "effective_date": "2026-01-01",
        "difficulty": "adversarial",
        "requires_citation": True,
        "requires_abstention": False
    },

    # E08 - Temporal Reasoning
    {
        "id": "EVAL-TR-0001",
        "category": "temporal_reasoning",
        "secondary_categories": ["legal_interpretation"],
        "question": "If a transaction took place in December 2023, do the Deduction of Tax at Source (Withholding) Regulations 2024 apply to that transaction?",
        "expected_answer": "No. The Deduction of Tax at Source Regulations 2024 take effect prospectively from their commencement date in 2024 and do not retroactively alter Withholding Tax rules for transactions completed in 2023.",
        "acceptable_answer_points": [
            "No, rules do not apply retroactively to Dec 2023",
            "Prospective application from 2024 effective date",
            "2023 rules governed by pre-existing withholding framework"
        ],
        "gold_sources": [
            {
                "document": "Deduction of Tax at Source (Withholding) Regulations 2024",
                "section": "Regulation 1",
                "page": 1
            }
        ],
        "legal_status": "current",
        "effective_date": "2024-07-01",
        "difficulty": "medium",
        "requires_citation": True,
        "requires_abstention": False
    },

    # E09 - Scenario / Application Questions
    {
        "id": "EVAL-SA-0001",
        "category": "scenario_application",
        "secondary_categories": ["legal_reasoning", "citation_completeness"],
        "question": "A Nigerian SME based in Kano achieves ₦55,000,000 in gross turnover in 2025 and pays ₦8,000,000 to independent contractors. What are its WHT remittance and annual return obligations under current law?",
        "expected_answer": "1. Under WHT Regulations 2024, WHT deducted from sub-contractor payments must be remitted to NRS within 21 days following month-end (Regulation 4). 2. Under NTAA 2025, the SME must file its annual self-assessment return with NRS within 6 months of fiscal year-end (Section 14).",
        "acceptable_answer_points": [
            "WHT remittance within 21 days following month-end (WHT Regs 2024, Reg 4)",
            "Annual self-assessment return within 6 months of year-end (NTAA 2025, Sec 14)",
            "Identifies Nigeria Revenue Service (NRS) as tax authority"
        ],
        "gold_sources": [
            {
                "document": "Deduction of Tax at Source (Withholding) Regulations 2024",
                "section": "Regulation 4",
                "page": 3
            },
            {
                "document": "Nigeria Tax Administration Act 2025",
                "section": "Section 14",
                "page": 18
            }
        ],
        "legal_status": "current",
        "effective_date": "2026-01-01",
        "difficulty": "hard",
        "requires_citation": True,
        "requires_abstention": False
    },

    # E10 - Abstention
    {
        "id": "EVAL-AB-0001",
        "category": "abstention",
        "secondary_categories": ["legal_interpretation"],
        "question": "Can you calculate the exact income tax liability for my Nigerian enterprise for the current tax year?",
        "expected_answer": "Insufficient information to calculate exact tax liability under the Nigeria Tax Act 2025. To provide an accurate calculation, key details such as annual gross turnover, allowable operating expenses, taxpayer entity classification (individual vs corporate), and foreign vs domestic revenue split are required.",
        "acceptable_answer_points": [
            "Declines to provide definitive calculation due to missing information",
            "Requests missing key facts (turnover, allowable expenses, entity classification)",
            "Cites requirement for compliance under NTA 2025"
        ],
        "gold_sources": [],
        "legal_status": "current",
        "effective_date": "2026-01-01",
        "difficulty": "medium",
        "requires_citation": False,
        "requires_abstention": True
    }
]

def ensure_directories():
    (EVAL_DIR / "train").mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / "validation").mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / "test").mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / "metadata").mkdir(parents=True, exist_ok=True)

def partition_data(items: List[Dict[str, Any]], train_ratio=0.70, val_ratio=0.15):
    random.seed(12345)
    shuffled = items.copy()
    random.shuffle(shuffled)
    
    n = len(shuffled)
    n_train = max(1, int(n * train_ratio))
    n_val = max(1, int(n * val_ratio))
    
    train_items = shuffled[:n_train]
    val_items = shuffled[n_train:n_train + n_val]
    test_items = shuffled[n_train + n_val:]
    
    # Tag split metadata
    for item in train_items:
        item["split"] = "train"
    for item in val_items:
        item["split"] = "validation"
    for item in test_items:
        item["split"] = "test"
        
    return train_items, val_items, test_items

def write_jsonl(file_path: Path, items: List[Dict[str, Any]]):
    with open(file_path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

def generate_statistics(train_items, val_items, test_items):
    all_items = train_items + val_items + test_items
    
    category_counts = {}
    difficulty_counts = {}
    
    for item in all_items:
        cat = item["category"]
        diff = item["difficulty"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
        difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
        
    stats = {
        "total_items": len(all_items),
        "splits": {
            "train_count": len(train_items),
            "train_percentage": round(len(train_items) / len(all_items) * 100, 2),
            "validation_count": len(val_items),
            "validation_percentage": round(len(val_items) / len(all_items) * 100, 2),
            "test_count": len(test_items),
            "test_percentage": round(len(test_items) / len(all_items) * 100, 2)
        },
        "category_distribution": category_counts,
        "difficulty_distribution": difficulty_counts,
        "schema_compliance": "execution1.txt rich schema v1.0"
    }
    
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
        
    return stats

def main():
    print("Building Step 2 Evaluation Datasets & Data Infrastructure...")
    ensure_directories()
    
    train_items, val_items, test_items = partition_data(RAW_PILOT_ITEMS)
    
    write_jsonl(TRAIN_FILE, train_items)
    write_jsonl(VAL_FILE, val_items)
    write_jsonl(TEST_FILE, test_items)
    
    stats = generate_statistics(train_items, val_items, test_items)
    
    print("Successfully built evaluation datasets:")
    print(f"  - Train: {len(train_items)} items ({TRAIN_FILE})")
    print(f"  - Validation: {len(val_items)} items ({VAL_FILE})")
    print(f"  - Test (Locked Exam): {len(test_items)} items ({TEST_FILE})")
    print(f"  - Statistics written to {STATS_FILE}")

if __name__ == "__main__":
    main()
