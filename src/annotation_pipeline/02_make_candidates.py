"""Annotation pipeline step 2: merge Q&A drafts with provisions into records.

Drafts are the minimal thing an annotator (or Kishi's generator) writes —
question, answer, and classification, keyed by chunk_id:

    {"chunk_id": "nrsea_2025#000", "instruction": "...", "response": "...",
     "tax_domain": "revenue_administration", "topic": "Objective of the Act",
     "question_type": "definition", "difficulty": "easy"}

Everything else (context, source, law, section, legal_status, effective_date,
provenance, id) is filled from the provisions catalog, so provenance can never
be typed wrong by hand.

Reads every data/annotation/drafts/*.jsonl (or the file(s) given as arguments),
writes data/annotation/candidates.jsonl. Ids are assigned deterministically
per tax-domain prefix (VAT_001, CIT_002, ...), so re-running regenerates the
same ids for the same drafts.

Run from the repo root:
    python src/annotation_pipeline/02_make_candidates.py [drafts.jsonl ...]
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

PROVISIONS_PATH = Path("data/annotation/provisions.jsonl")
DRAFTS_DIR = Path("data/annotation/drafts")
OUT_PATH = Path("data/annotation/candidates.jsonl")

DOMAIN_PREFIX = {
    "company_income_tax": "CIT",
    "personal_income_tax": "PIT",
    "value_added_tax": "VAT",
    "paye": "PAYE",
    "capital_gains": "CGT",
    "petroleum_taxation": "PPT",
    "stamp_duties": "SD",
    "withholding_tax": "WHT",
    "development_levy": "DL",
    "virtual_assets": "VA",
    "tax_administration": "TAXADMIN",
    "revenue_administration": "REVADMIN",
    "general": "GEN",
}


def main() -> None:
    if not PROVISIONS_PATH.exists():
        raise SystemExit("provisions.jsonl not found — run 01_extract_provisions.py first")
    provisions = {}
    with open(PROVISIONS_PATH, encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            provisions[p["chunk_id"]] = p

    draft_files = [Path(a) for a in sys.argv[1:]] or sorted(DRAFTS_DIR.glob("*.jsonl"))
    if not draft_files:
        raise SystemExit(f"no draft files given and none found in {DRAFTS_DIR}")

    records, errors = [], []
    counters = defaultdict(int)
    for path in draft_files:
        with open(path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                draft = json.loads(line)
                where = f"{path.name}:{line_no}"
                prov = provisions.get(draft.get("chunk_id", ""))
                if prov is None:
                    errors.append(f"{where}: chunk_id {draft.get('chunk_id')!r} "
                                  "not in provisions catalog")
                    continue
                prefix = DOMAIN_PREFIX.get(draft.get("tax_domain", ""), "GEN")
                counters[prefix] += 1
                records.append(
                    {
                        "id": f"{prefix}_{counters[prefix]:03d}",
                        "instruction": draft.get("instruction", ""),
                        "context": draft.get("context") or prov["text"],
                        "response": draft.get("response", ""),
                        "source": prov["source"] or prov["law_name"],
                        "law": prov["law"],
                        "section": prov["section"],
                        "subsection": draft.get("subsection", ""),
                        "tax_domain": draft.get("tax_domain", "general"),
                        "topic": draft.get("topic", ""),
                        "question_type": draft.get("question_type", ""),
                        "difficulty": draft.get("difficulty", ""),
                        "legal_status": draft.get("legal_status") or prov["legal_status"],
                        "effective_date": prov["effective_date"],
                        "replacement_legislation": prov["replacement_legislation"],
                        "provenance": {
                            "chunk_id": prov["chunk_id"],
                            "document_id": prov["document_id"],
                            "source_file": prov["source_file"] or prov["corpus_file"],
                            "page": prov["page"],
                            "source_url": prov["source_url"],
                        },
                        "review": {"status": "pending", "reviewer": "", "notes": ""},
                    }
                )

    for e in errors:
        print("ERROR:", e)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} candidate records to {OUT_PATH} "
          f"({len(errors)} draft error(s))")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
