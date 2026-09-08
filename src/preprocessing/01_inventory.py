"""Stage 01: Inventory of raw PDFs.

Scans data/raw/ (recursively, so data/raw/guidance/ is included once it
exists), matches each PDF against the KNOWN_DOCUMENTS registry, inspects it
with pdfplumber (page count, embedded-text availability), and writes
data/metadata/documents.csv.

Run from the repo root:
    python src/preprocessing/01_inventory.py

PDFs found on disk but missing from KNOWN_DOCUMENTS are still inventoried,
but flagged UNREGISTERED so we notice new circulars/FAQs/notices and register
them here with proper metadata before processing them further.
"""

import json
from pathlib import Path

import pandas as pd
import pdfplumber

RAW_DIR = Path("data/raw")
METADATA_DIR = Path("data/metadata")

# How many pages to sample per PDF when checking for embedded text.
# Sampling keeps the 610-page repealed-acts compilation from slowing the scan.
TEXT_SAMPLE_PAGES = 15
MIN_CHARS_PER_PAGE = 50  # fewer chars than this => page counts as "no text"

# Registry of every document we know about, keyed by filename in data/raw/.
# When a new circular/FAQ/notice lands in data/raw/guidance/, add an entry
# here — the scan will warn about any PDF it finds that is not registered.
#
# legal_weight distinguishes what the RAG layer may cite as law:
#   statute                 - an Act of the National Assembly
#   subsidiary_legislation  - regulations made under an Act (gazetted S.I.)
#   administrative_guidance - circulars/FAQs/notices; NOT law
#   reference_compilation   - collections kept for negative/reference data
KNOWN_DOCUMENTS = {
    "Approved Copy to Print. Nigeria Revenue Service (Establishment) Act, 2025-1.pdf": {
        "document_id": "nrsea_2025",
        "title": "Nigeria Revenue Service (Establishment) Act, 2025",
        "short_title": "NRSEA",
        "document_type": "act",
        "legal_weight": "statute",
        "issuing_authority": "National Assembly of the Federal Republic of Nigeria",
        "status": "in_force",
        "assigned_to": "abdul",
        "publication_date": "2025-06-26",  # Official Gazette No. 117, Vol. 112
        "effective_date": "2025-06-26",
        "notes": "Act No. 4 of 2025. Passed 11 Jun 2025, assented 26 Jun 2025. "
                 "No commencement clause, so in force from assent.",
    },
    "Approved Copy to Print Joint Revenue Board of Nigeria (Establishment) Act, 2025 B.pdf": {
        "document_id": "jrba_2025",
        "title": "Joint Revenue Board of Nigeria (Establishment) Act, 2025",
        "short_title": "JRBA",
        "document_type": "act",
        "legal_weight": "statute",
        "issuing_authority": "National Assembly of the Federal Republic of Nigeria",
        "status": "in_force",
        "assigned_to": "abdul",
        "publication_date": "2025-06-26",  # Official Gazette No. 117, Vol. 112
        "effective_date": "2025-06-26",
        "notes": "Act No. 6 of 2025. Passed 11 Jun 2025, assented 26 Jun 2025. "
                 "No commencement clause, so in force from assent.",
    },
    "Final Approved Copy for Print  NIGERIA TAX ACT 2025.pdf": {
        "document_id": "nta_2025",
        "title": "Nigeria Tax Act, 2025",
        "short_title": "NTA",
        "document_type": "act",
        "legal_weight": "statute",
        "issuing_authority": "National Assembly of the Federal Republic of Nigeria",
        "status": "in_force",
        "assigned_to": "team",
        "publication_date": "2025-06-26",
        "effective_date": "2026-01-01",
        "notes": "Act No. 7 of 2025. Commencement clause: 1st January, 2026. "
                 "Processed by other team members.",
    },
    "Approved Copy to Print NIGERIA TAX ADMINISTRATION ACT, 2025.pdf": {
        "document_id": "ntaa_2025",
        "title": "Nigeria Tax Administration Act, 2025",
        "short_title": "NTAA",
        "document_type": "act",
        "legal_weight": "statute",
        "issuing_authority": "National Assembly of the Federal Republic of Nigeria",
        "status": "in_force",
        "assigned_to": "team",
        "publication_date": "2025-06-26",
        "effective_date": "2025-06-26",
        "notes": "Act No. 5 of 2025. No commencement clause found on scan — "
                 "owner should verify effective date. Processed by other team members.",
    },
    "Deduction of Tax at Source (Withholding) Regulations 2024_Gazetted.pdf": {
        "document_id": "wht_regulations_2024",
        "title": "Deduction of Tax at Source (Withholding) Regulations, 2024",
        "short_title": "WHT Regulations",
        "document_type": "regulation",
        "legal_weight": "subsidiary_legislation",
        "issuing_authority": "Federal Ministry of Finance",
        "status": "in_force",
        "assigned_to": "team",
        "publication_date": "2024-10-02",  # Official Gazette No. 168, Vol. 111
        "effective_date": "2024-09-30",    # commencement printed in the S.I.
        "notes": "S.I. No. 34 of 2024.",
    },
    "Repealed acts.pdf": {
        "document_id": "repealed_acts_compilation",
        "title": "E-Book of Tax and Related Laws (Finance Act 2020 edition)",
        "short_title": "Repealed Acts",
        "document_type": "reference",
        "legal_weight": "reference_compilation",
        "issuing_authority": "Federal Inland Revenue Service (defunct)",
        "status": "repealed",
        "assigned_to": "team",
        "publication_date": "",
        "effective_date": "",
        "notes": "Compilation of pre-reform tax laws (CGT, CITA, PITA, VAT, PPT, "
                 "Stamp Duties). Kept as negative/reference dataset only.",
    },
}

