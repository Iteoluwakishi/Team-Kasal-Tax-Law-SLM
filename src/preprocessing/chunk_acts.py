"""
Phase 2 preprocessing — Step 2 (per assignment spec: Iteoluwa - REPEALED /
NEGATIVE TEST DATASET, Day 2 "Cleaning & Parsing").

Chunks each Act's raw text into section-level units tagged with legal
hierarchy (Part, Section), temporal metadata, and dataset-role metadata,
then writes one JSONL file per Act as specified.

Usage (from project root, after running extract_acts.py):
    python src/preprocessing/chunk_acts.py

Reads:  data/processed/repealed/interim/<ACT>_raw.txt
Writes: data/processed/repealed/pita.jsonl
        data/processed/repealed/cita.jsonl
        data/processed/repealed/vat.jsonl
        data/processed/repealed/cgt.jsonl
        data/processed/repealed/ppt.jsonl
        data/processed/repealed/stamp_duties.jsonl
"""
import re
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "data" / "processed" / "repealed" / "interim"
OUT_DIR = PROJECT_ROOT / "data" / "processed" / "repealed"

# Exactly the 6 Acts specified in the assignment. Output filename, document_id,
# and original_effective_date are per the Act's commencement clause in the
# consolidated text (LFN citation), used for original_effective_date metadata.
TARGET_ACTS = {
    "PITA": {
        "full_name": "Personal Income Tax Act",
        "cap": "Cap. P8 LFN 2004",
        "out_file": "pita.jsonl",
        "original_effective_date": "1993-01-01",  # PITA 1993, No. 104
    },
    "CITA": {
        "full_name": "Companies Income Tax Act",
        "cap": "Cap. C21 LFN 2004",
        "out_file": "cita.jsonl",
        "original_effective_date": "1979-04-01",  # 1979 No. 28
    },
    "VATA": {
        "full_name": "Value Added Tax Act",
        "cap": "Cap. V1 LFN 2004",
        "out_file": "vat.jsonl",
        "original_effective_date": "1993-12-01",  # VAT Act 1993, No. 102
    },
    "CGTA": {
        "full_name": "Capital Gains Tax Act",
        "cap": "Cap. C1 LFN 2004",
        "out_file": "cgt.jsonl",
        "original_effective_date": "1967-04-01",  # 1967 No. 44
    },
    "PPTA": {
        "full_name": "Petroleum Profits Tax Act",
        "cap": "Cap. P13 LFN 2004",
        "out_file": "ppt.jsonl",
        "original_effective_date": "1959-01-01",  # PPTA 1959
    },
    "SDA": {
        "full_name": "Stamp Duties Act",
        "cap": "Cap. S8 LFN 2004",
        "out_file": "stamp_duties.jsonl",
        "original_effective_date": "1939-01-01",  # Stamp Duties Act, colonial-era origin
    },
}

COMMON_META = {
    "status": "REPEALED",
    "dataset_role": "NEGATIVE_TEST",
    "repeal_status": "Repealed effective 2026-01-01",
    "replacement_legislation": "Nigeria Tax Act, 2025",
    "source": "E-Book of Tax and Related Laws (updated with Finance Act 2020 amendments), "
              "compiled by Kazeem Kayode Lawal FCA FCTI, FIRS, March 2021",
    "source_vintage_note": "Consolidated text current as of Finance Act 2020; "
                           "does not reflect Finance Act 2021-2023 amendments.",
}

SECTION_RE = re.compile(r'\n(\d{1,3}[A-Z]{0,2})\.\s{1,4}([A-Z][^\n]{2,100}?)\.?\s*\n')
PART_RE = re.compile(r'\n(PART\s+[IVXLC]+)\s*\n')
SCHEDULE_HEADING_RE = re.compile(
    r'\n((?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|'
    r'ELEVENTH|TWELFTH|THIRTEENTH)\s+SCHEDULE)\s*\n'
)


def find_body_start(text: str) -> int:
    idx = text.find('An Act')
    if idx == -1:
        idx = text.find('AN ACT')
    if idx == -1:
        return 0
    chap_idx = text.rfind('CHAPTER', 0, idx)
    return chap_idx if chap_idx != -1 else idx


def find_schedules_start(body: str) -> int:
    idx = body.find('\nSCHEDULES')
    if idx != -1:
        return idx
    m = SCHEDULE_HEADING_RE.search(body)
    return m.start() if m else len(body)


