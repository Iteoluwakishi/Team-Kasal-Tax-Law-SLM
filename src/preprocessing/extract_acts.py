"""
Phase 2 preprocessing — Step 1: Extract per-Act raw text from the consolidated
E-Book of Tax and Related Laws PDF, based on its table of contents page numbers.

Usage (from project root):
    python src/preprocessing/extract_acts.py

Reads:  data/raw/Repealed_acts.pdf
Writes: data/processed/repealed/interim/<ACT>_raw.txt
"""
import fitz  # PyMuPDF
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PDF = PROJECT_ROOT / "data" / "raw" / "Repealed_acts.pdf"
OUT_DIR = PROJECT_ROOT / "data" / "processed" / "repealed" / "interim"

# TOC book-page numbers (as printed in the E-Book itself)
TOC = [
    ("CAPITAL GAINS TAX ACT", 1),
    ("CASINO TAXATION ACT", 33),
    ("CHARTERED INSTITUTE OF TAXATION OF NIGERIA ACT", 47),
    ("COMPANIES INCOME TAX ACT", 72),
    ("DEEP OFFSHORE AND INLAND BASIN PRODUCTION SHARING CONTRACTS ACT", 177),
    ("FEDERAL INLAND REVENUE SERVICE (ESTABLISHMENT) ACT", 183),
    ("INCOME TAX (AUTHORISED COMMUNICATION) ACT", 232),
    ("INDUSTRIAL DEVELOPMENT (INCOME TAX RELIEF) ACT", 236),
    ("INDUSTRIAL INSPECTORATE ACT", 256),
    ("NATIONAL INFORMATION TECHNOLOGY DEVELOPMENT AGENCY ACT", 265),
    ("NIGERIA EXPORT PROCESSING ZONE ACT", 286),
    ("OIL AND GAS EXPORT FREE ZONE ACT", 305),
    ("PERSONAL INCOME TAX ACT", 321),
    ("PETROLEUM PROFITS TAX ACT", 426),
    ("STAMP DUTIES ACT", 486),
    ("TAXES AND LEVIES (APPROVED LIST FOR COLLECTION) ACT", 561),
    ("TERTIARY EDUCATION TRUST FUND (ESTABLISHMENT ETC.) ACT", 566),
    ("VALUE ADDED TAX ACT", 580),
    ("VENTURE CAPITAL (INCENTIVES) ACT", 605),
]

# Only these 11 are confirmed repealed by the Nigeria Tax Act 2025.
# The remaining 8 in the E-Book (FIRS Establishment Act, Chartered Institute of
# Taxation Act, Industrial Inspectorate Act, NITDA Act, Nigeria Export Processing
# Zone Act, Oil and Gas Export Free Zone Act, Taxes and Levies Act, TETFUND Act)
# are deliberately excluded — they are not part of the CITA/PITA-style repeal
# package and their status needs separate verification before inclusion.
REPEALED_ACTS = {
    "CAPITAL GAINS TAX ACT": {"cap": "Cap. C1 LFN 2004", "short": "CGTA"},
    "CASINO TAXATION ACT": {"cap": "Cap. C3 LFN 2004", "short": "CasinoAct"},
    "COMPANIES INCOME TAX ACT": {"cap": "Cap. C21 LFN 2004", "short": "CITA"},
    "DEEP OFFSHORE AND INLAND BASIN PRODUCTION SHARING CONTRACTS ACT": {"cap": "N/A", "short": "DeepOffshorePSC"},
    "INCOME TAX (AUTHORISED COMMUNICATION) ACT": {"cap": "N/A", "short": "IncomeTaxAuthComm"},
    "INDUSTRIAL DEVELOPMENT (INCOME TAX RELIEF) ACT": {"cap": "Cap. I7 LFN 2004", "short": "IndustrialDevRelief"},
    "PERSONAL INCOME TAX ACT": {"cap": "Cap. P8 LFN 2004", "short": "PITA"},
    "PETROLEUM PROFITS TAX ACT": {"cap": "Cap. P13 LFN 2004", "short": "PPTA"},
    "STAMP DUTIES ACT": {"cap": "Cap. S8 LFN 2004", "short": "SDA"},
    "VALUE ADDED TAX ACT": {"cap": "Cap. V1 LFN 2004", "short": "VATA"},
    "VENTURE CAPITAL (INCENTIVES) ACT": {"cap": "N/A", "short": "VentureCapitalAct"},
}


def pdf_index(book_page: int) -> int:
    """Confirmed offset: PDF 0-indexed page = book-printed page number + 1."""
    return book_page + 1


def main():
    if not SOURCE_PDF.exists():
        raise FileNotFoundError(
            f"Source PDF not found at {SOURCE_PDF}. "
            f"Place the E-Book PDF at data/raw/Repealed_acts.pdf first."
        )

    doc = fitz.open(str(SOURCE_PDF))
    total_pages = len(doc)

    ranges = []
    for i, (name, bp) in enumerate(TOC):
        start = pdf_index(bp)
        end = pdf_index(TOC[i + 1][1]) if i + 1 < len(TOC) else total_pages
        ranges.append((name, start, end))

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"{'Act':<70} {'Short':<20} {'PDF pages':<14} {'chars'}")
    for name, start, end in ranges:
        if name not in REPEALED_ACTS:
            continue
        text = "\n".join(doc[p].get_text() for p in range(start, end))
        short = REPEALED_ACTS[name]["short"]
        out_path = OUT_DIR / f"{short}_raw.txt"
        out_path.write_text(text, encoding="utf-8")
        print(f"{name:<70} {short:<20} {start+1}-{end:<10} {len(text)}")

    print(f"\nDone. Raw per-Act text written to {OUT_DIR}")


if __name__ == "__main__":
    main()
