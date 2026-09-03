"""
Phase 2 preprocessing — Day 3: Validation & Statistics
(per assignment spec: Iteoluwa - REPEALED / NEGATIVE TEST DATASET, Steps 10-11)

Checks each of the 6 JSONL files for:
  - duplicate chunks (by chunk_id and by exact text)
  - empty chunks
  - malformed sections (missing required fields)
  - missing metadata
  - encoding errors
  - incorrect status (must be REPEALED / NEGATIVE_TEST)

Generates per-Act statistics and a combined validation_report.json.

Usage (from project root, after running chunk_acts.py):
    python src/preprocessing/validate_stats.py
"""
import json
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "repealed"
REPORT_PATH = DATA_DIR / "validation_report.json"

REQUIRED_FIELDS = [
    "chunk_id", "document_id", "act", "cap", "unit_type", "section",
    "section_heading", "original_effective_date", "text", "status",
    "dataset_role", "repeal_status", "replacement_legislation",
]

FILES = {
    "PITA": "pita.jsonl",
    "CITA": "cita.jsonl",
    "VATA": "vat.jsonl",
    "CGTA": "cgt.jsonl",
    "PPTA": "ppt.jsonl",
    "SDA": "stamp_duties.jsonl",
}


def load_jsonl(path: Path) -> list[dict]:
    records = []
    errors = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                errors.append(f"line {lineno}: {e}")
    return records, errors


def validate_act(short: str, records: list[dict], decode_errors: list[str]) -> dict:
    issues = {
        "encoding_errors": decode_errors,
        "empty_chunks": [],
        "malformed_sections": [],
        "missing_metadata_fields": [],
        "incorrect_status": [],
        "duplicate_chunk_ids": [],
        "duplicate_text": [],
    }

    chunk_id_counts = Counter(r.get("chunk_id") for r in records)
    text_counts = Counter(r.get("text", "").strip() for r in records)

    for r in records:
        cid = r.get("chunk_id", "<missing>")

        if not r.get("text") or not r["text"].strip():
            issues["empty_chunks"].append(cid)

        missing = [f for f in REQUIRED_FIELDS if f not in r]
        if missing:
            issues["missing_metadata_fields"].append({cid: missing})

        if not r.get("section") or not r.get("document_id"):
            issues["malformed_sections"].append(cid)

        if r.get("status") != "REPEALED" or r.get("dataset_role") != "NEGATIVE_TEST":
            issues["incorrect_status"].append(cid)

        if chunk_id_counts[cid] > 1 and cid not in issues["duplicate_chunk_ids"]:
            issues["duplicate_chunk_ids"].append(cid)

        txt = r.get("text", "").strip()
        if text_counts[txt] > 1 and txt not in [d[:60] for d in issues["duplicate_text"]]:
            issues["duplicate_text"].append(txt[:60] + "...")

    stats = {
        "total_chunks": len(records),
        "sections": sum(1 for r in records if r.get("unit_type") == "section"),
        "schedules": sum(1 for r in records if r.get("unit_type") == "schedule"),
        "parts_covered": sorted(set(r["part"] for r in records if r.get("part")),
                                 key=lambda x: x),
        "avg_text_length_chars": (
            round(sum(len(r.get("text", "")) for r in records) / len(records), 1)
            if records else 0
        ),
        "min_text_length_chars": min((len(r.get("text", "")) for r in records), default=0),
        "max_text_length_chars": max((len(r.get("text", "")) for r in records), default=0),
    }

    issue_count = sum(
        len(v) if isinstance(v, list) else 0 for v in issues.values()
    )

    return {
        "act": short,
        "status": "PASS" if issue_count == 0 else "ISSUES_FOUND",
        "issue_count": issue_count,
        "issues": issues,
        "stats": stats,
    }


def main():
    report = {}
    print(f"{'Act':<10} {'Chunks':<8} {'Status':<15} {'Issues'}")
    for short, fname in FILES.items():
        path = DATA_DIR / fname
        if not path.exists():
            print(f"{short:<10} {'-':<8} {'FILE_MISSING':<15} run chunk_acts.py first")
            report[short] = {"status": "FILE_MISSING"}
            continue
        records, decode_errors = load_jsonl(path)
        result = validate_act(short, records, decode_errors)
        report[short] = result
        print(f"{short:<10} {result['stats']['total_chunks']:<8} {result['status']:<15} {result['issue_count']}")

    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nFull report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