def build_part_lookup(body: str, limit: int) -> list[tuple[int, str]]:
    """Return sorted list of (char_offset, part_label) within body[:limit],
    skipping the arrangement-of-sections TOC occurrences (first duplicate run)."""
    marks = [(m.start(), m.group(1)) for m in PART_RE.finditer(body, 0, limit)]
    # The TOC (arrangement of sections) repeats Part I..N before the real body
    # does. Keep only the SECOND full pass onward if a duplicate run is detected.
    seen_once = set()
    real_start_idx = 0
    for i, (_, label) in enumerate(marks):
        if label in seen_once:
            real_start_idx = i
            break
        seen_once.add(label)
    return marks[real_start_idx:] if real_start_idx else marks


def part_at(offset: int, part_marks: list[tuple[int, str]]) -> str | None:
    current = None
    for pos, label in part_marks:
        if pos <= offset:
            current = label
        else:
            break
    return current


def chunk_act(short: str, full_text: str) -> list[dict]:
    body_start = find_body_start(full_text)
    body = full_text[body_start:]

    sched_start = find_schedules_start(body)
    principal_body = body[:sched_start]
    schedules_body = body[sched_start:]

    part_marks = build_part_lookup(principal_body, len(principal_body))

    chunks = []
    seq = 1

    # Principal sections
    matches = list(SECTION_RE.finditer(principal_body))
    prev_num = 0
    for i, m in enumerate(matches):
        sec_num_raw = m.group(1)
        num_digits = int(re.match(r'\d+', sec_num_raw).group())
        heading = m.group(2).strip()
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(principal_body)
        sec_text = principal_body[start:end].strip()
        if len(sec_text) < 30:
            continue
        if num_digits < prev_num - 2:
            continue
        prev_num = max(prev_num, num_digits)

        part_label = part_at(start, part_marks)

        chunks.append({
            "chunk_id": f"{short}_S{sec_num_raw}_{seq:03d}",
            "document_id": short,
            "act": TARGET_ACTS[short]["full_name"],
            "cap": TARGET_ACTS[short]["cap"],
            "unit_type": "section",
            "part": part_label,
            "section": sec_num_raw,
            "section_heading": heading,
            "original_effective_date": TARGET_ACTS[short]["original_effective_date"],
            "text": sec_text,
            **COMMON_META,
        })
        seq += 1

    # Schedules
    sched_headings = list(SCHEDULE_HEADING_RE.finditer(schedules_body))
    for i, m in enumerate(sched_headings):
        name = m.group(1).strip()
        start = m.start()
        end = sched_headings[i + 1].start() if i + 1 < len(sched_headings) else len(schedules_body)
        sched_text = schedules_body[start:end].strip()
        if len(sched_text) < 30:
            continue
        chunks.append({
            "chunk_id": f"{short}_{name.replace(' ', '_')}_{seq:03d}",
            "document_id": short,
            "act": TARGET_ACTS[short]["full_name"],
            "cap": TARGET_ACTS[short]["cap"],
            "unit_type": "schedule",
            "part": None,
            "section": name,
            "section_heading": name.title(),
            "original_effective_date": TARGET_ACTS[short]["original_effective_date"],
            "text": sched_text,
            **COMMON_META,
        })
        seq += 1

    return chunks


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"{'Act':<10} {'#Sections':<12} {'#Schedules':<12} {'output file'}")
    for short, cfg in TARGET_ACTS.items():
        raw_path = INTERIM_DIR / f"{short}_raw.txt"
        if not raw_path.exists():
            print(f"  [skip] {raw_path} not found — run extract_acts.py first")
            continue
        full_text = raw_path.read_text(encoding="utf-8")
        chunks = chunk_act(short, full_text)
        n_sections = sum(1 for c in chunks if c["unit_type"] == "section")
        n_schedules = sum(1 for c in chunks if c["unit_type"] == "schedule")

        out_path = OUT_DIR / cfg["out_file"]
        with open(out_path, "w", encoding="utf-8") as f:
            for c in chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")

        print(f"{short:<10} {n_sections:<12} {n_schedules:<12} {cfg['out_file']}")

    print(f"\nDone. JSONL files written to {OUT_DIR}")


if __name__ == "__main__":
    main()
