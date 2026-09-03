# Kasai Evaluation Data Infrastructure (Step 2)

This directory contains the structured evaluation datasets, split partitions, and enriched metadata for **Kasai** (Nigerian Tax Law Small Language Model & RAG System).

---

## 📂 Directory Layout

```text
evaluation/
├── README.md                     # Dataset architecture & ground-truth provenance guide
├── build_evaluation_datasets.py  # Automation script to compile, validate, and split datasets
├── metadata/
│   ├── categories.json           # 10-category target matrix & question type definitions
│   ├── sources.json              # Provenance registry of active 2024/2025 acts & repealed laws
│   └── dataset_statistics.json   # Split distribution, difficulty breakdown, and dataset stats
├── train/
│   └── train.jsonl               # 70% split evaluation dataset
├── validation/
│   └── validation.jsonl          # 15% split evaluation dataset
└── test/
    └── test.jsonl                # 15% split locked benchmark test dataset
```

---

## 📐 Evaluation Entry Schema

All evaluation datasets (`train.jsonl`, `validation.jsonl`, `test.jsonl`) strictly adhere to the enriched JSONL schema defined in `execution1.txt`:

```json
{
  "id": "EVAL-RL-0001",
  "category": "repealed_law_detection",
  "secondary_categories": ["current_law_recognition"],
  "question": "Under Section 19 of CITA Cap C21 LFN 2004, what is the excess dividend tax rule?",
  "expected_answer": "CITA Cap C21 LFN 2004 has been repealed and replaced by the Nigeria Tax Act 2025...",
  "acceptable_answer_points": [
    "Identifies CITA as repealed",
    "References Nigeria Tax Act 2025",
    "Explains modern retained earnings tax treatment"
  ],
  "gold_sources": [
    {
      "document": "Nigeria Tax Act 2025",
      "section": "Chapter 2",
      "page": 14
    }
  ],
  "legal_status": "current",
  "effective_date": "2026-01-01",
  "difficulty": "adversarial",
  "requires_citation": true,
  "requires_abstention": false
}
```

---

## 🔒 Data Isolation & Leakage Prevention Rules

1. **No Memorization Overlap**: Test evaluation questions must be independently derived formulations from legal sources and never duplicate training questions verbatim.
2. **Locked Test Set**: `test/test.jsonl` is strictly isolated from model training, prompt context examples, or fine-tuning datasets.
3. **No Near-Duplicates**: Automated similarity checks prevent paraphrased questions from leaking between `train` and `test` splits.