# NRS Information Circulars downloaded from www.nrs.gov.ng (files live in
# data/raw/guidance/). Circular number and publication date are printed on
# each circular's first page. Format: (circular_no, filename, subject, pub_date, extra_notes)
_NRS_CIRCULARS = [
    ("2026/01", "circular_2026_01_companies_income_tax_development_levy.pdf",
     "Ascertainment of Income Tax of Companies and Development Levy",
     "2026-06-29", ""),
    ("2026/03", "circular_2026_03_chargeable_gains.pdf",
     "Clarification on Ascertainment of Chargeable Gains",
     "2026-06-29", "Revised version (30/05/2026 revision marker in source filename)."),
    ("2026/04", "circular_2026_04_dutiable_instruments.pdf",
     "Clarification on Dutiable Instruments",
     "2026-06-29", "Replaces FIRS Information Circular No. 2021/12."),
    ("2026/05", "circular_2026_05_vat_administration.pdf",
     "Clarification on the Changes in the Administration of the Value Added Tax",
     "2026-06-29", ""),
    ("2026/10", "circular_2026_10_shipping_air_transport.pdf",
     "Taxation of Non-Resident Persons Engaged in Shipping and Air Transport",
     "2026-06-29", ""),
    ("2026/11", "circular_2026_11_tax_treaty_benefits.pdf",
     "Claim of Tax Treaties Benefits and Unilateral Credit Relief in Nigeria",
     "2026-06-29", ""),
    ("2026/14", "circular_2026_14_lng_estimated_returns.pdf",
     "Guidelines for Estimated Returns by Companies Engaged in Midstream "
     "Liquefied Natural Gas Activities",
     "2026-06-29", "Issued as Guidelines under Information Circular numbering."),
    ("2026/17", "circular_2026_17_tax_refund_guidelines.pdf",
     "Guidelines on Tax Refund",
     "2026-06-29", "Issued as Guidelines under Information Circular numbering."),
    ("2026/18", "circular_2026_18_vat_withholding_guidelines.pdf",
     "Guidelines on the Withholding of Value Added Tax",
     "2026-06-29", "Issued as Guidelines under Information Circular numbering."),
    ("2026/21", "circular_2026_21_virtual_assets_guidelines.pdf",
     "Guidelines on the Taxation of Virtual Assets",
     "2026-07-31", "Issued as Guidelines under Information Circular numbering."),
]

for _no, _fname, _subject, _pub, _extra in _NRS_CIRCULARS:
    KNOWN_DOCUMENTS[_fname] = {
        # "2026/01" -> "circular_2026_01"
        "document_id": "circular_" + _no.replace("/", "_"),
        "title": f"NRS Information Circular No. {_no}: {_subject}",
        "short_title": f"Circular {_no}",
        "document_type": "circular",
        "legal_weight": "administrative_guidance",
        "issuing_authority": "Nigeria Revenue Service",
        "status": "in_force",
        "assigned_to": "abdul",
        "publication_date": _pub,
        "effective_date": _pub,
        "notes": (f"Downloaded from www.nrs.gov.ng. Administrative guidance, not law. "
                  + _extra).strip(),
    }


def news_snapshot_rows(path: Path) -> list:
    """Expand the news-releases JSON snapshot into one row per item.

    The snapshot was captured from the NRS website's own data API
    (www.nrs.gov.ng/api/news-releases). Each notice/press release/news item
    is its own document per our data conventions.
    """
    with open(path, encoding="utf-8") as f:
        snap = json.load(f)

    type_map = {"Notice": "notice", "Press Release": "press_release", "News": "news"}
    rows = []
    for item in snap["items"]:
        doc_type = type_map.get(item["category"], "news")
        body_ok = len(item["body"]) >= 45
        pub_date = (item.get("publish_date") or "")[:10]
        notes = f"From NRS website API, retrieved {snap['retrieved'][:10]}. Item id {item['id']}."
        if not body_ok:
            notes += " IMAGE-ONLY: text lives in a poster image (see data/raw/guidance/images/); needs OCR decision."
        rows.append(
            {
                "document_id": f"nrs_{doc_type}_{item['id']}",
                "title": item["title"].strip(),
                "short_title": "",
                "document_type": doc_type,
                "legal_weight": "administrative_guidance" if doc_type == "notice"
                                else "official_communication",
                "issuing_authority": "Nigeria Revenue Service",
                "status": "in_force",
                "assigned_to": "abdul",
                "publication_date": pub_date,
                "effective_date": pub_date,
                "notes": notes,
                "filename": str(path.relative_to(RAW_DIR)),
                "pages": 1,
                "sampled_pages": "",
                "text_coverage": "",
                "has_text": body_ok,
            }
        )
    return rows


