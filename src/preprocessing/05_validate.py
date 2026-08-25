"""Stage 05: Validate the processed corpus and produce statistics.

Reads the stage-04 JSONL outputs plus documents.csv and checks:
  - missing/empty required metadata fields per chunk
  - empty or suspiciously short chunks
  - exact duplicate chunk text
  - encoding problems (replacement chars, mojibake, control chars)
  - invalid page references (outside the source document's page range)
  - act section continuity (every section number present, headings attached)
  - act page coverage (no unexplained gaps between chunk start pages)
  - FAQ integrity (every question has an answer)
  - documents that were inventoried but produced no chunks

Writes:
  reports/validation_report.md   - human-readable report
  data/metadata/statistics.csv   - per-source statistics table

Exit code is non-zero if any ERROR-level issue is found (warnings pass).

Run from the repo root:
    python src/preprocessing/05_validate.py
"""

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

METADATA_CSV = Path("data/metadata/documents.csv")
JSONL_FILES = [
    Path("data/processed/current/nrsea.jsonl"),
    Path("data/processed/current/jrba.jsonl"),
    Path("data/processed/guidance/nrs_guidance.jsonl"),
]
REPORT_PATH = Path("reports/validation_report.md")
STATS_PATH = Path("data/metadata/statistics.csv")

REQUIRED_FIELDS = [
    "chunk_id", "document_id", "document_type", "legal_weight", "status",
    "document_title", "source_file", "page", "text",
]
VALID_STATUS = {"in_force", "superseded", "repealed"}
MIN_CHUNK_CHARS = 40
MOJIBAKE_RE = re.compile(r"[�]|â€|Ã.|[\x00-\x08\x0b\x0c\x0e-\x1f]")

# statistics groups per the task sheet
def source_group(chunk: dict) -> str:
    if chunk["document_id"] == "nrsea_2025":
        return "NRSEA"
    if chunk["document_id"] == "jrba_2025":
        return "JRBA"
    return {
        "circular": "Circulars",
        "faq": "FAQs",
        "notice": "Notices",
        "press_release": "Press releases",
        "news": "News",
    }.get(chunk["document_type"], "Other")


