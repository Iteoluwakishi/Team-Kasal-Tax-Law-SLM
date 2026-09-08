"""Stage 04: Parse document structure and chunk by document type.

Reads cleaned documents from data/interim/cleaned/ and writes JSONL chunks:

  data/processed/current/nrsea.jsonl     - NRSEA act, one chunk per section
  data/processed/current/jrba.jsonl      - JRBA act, one chunk per section
  data/processed/guidance/nrs_guidance.jsonl - circulars + FAQs + notices
                                               + press releases + news

Chunking rules per type:
  act      Part -> Section (heading = recovered margin note; body starts at
           "ENACTED", schedules chunked separately, stops at "I certify")
  circular decimal-numbered headings (1.0 / 2.1 / 4.1.1), preamble first
  faq      one chunk per Q&A pair - a question is NEVER split from its answer
  notice / press_release / news
           one chunk per document, split at paragraph breaks only if long

Every chunk keeps full provenance: document_id, section, page, status,
legal_weight, so any model answer can be traced to its source.

Run from the repo root:
    python src/preprocessing/04_structure_chunk.py
"""

import json
import re
from pathlib import Path

import pandas as pd

METADATA_CSV = Path("data/metadata/documents.csv")
CLEAN_DIR = Path("data/interim/cleaned")
CURRENT_DIR = Path("data/processed/current")
GUIDANCE_DIR = Path("data/processed/guidance")

ASSIGNEE = "abdul"
MAX_CHUNK_CHARS = 2800       # soft cap; long sections split at subsection starts
# A margin heading sits level with its section's first line, but can be
# printed up to ~35pt above it (NRSEA s.38 "Indemnity"). Window is relative
# to the section line: negative = note above.
HEADING_WINDOW_ABOVE = 40
HEADING_WINDOW_BELOW = 15

# "1. text" or "5.—(1) text" at line start opens an act section
ACT_SECTION_RE = re.compile(r"^(\d{1,3})\.\s*(—|—)?\s*")
ACT_PART_RE = re.compile(r"^PART\s+[IVXLC]+\b")
SUBSECTION_RE = re.compile(r"^\(\d{1,2}\)")
# "1.0 Introduction" / "4.1.1 Treatment ..." — digit(s) required after the dot
# so body wraps like "2025. tokenised" don't match
CIRCULAR_HEADING_RE = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){1,3})\.?\s+(\S.*)")


def assemble(line_texts: list) -> str:
    """Join wrapped lines into flowing text, mending hyphenated breaks.

    A trailing -/– glued to a letter is a line-wrap hyphen ("institu-" +
    "tional"); a dash after a space ("shall –") is punctuation and kept.
    """
    out = ""
    for t in line_texts:
        t = t.strip()
        if not t:
            continue
        if (out and out[-1] in "-–‑" and len(out) > 1 and out[-2].isalpha()
                and t[:1].islower()):
            out = out[:-1] + t
        elif out:
            out += " " + t
        else:
            out = t
    return out


def base_record(meta: pd.Series) -> dict:
    return {
        "document_id": meta["document_id"],
        "document_type": meta["document_type"],
        "legal_weight": meta["legal_weight"],
        "issuing_authority": meta["issuing_authority"],
        "status": meta["status"],
        "document_title": meta["title"],
        "publication_date": meta["publication_date"],
        "effective_date": meta["effective_date"],
        "source_file": meta["filename"],
    }


MIN_STANDALONE_CHARS = 40


def finish(chunks: list, meta: pd.Series) -> list:
    """Merge heading-only fragments forward, then assign chunk ids.

    A chunk shorter than MIN_STANDALONE_CHARS is usually a parent heading
    whose content lives in its sub-sections (e.g. "6.0 Applicable Taxes"
    directly followed by "6.1 Income tax"); it is prepended to the next
    chunk so the heading context travels with the content.
    """
    chunks = [c for c in chunks if c["text"].strip()]
    merged = []
    carry = None
    for chunk in chunks:
        if carry is not None:
            chunk = {**chunk, "text": carry["text"] + "\n" + chunk["text"],
                     "page": carry["page"]}
            carry = None
        if len(chunk["text"]) < MIN_STANDALONE_CHARS:
            carry = chunk
        else:
            merged.append(chunk)
    if carry is not None:  # short tail: merge backward instead
        if merged:
            merged[-1]["text"] += "\n" + carry["text"]
        else:
            merged.append(carry)

    out = []
    for chunk in merged:
        chunk = {**base_record(meta), **chunk}
        chunk["chunk_id"] = f"{meta['document_id']}#{len(out):03d}"
        out.append(chunk)
    return out


# ----------------------------------------------------------------- acts

def split_long_section(lines: list) -> list:
    """Split an oversized section's lines into pieces at subsection starts."""
    pieces, current = [], []
    size = 0
    for line in lines:
        if current and size > MAX_CHUNK_CHARS and SUBSECTION_RE.match(line["text"]):
            pieces.append(current)
            current, size = [], 0
        current.append(line)
        size += len(line["text"])
    if current:
        pieces.append(current)
    return pieces


