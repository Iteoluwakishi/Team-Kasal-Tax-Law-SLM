"""Stage 02: Extract raw text page-by-page from Abdul's documents.

Reads data/metadata/documents.csv (produced by 01_inventory.py), selects the
documents assigned to "abdul", and extracts the full text of each one with
pdfplumber, one JSON file per document in data/interim/.

Text is written exactly as pdfplumber returns it — headers, page numbers and
line-wrap artifacts included. Cleaning is deliberately deferred to stage 03 so
the interim files stay a faithful record of the source PDFs.

Run from the repo root:
    python src/preprocessing/02_extract.py
"""

import json
from pathlib import Path

import pandas as pd
import pdfplumber

RAW_DIR = Path("data/raw")
METADATA_CSV = Path("data/metadata/documents.csv")
INTERIM_DIR = Path("data/interim")

ASSIGNEE = "abdul"


def rich_to_text(node) -> str:
    """Flatten Strapi rich-text JSON (nested lists/dicts) into plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(rich_to_text(n) for n in node)
    if isinstance(node, dict):
        if "text" in node:
            return node["text"]
        inner = rich_to_text(node.get("children", []))
        node_type = node.get("type", "")
        if node_type == "paragraph" or node_type.startswith("heading"):
            return inner + "\n\n"
        if node_type == "list-item":
            return "- " + inner + "\n"
        return inner
    return ""


def extract_news_item(doc: pd.Series, snapshot: dict) -> dict:
    """Extract one notice/press release/news item from the news snapshot."""
    item_id = int(doc["document_id"].rsplit("_", 1)[-1])
    item = next(i for i in snapshot["items"] if i["id"] == item_id)
    text = (item["title"].strip() + "\n\n" + item["body"].strip()).strip()
    return {
        "document_id": doc["document_id"],
        "title": doc["title"],
        "document_type": doc["document_type"],
        "legal_weight": doc["legal_weight"],
        "status": doc["status"],
        "source_file": doc["filename"],
        "source_url": snapshot["source_url"],
        "retrieved": snapshot["retrieved"],
        "image": item.get("image"),
        "n_pages": 1,
        "pages": [{"page": 1, "chars": len(text), "text": text}],
    }


def extract_faq(doc: pd.Series, snapshot: dict) -> dict:
    """Extract all Q&A pairs from the FAQ snapshot."""
    faqs = snapshot["data"]["PageContent"][0]["FAQs"]
    items = [
        {
            "question": rich_to_text(f.get("Question")).strip(),
            "answer": rich_to_text(f.get("Answer")).strip(),
            "topic": (f.get("Topic") or "").strip(),
        }
        for f in faqs
    ]
    empty = sum(1 for i in items if not i["question"] or not i["answer"])
    if empty:
        print(f"  NOTE: {empty} FAQ items with empty question or answer")
    return {
        "document_id": doc["document_id"],
        "title": doc["title"],
        "document_type": doc["document_type"],
        "legal_weight": doc["legal_weight"],
        "status": doc["status"],
        "source_file": doc["filename"],
        "source_url": snapshot["source_url"],
        "retrieved": snapshot["retrieved"],
        "n_items": len(items),
        "faq_items": items,
    }


def extract_document(doc: pd.Series) -> dict:
    """Extract every page of one PDF into a JSON-serialisable dict."""
    pdf_path = RAW_DIR / doc["filename"]
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            # Also store each word with its position on the page. Stage 03
            # needs the x-coordinates to separate the gazette margin column
            # (section headings) from the body column, without re-reading the
            # PDFs. Coordinates are in PDF points from the page's top-left.
            words = [
                {
                    "t": w["text"],
                    "x0": round(w["x0"], 1),
                    "x1": round(w["x1"], 1),
                    "top": round(w["top"], 1),
                    "bottom": round(w["bottom"], 1),
                }
                for w in page.extract_words()
            ]
            pages.append(
                {"page": i, "chars": len(text), "text": text, "words": words}
            )

    empty = [p["page"] for p in pages if p["chars"] == 0]
    if empty:
        print(f"  NOTE: pages with no text in {doc['document_id']}: {empty}")

    return {
        "document_id": doc["document_id"],
        "title": doc["title"],
        "document_type": doc["document_type"],
        "legal_weight": doc["legal_weight"],
        "status": doc["status"],
        "source_file": doc["filename"],
        "n_pages": len(pages),
        "pages": pages,
    }


def main() -> None:
    if not METADATA_CSV.exists():
        raise SystemExit(f"{METADATA_CSV} not found — run 01_inventory.py first.")

    df = pd.read_csv(METADATA_CSV, encoding="utf-8-sig").fillna("")
    mine = df[df["assigned_to"] == ASSIGNEE]
    if mine.empty:
        raise SystemExit(f"No documents assigned to '{ASSIGNEE}' in {METADATA_CSV}.")

    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    # JSON snapshots hold many documents each — load each file only once.
    snapshot_cache = {}
    for _, doc in mine.iterrows():
        print(f"Extracting {doc['document_id']} ({doc['filename']}) ...")
        if str(doc["filename"]).endswith(".json"):
            path = RAW_DIR / doc["filename"]
            if path not in snapshot_cache:
                with open(path, encoding="utf-8") as f:
                    snapshot_cache[path] = json.load(f)
            snapshot = snapshot_cache[path]
            if doc["document_type"] == "faq":
                result = extract_faq(doc, snapshot)
            else:
                result = extract_news_item(doc, snapshot)
        else:
            result = extract_document(doc)

        out_path = INTERIM_DIR / f"{doc['document_id']}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
        if "faq_items" in result:
            print(f"  wrote {out_path} — {result['n_items']} Q&A pairs")
        else:
            total_chars = sum(p["chars"] for p in result["pages"])
            print(f"  wrote {out_path} — {result['n_pages']} pages, {total_chars:,} chars")


if __name__ == "__main__":
    main()
