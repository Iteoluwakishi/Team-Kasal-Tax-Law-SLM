"""Annotation pipeline step 1: build the provisions catalog.

Reads every chunk file under data/processed/ (current law, guidance, repealed
law) and normalises the three different chunk schemas in the repo into ONE
provisions format that the rest of the annotation pipeline consumes:

  - abdul's chunks   (nrsea/jrba/guidance): document_id, section, heading,
                     page, status, legal_weight, ...
  - nta/ntaa chunks  (minimal): chunk_id, document_id, status, text
  - repealed chunks  (rich): act, cap, section, repeal_status,
                     replacement_legislation, ...

Chunks failing a basic quality gate (too short, or mostly non-letter garbage
from OCR) are dropped and counted per source, so extraction problems upstream
stay visible instead of leaking into the dataset.

Writes data/annotation/provisions.jsonl.

Run from the repo root:
    python src/annotation_pipeline/01_extract_provisions.py
"""

import json
from pathlib import Path

PROCESSED_DIR = Path("data/processed")
OUT_PATH = Path("data/annotation/provisions.jsonl")

MIN_CHARS = 100
MIN_LETTER_RATIO = 0.55

# document_id -> (short law id, human-readable name, effective_date)
LAW_INFO = {
    "nrsea_2025": ("NRSEA", "Nigeria Revenue Service (Establishment) Act, 2025", "2025-06-26"),
    "jrba_2025": ("JRBA", "Joint Revenue Board of Nigeria (Establishment) Act, 2025", "2025-06-26"),
    "nta": ("NTA", "Nigeria Tax Act, 2025", "2026-01-01"),
    "ntaa": ("NTAA", "Nigeria Tax Administration Act, 2025", "2025-06-26"),
}

STATUS_MAP = {
    "in_force": "current",
    "active": "current",
    "current": "current",
    "amended": "amended",
    "repealed": "repealed",
    "superseded": "superseded",
    "transitional": "transitional",
}


def quality_ok(text: str) -> bool:
    if len(text) < MIN_CHARS:
        return False
    letters = sum(1 for ch in text if ch.isalpha() or ch.isspace())
    return letters / len(text) >= MIN_LETTER_RATIO


def normalise(chunk: dict, corpus_file: str) -> dict:
    """Map any of the repo's chunk schemas onto the provisions format."""
    doc_id = chunk.get("document_id", "")

    if "act" in chunk and "repeal_status" in chunk:      # repealed-law schema
        law = doc_id or chunk["act"]
        return {
            "chunk_id": chunk["chunk_id"],
            "document_id": doc_id,
            "law": law.upper(),
            "law_name": chunk.get("act", law),
            "part": chunk.get("part", ""),
            "section": str(chunk.get("section", "")),
            "heading": chunk.get("section_heading", ""),
            "text": chunk["text"],
            "legal_status": STATUS_MAP.get(chunk.get("repeal_status", "repealed"), "repealed"),
            "effective_date": chunk.get("original_effective_date", ""),
            "replacement_legislation": chunk.get("replacement_legislation", ""),
            "source": chunk.get("source", chunk.get("cap", "")),
            "source_file": chunk.get("source", ""),
            "page": None,
            "source_url": "",
            "document_type": "repealed_act",
            "corpus_file": corpus_file,
        }

    if "legal_weight" in chunk:                          # abdul's schema
        law, law_name, eff = LAW_INFO.get(
            doc_id, (doc_id.upper(), chunk.get("document_title", doc_id), "")
        )
        if chunk["document_type"] != "act":
            law = doc_id.upper()
            law_name = chunk.get("document_title", doc_id)
            eff = chunk.get("effective_date", "")
        return {
            "chunk_id": chunk["chunk_id"],
            "document_id": doc_id,
            "law": law,
            "law_name": law_name,
            "part": chunk.get("part", ""),
            "section": str(chunk.get("section", "")),
            "heading": chunk.get("heading", ""),
            "text": chunk["text"],
            "legal_status": STATUS_MAP.get(chunk.get("status", ""), "current"),
            "effective_date": chunk.get("effective_date", eff) or eff,
            "replacement_legislation": "",
            "source": chunk.get("document_title", law_name),
            "source_file": chunk.get("source_file", ""),
            "page": chunk.get("page"),
            "source_url": chunk.get("source_url", ""),
            "document_type": chunk.get("document_type", ""),
            "corpus_file": corpus_file,
        }

    # minimal nta/ntaa schema
    law, law_name, eff = LAW_INFO.get(doc_id, (doc_id.upper(), doc_id, ""))
    return {
        "chunk_id": chunk["chunk_id"],
        "document_id": doc_id,
        "law": law,
        "law_name": law_name,
        "part": "",
        "section": "",
        "heading": "",
        "text": chunk["text"],
        "legal_status": STATUS_MAP.get(chunk.get("status", ""), "current"),
        "effective_date": eff,
        "replacement_legislation": "",
        "source": law_name,
        "source_file": corpus_file,
        "page": None,
        "source_url": "",
        "document_type": "act",
        "corpus_file": corpus_file,
    }


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    kept, dropped = [], {}
    seen_ids = set()
    for path in sorted(PROCESSED_DIR.rglob("*.jsonl")):
        if "interim" in path.parts:
            continue
        name = str(path.relative_to(PROCESSED_DIR)).replace("\\", "/")
        n_kept = n_dropped = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                chunk = json.loads(line)
                if "chunk_id" not in chunk or "text" not in chunk:
                    continue
                if not quality_ok(chunk["text"]):
                    n_dropped += 1
                    continue
                prov = normalise(chunk, name)
                # chunk_ids collide across corpus files from different authors
                if prov["chunk_id"] in seen_ids:
                    prov["chunk_id"] = f"{name}:{prov['chunk_id']}"
                seen_ids.add(prov["chunk_id"])
                kept.append(prov)
                n_kept += 1
        dropped[name] = (n_kept, n_dropped)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for prov in kept:
            f.write(json.dumps(prov, ensure_ascii=False) + "\n")

    print(f"{'corpus file':38s} {'kept':>6s} {'dropped':>8s}")
    for name, (n_kept, n_dropped) in dropped.items():
        flag = "  <-- check source quality" if n_dropped > n_kept * 0.2 else ""
        print(f"{name:38s} {n_kept:6d} {n_dropped:8d}{flag}")
    print(f"\nwrote {len(kept)} provisions to {OUT_PATH}")


if __name__ == "__main__":
    main()