def chunk_act(doc: dict, meta: pd.Series) -> list:
    chunks = []
    part = ""
    in_body = False
    in_schedules = False
    stopped = False
    # current section accumulator: {"section", "heading", "page", "lines"}
    current = None

    def close_current():
        nonlocal current
        if current is None:
            return
        for piece in split_long_section(current["lines"]):
            chunks.append(
                {
                    "part": current["part"],
                    "section": current["section"],
                    "heading": current["heading"],
                    "page": current["page"],
                    "text": assemble([l["text"] for l in piece]),
                }
            )
        current = None

    for page in doc["pages"]:
        if stopped:
            break
        notes = page.get("margin_notes", [])
        for line in page.get("lines", []):
            text = line["text"].strip()
            if not text:
                continue
            if not in_body:
                if text.startswith("ENACTED"):
                    in_body = True
                continue
            if text.startswith("I certify"):
                close_current()
                stopped = True
                break
            if text == "SCHEDULES" or text.startswith("SCHEDULE"):
                close_current()
                in_schedules = True
                part = text
                continue
            if in_schedules and text.isupper():
                # schedule title lines extend the part context
                part = (part + " " + text).strip()
                continue
            if ACT_PART_RE.match(text):
                close_current()
                part = text
                continue
            match = ACT_SECTION_RE.match(text)
            if match:
                close_current()
                # nearest unclaimed margin note within the window is the heading
                heading = ""
                best = None
                for note in notes:
                    delta = note["top"] - line["top"]
                    if -HEADING_WINDOW_ABOVE <= delta <= HEADING_WINDOW_BELOW:
                        if best is None or abs(delta) < abs(best["top"] - line["top"]):
                            best = note
                if best is not None:
                    heading = best["text"]
                    notes = [n for n in notes if n is not best]
                current = {
                    "part": part,
                    "section": match.group(1),
                    "heading": heading,
                    "page": page["page"],
                    "lines": [line],
                }
            elif current is not None:
                current["lines"].append(line)
            # text before the first section (e.g. the long title) is dropped;
            # it repeats the metadata already in documents.csv
    close_current()
    return finish(chunks, meta)


# ------------------------------------------------------------ circulars

def chunk_circular(doc: dict, meta: pd.Series) -> list:
    chunks = []
    current = {"section": "0", "heading": "Preamble", "page": 1, "lines": []}

    def close_current():
        if not current["lines"]:
            return
        # oversized sections (long worked examples) split at line boundaries
        pieces, buf, size = [], [], 0
        for line in current["lines"]:
            if buf and size + len(line["text"]) > MAX_CHUNK_CHARS:
                pieces.append(buf)
                buf, size = [], 0
            buf.append(line)
            size += len(line["text"])
        if buf:
            pieces.append(buf)
        for piece in pieces:
            chunks.append(
                {
                    "part": "",
                    "section": current["section"],
                    "heading": current["heading"],
                    "page": current["page"],
                    "text": assemble([l["text"] for l in piece]),
                }
            )

    for page in doc["pages"]:
        for line in page.get("lines", []):
            match = CIRCULAR_HEADING_RE.match(line["text"])
            if match:
                close_current()
                current = {
                    "section": match.group(1),
                    "heading": match.group(2).strip().rstrip(":"),
                    "page": page["page"],
                    "lines": [line],
                }
            else:
                current["lines"].append(line)
    close_current()
    return finish(chunks, meta)


# ------------------------------------------------- faq and web documents

def chunk_faq(doc: dict, meta: pd.Series) -> list:
    chunks = []
    for item in doc["faq_items"]:
        if not item["question"] or not item["answer"]:
            continue
        chunks.append(
            {
                "part": "",
                "section": item["topic"],
                "heading": item["question"],
                "page": 1,
                "text": f"Q: {item['question']}\nA: {item['answer']}",
                "source_url": doc.get("source_url", ""),
            }
        )
    return finish(chunks, meta)


def chunk_web_document(doc: dict, meta: pd.Series) -> list:
    text = doc["pages"][0]["text"]
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    pieces, current = [], ""
    for para in paragraphs:
        if current and len(current) + len(para) > MAX_CHUNK_CHARS:
            pieces.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        pieces.append(current)
    return finish(
        [
            {
                "part": "",
                "section": "",
                "heading": meta["title"],
                "page": 1,
                "text": piece,
                "source_url": doc.get("source_url", ""),
            }
            for piece in pieces
        ],
        meta,
    )


CHUNKERS = {
    "act": chunk_act,
    "circular": chunk_circular,
    "faq": chunk_faq,
    "notice": chunk_web_document,
    "press_release": chunk_web_document,
    "news": chunk_web_document,
}

# which output file each of abdul's documents belongs to
ACT_OUTPUT = {"nrsea_2025": "nrsea.jsonl", "jrba_2025": "jrba.jsonl"}


def main() -> None:
    df = pd.read_csv(METADATA_CSV, encoding="utf-8-sig").fillna("")
    mine = df[df["assigned_to"] == ASSIGNEE]
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    GUIDANCE_DIR.mkdir(parents=True, exist_ok=True)

    act_chunks = {}      # output filename -> chunks
    guidance_chunks = []

    for _, meta in mine.iterrows():
        src = CLEAN_DIR / f"{meta['document_id']}.json"
        if not src.exists():
            print(f"WARNING: missing cleaned file {src} — run 03_clean.py")
            continue
        if str(meta["has_text"]).lower() == "false":
            print(f"SKIPPED {meta['document_id']}: image-only, no text to chunk "
                  "(poster saved in data/raw/guidance/images/)")
            continue
        with open(src, encoding="utf-8") as f:
            doc = json.load(f)
        chunks = CHUNKERS[meta["document_type"]](doc, meta)
        print(f"{meta['document_id']}: {len(chunks)} chunks")
        if meta["document_id"] in ACT_OUTPUT:
            act_chunks[ACT_OUTPUT[meta["document_id"]]] = chunks
        else:
            guidance_chunks.extend(chunks)

    for filename, chunks in act_chunks.items():
        path = CURRENT_DIR / filename
        with open(path, "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
        print(f"wrote {path} ({len(chunks)} chunks)")

    path = GUIDANCE_DIR / "nrs_guidance.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for chunk in guidance_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"wrote {path} ({len(guidance_chunks)} chunks)")


if __name__ == "__main__":
    main()