def faq_snapshot_row(path: Path) -> dict:
    """One row for the FAQ snapshot (the FAQ collection is one document;
    individual Q&A pairs become chunks in stage 04)."""
    with open(path, encoding="utf-8") as f:
        snap = json.load(f)
    faqs = snap["data"]["PageContent"][0]["FAQs"]
    return {
        "document_id": "nrs_faq_2026",
        "title": "NRS Frequently Asked Questions (nrs.gov.ng)",
        "short_title": "NRS FAQ",
        "document_type": "faq",
        "legal_weight": "administrative_guidance",
        "issuing_authority": "Nigeria Revenue Service",
        "status": "in_force",
        "assigned_to": "abdul",
        "publication_date": snap["data"].get("updatedAt", "")[:10],
        "effective_date": "",
        "notes": f"From NRS website API, retrieved {snap['retrieved'][:10]}. "
                 f"{len(faqs)} Q&A pairs with topics.",
        "filename": str(path.relative_to(RAW_DIR)),
        "pages": 1,
        "sampled_pages": "",
        "text_coverage": "",
        "has_text": True,
    }


# Non-PDF raw sources captured from the NRS website; each maps to a function
# that turns the snapshot file into inventory row(s).
SNAPSHOT_FILES = {
    "nrs_news_releases_snapshot.json": news_snapshot_rows,
    "nrs_faq_snapshot.json": faq_snapshot_row,
}


def inspect_pdf(path: Path) -> dict:
    """Open one PDF and report page count and embedded-text availability."""
    with pdfplumber.open(path) as pdf:
        n_pages = len(pdf.pages)
        # Sample pages evenly across the document instead of reading them all.
        step = max(1, n_pages // TEXT_SAMPLE_PAGES)
        sampled = pdf.pages[::step][:TEXT_SAMPLE_PAGES]
        pages_with_text = sum(
            1
            for page in sampled
            if len(page.extract_text() or "") >= MIN_CHARS_PER_PAGE
        )
        # Gazettes contain deliberately blank pages carrying only a page label
        # ("B 754"), so require most — not all — sampled pages to have text.
        coverage = pages_with_text / len(sampled)
        return {
            "pages": n_pages,
            "sampled_pages": len(sampled),
            "text_coverage": round(coverage, 2),
            "has_text": coverage >= 0.7,
        }


def build_inventory() -> pd.DataFrame:
    rows = []
    pdf_paths = sorted(RAW_DIR.rglob("*.pdf"))
    if not pdf_paths:
        raise SystemExit(f"No PDFs found under {RAW_DIR} — run from the repo root.")

    for path in pdf_paths:
        meta = KNOWN_DOCUMENTS.get(path.name)
        if meta is None:
            print(f"WARNING: unregistered PDF: {path} — add it to KNOWN_DOCUMENTS")
            meta = {
                "document_id": path.stem.lower().replace(" ", "_"),
                "title": path.stem,
                "short_title": "",
                "document_type": "unknown",
                "legal_weight": "unknown",
                "issuing_authority": "",
                "status": "unknown",
                "assigned_to": "",
                "publication_date": "",
                "effective_date": "",
                "notes": "UNREGISTERED — metadata not yet entered in 01_inventory.py",
            }

        print(f"Inspecting {path.name} ...")
        inspection = inspect_pdf(path)
        rows.append(
            {
                **meta,
                "filename": str(path.relative_to(RAW_DIR)),
                **inspection,
            }
        )

    registered_missing = set(KNOWN_DOCUMENTS) - {p.name for p in pdf_paths}
    for name in sorted(registered_missing):
        print(f"WARNING: registered document not found on disk: {name}")

    # JSON snapshots captured from the NRS website (FAQs, notices, press releases)
    for name, handler in SNAPSHOT_FILES.items():
        matches = list(RAW_DIR.rglob(name))
        if not matches:
            print(f"WARNING: snapshot not found on disk: {name}")
            continue
        result = handler(matches[0])
        new_rows = result if isinstance(result, list) else [result]
        print(f"Registered {len(new_rows)} document(s) from {name}")
        rows.extend(new_rows)

    return pd.DataFrame(rows)


def main() -> None:
    df = build_inventory()
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = METADATA_DIR / "documents.csv"
    # utf-8-sig writes a BOM so Excel/PowerShell on Windows decode it correctly.
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\nWrote {len(df)} documents to {out_path}")
    print(
        df[["document_id", "document_type", "status", "assigned_to", "pages", "has_text"]]
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
