"""Annotation pipeline step 4: export legally approved records.

Reads data/annotation/candidates.jsonl and writes ONLY records whose
review.status is 'approved' to data/annotation/training_candidates.jsonl —
the file Kishi's split-building and Ak's evaluation work start from.
Everything else stays in candidates.jsonl awaiting review.

Run from the repo root:
    python src/annotation_pipeline/04_export_approved.py
"""

import json
from collections import Counter
from pathlib import Path

CANDIDATES_PATH = Path("data/annotation/candidates.jsonl")
OUT_PATH = Path("data/annotation/training_candidates.jsonl")


def main() -> None:
    approved, statuses = [], Counter()
    with open(CANDIDATES_PATH, encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            status = record.get("review", {}).get("status", "pending")
            statuses[status] += 1
            if status == "approved":
                approved.append(record)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for record in approved:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("review status counts:", dict(statuses))
    print(f"wrote {len(approved)} approved records to {OUT_PATH}")
    if statuses.get("pending"):
        print(f"note: {statuses['pending']} record(s) still awaiting legal review")


if __name__ == "__main__":
    main()