def main() -> None:
    docs = pd.read_csv(METADATA_CSV, encoding="utf-8-sig").fillna("")
    doc_meta = {row["document_id"]: row for _, row in docs.iterrows()}

    chunks = []
    for path in JSONL_FILES:
        if not path.exists():
            print(f"ERROR: missing output file {path}")
            sys.exit(1)
        with open(path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                chunk = json.loads(line)
                chunk["_file"] = f"{path.name}:{line_no}"
                chunks.append(chunk)

    errors, warnings = [], []

    # --- field completeness, chunk size, encoding, status, page ranges
    seen_hashes = {}
    for c in chunks:
        where = f"{c.get('chunk_id', '?')} ({c['_file']})"
        for field in REQUIRED_FIELDS:
            if field not in c or c[field] in ("", None):
                errors.append(f"missing field '{field}' in {where}")
        text = c.get("text", "")
        if len(text) < MIN_CHUNK_CHARS:
            errors.append(f"short/empty chunk ({len(text)} chars) in {where}")
        if MOJIBAKE_RE.search(text):
            errors.append(f"encoding artifact in {where}: "
                          f"{MOJIBAKE_RE.search(text).group()!r}")
        if c.get("status") not in VALID_STATUS:
            errors.append(f"invalid status '{c.get('status')}' in {where}")

        digest = hashlib.sha256(text.encode()).hexdigest()
        if digest in seen_hashes:
            prev_where, prev_doc = seen_hashes[digest]
            if prev_doc == c.get("document_id"):
                # same document repeating itself is a pipeline bug
                errors.append(f"duplicate text within document: {where} == {prev_where}")
            else:
                # different statutes/circulars genuinely share boilerplate
                # (e.g. identical schedule provisions in NRSEA and JRBA)
                warnings.append(f"identical text across documents: {where} == {prev_where}")
        else:
            seen_hashes[digest] = (where, c.get("document_id"))

        meta = doc_meta.get(c.get("document_id"))
        if meta is None:
            errors.append(f"document_id not in documents.csv: {where}")
        else:
            if int(c.get("page", 0)) < 1 or int(c.get("page", 0)) > int(meta["pages"]):
                errors.append(f"page {c.get('page')} outside 1..{meta['pages']} in {where}")

    # --- act-specific: section continuity, headings, page coverage
    for doc_id, name in (("nrsea_2025", "NRSEA"), ("jrba_2025", "JRBA")):
        secs = [c for c in chunks
                if c["document_id"] == doc_id and c.get("part", "").startswith("PART")]
        nums = sorted({int(c["section"]) for c in secs})
        missing = [n for n in range(nums[0], nums[-1] + 1) if n not in nums]
        if missing:
            errors.append(f"{name}: missing section numbers {missing}")
        for c in secs:
            if not c.get("heading"):
                warnings.append(f"{name} s.{c['section']}: no margin heading attached")
        doc_chunks = [c for c in chunks if c["document_id"] == doc_id]
        pages_used = sorted({int(c["page"]) for c in doc_chunks})
        gaps = [(a, b) for a, b in zip(pages_used, pages_used[1:]) if b - a > 3]
        for a, b in gaps:
            warnings.append(f"{name}: no chunk starts on pages {a + 1}-{b - 1} "
                            "(long section or lost content? verify against the PDF)")

    # --- FAQ integrity
    faq = [c for c in chunks if c["document_type"] == "faq"]
    for c in faq:
        if not re.match(r"^Q: .+\nA: .+", c["text"], re.S):
            errors.append(f"FAQ chunk without Q/A pair: {c['chunk_id']}")

    # --- inventoried documents that produced no chunks
    chunked_ids = {c["document_id"] for c in chunks}
    for doc_id, meta in doc_meta.items():
        if meta["assigned_to"] != "abdul" or doc_id in chunked_ids:
            continue
        if str(meta["has_text"]).lower() == "false":
            warnings.append(f"{doc_id}: no chunks — image-only source "
                            "(poster kept in data/raw/guidance/images/, OCR pending)")
        else:
            errors.append(f"{doc_id}: inventoried with text but produced no chunks")

    # --- statistics per source group
    groups = defaultdict(list)
    for c in chunks:
        groups[source_group(c)].append(c)
    stats_rows = []
    for group in ("NRSEA", "JRBA", "Circulars", "FAQs", "Notices",
                  "Press releases", "News", "Other"):
        if group not in groups:
            continue
        lengths = [len(c["text"]) for c in groups[group]]
        stats_rows.append(
            {
                "source": group,
                "documents": len({c["document_id"] for c in groups[group]}),
                "chunks": len(lengths),
                "total_chars": sum(lengths),
                "mean_chunk_chars": round(sum(lengths) / len(lengths)),
                "min_chunk_chars": min(lengths),
                "max_chunk_chars": max(lengths),
                "chunks_with_heading": sum(1 for c in groups[group] if c.get("heading")),
            }
        )
    stats = pd.DataFrame(stats_rows)
    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    stats.to_csv(STATS_PATH, index=False, encoding="utf-8-sig")

    # --- report (markdown table built by hand; pandas.to_markdown would pull
    # in the extra 'tabulate' dependency for nothing)
    cols = list(stats.columns)
    md_table = "\n".join(
        ["| " + " | ".join(cols) + " |",
         "|" + "---|" * len(cols)]
        + ["| " + " | ".join(str(v) for v in row) + " |"
           for row in stats.itertuples(index=False)]
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    verdict = "PASS" if not errors else "FAIL"
    lines = [
        "# Validation report — NRS corpus (Abdul)",
        "",
        f"Result: **{verdict}** — {len(errors)} error(s), {len(warnings)} warning(s), "
        f"{len(chunks)} chunks across {len(chunked_ids)} documents.",
        "",
        "## Statistics",
        "",
        md_table,
        "",
        "## Errors",
        "",
        *([f"- {e}" for e in errors] or ["- none"]),
        "",
        "## Warnings",
        "",
        *([f"- {w}" for w in warnings] or ["- none"]),
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(stats.to_string(index=False))
    print(f"\n{verdict}: {len(errors)} error(s), {len(warnings)} warning(s)")
    for e in errors[:20]:
        print(" ERROR:", e)
    for w in warnings[:20]:
        print(" warn :", w)
    print(f"report: {REPORT_PATH}, statistics: {STATS_PATH}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
