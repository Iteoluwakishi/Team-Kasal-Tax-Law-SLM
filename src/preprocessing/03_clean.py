"""Stage 03: Clean extracted text.

Reads the stage-02 interim JSONs for documents assigned to "abdul" and writes
cleaned versions to data/interim/cleaned/, removing PDF artifacts while
preserving the structure stage 04 needs:

Acts (gazette layout, measured from the real PDFs):
  - the running header is the single line at the top of each page
    ("A 236  2025 No. 4  Nigeria Revenue Service (Establishment) Act, 2025");
    it is removed, and the gazette page label ("A 236") kept as metadata
  - section headings are printed in the OUTER PAGE MARGIN (right margin on
    odd pages, left on even pages) and pdfplumber merges them into body
    lines. Words are re-split into body vs margin using x-coordinates:
    a margin word sits entirely left of the page's median line start, or
    starts right of the median line end. Margin notes are recovered as
    headings with their vertical position, so stage 04 can attach each one
    to the section that starts at the same height.
  - body text is kept as lines WITH their y-position (stage 04 joins lines
    into section text and mends hyphenated line breaks at that point)

Circulars:
  - bare page-number footer lines and "Internal" watermark lines removed

Web snapshots (FAQ / notices / press releases / news):
  - already clean; whitespace and unicode normalised only

Run from the repo root:
    python src/preprocessing/03_clean.py
"""

import json
import re
import statistics
import unicodedata
from pathlib import Path

import pandas as pd

METADATA_CSV = Path("data/metadata/documents.csv")
INTERIM_DIR = Path("data/interim")
CLEAN_DIR = Path("data/interim/cleaned")

ASSIGNEE = "abdul"

LINE_TOP_TOLERANCE = 3.0   # words within this vertical distance form one line
# Margin classification thresholds, measured on the real gazettes.
# LEFT margin (verso pages): margin words start at x≈103-144 and body words at
# x≈148+, so no fixed offset from the median line start separates them safely.
# Instead: a line whose FIRST word starts far left of the body column
# (median-40) opens with margin words, and the margin ends at the first large
# horizontal jump between words (margin-internal gaps are 2-6pt; the jump to
# body text is 20-41pt).
MARGIN_LEFT_ANCHOR = 40.0    # line starts this far left of median => margin line
MARGIN_LEFT_GAP_SPLIT = 12.0  # first inter-word gap >= this ends the margin part
# RIGHT margin (recto pages): margin words start past the body column's median
# right edge; the simple offset rule has produced no errors on either act.
MARGIN_GAP_RIGHT = 6.0
MARGIN_NOTE_LINE_GAP = 14  # max vertical gap between lines of one margin note
HEADER_TOP_LIMIT = 170     # running headers sit at top≈151 in these gazettes

GAZETTE_LABEL_RE = re.compile(r"\b([AB]\s?\d{3})\b")
PAGE_NUMBER_RE = re.compile(r"^\d{1,3}$")


def normalise(text: str) -> str:
    """Unicode-normalise and tidy whitespace without changing content."""
    text = unicodedata.normalize("NFC", text)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def group_lines(words: list) -> list:
    """Group words into lines by vertical position; returns lines sorted
    top-to-bottom, words within a line sorted left-to-right."""
    lines = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(w["top"] - lines[-1][0]["top"]) <= LINE_TOP_TOLERANCE:
            lines[-1].append(w)
        else:
            lines.append([w])
    for line in lines:
        line.sort(key=lambda w: w["x0"])
    return lines


def join_margin_words(margin_words: list) -> list:
    """Group margin words into notes by vertical adjacency and mend
    hyphenated wraps ('Commence-' + 'ment' -> 'Commencement')."""
    notes = []
    for w in sorted(margin_words, key=lambda w: w["top"]):
        if notes and w["top"] - notes[-1]["words"][-1]["top"] <= MARGIN_NOTE_LINE_GAP:
            notes[-1]["words"].append(w)
        else:
            notes.append({"words": [w]})
    out = []
    for note in notes:
        text = ""
        for w in note["words"]:
            # mend wrap-hyphens ("Commence-" + "ment") but keep true hyphens
            # in compounds ("Accountant-" + "General" starts uppercase)
            if text.endswith(("-", "–", "‑")) and w["t"][:1].islower():
                text = text[:-1] + w["t"]
            elif text:
                text += " " + w["t"]
            else:
                text = w["t"]
        out.append({"top": round(note["words"][0]["top"], 1), "text": text})
    return out


def clean_act_page(page: dict) -> dict:
    """Split one gazette page into header, body lines and margin notes."""
    words = page["words"]
    result = {"page": page["page"], "gazette_label": "", "lines": [], "margin_notes": []}
    if not words:
        return result

    lines = group_lines(words)

    # Running header: the topmost line, when it sits in the header band and
    # carries the gazette page label or the act title.
    first_text = " ".join(w["t"] for w in lines[0])
    if lines[0][0]["top"] < HEADER_TOP_LIMIT:
        label = GAZETTE_LABEL_RE.search(first_text)
        if label or "No." in first_text:
            result["gazette_label"] = label.group(1).replace(" ", "") if label else ""
            lines = lines[1:]

    if not lines:
        return result

    # Body column bounds from the median line start/end. Margin notes are the
    # only text outside those bounds (verified against the real PDFs: the gap
    # between margin and body exceeds 19pt on every measured page).
    starts = [min(w["x0"] for w in line) for line in lines]
    ends = [max(w["x1"] for w in line) for line in lines]
    m_start = statistics.median(starts)
    m_end = statistics.median(ends)

    # The margin sits on ONE side per page: right on recto (odd gazette page
    # number), left on verso (even). Applying both rules misclassifies body
    # lines that outdent past the median, so pick the side first — from the
    # gazette label's parity, falling back to whichever side has more
    # out-of-column words.
    def left_margin_words(line):
        if line[0]["x0"] >= m_start - MARGIN_LEFT_ANCHOR:
            return []
        margin = [line[0]]
        for prev, w in zip(line, line[1:]):
            if w["x0"] - prev["x1"] >= MARGIN_LEFT_GAP_SPLIT:
                break
            margin.append(w)
        return margin

    def right_margin_words(line):
        return [w for w in line if w["x0"] > m_end + MARGIN_GAP_RIGHT]

    label_no = re.search(r"\d+", result["gazette_label"] or "")
    per_line = left_margin_words if (
        (label_no and int(label_no.group()) % 2 == 0)
        or (not label_no and sum(len(left_margin_words(l)) for l in lines)
            > sum(len(right_margin_words(l)) for l in lines))
    ) else right_margin_words

    body_words, margin_words = [], []
    for line in lines:
        in_margin = {id(w) for w in per_line(line)}
        for w in line:
            (margin_words if id(w) in in_margin else body_words).append(w)

    for line in group_lines(body_words):
        text = " ".join(w["t"] for w in line)
        result["lines"].append({"top": round(line[0]["top"], 1), "text": text})
    result["margin_notes"] = join_margin_words(margin_words)
    return result


def clean_circular_page(page: dict) -> dict:
    """Drop page-number footers and 'Internal' watermark lines."""
    lines = group_lines(page["words"])
    kept = []
    for line in lines:
        text = " ".join(w["t"] for w in line)
        if PAGE_NUMBER_RE.match(text.strip()):
            continue
        if text.strip() == "Internal":
            continue
        kept.append({"top": round(line[0]["top"], 1), "text": text})
    return {"page": page["page"], "lines": kept}


def clean_document(doc_meta: pd.Series, interim: dict) -> dict:
    doc_type = doc_meta["document_type"]
    cleaned = {
        key: interim[key]
        for key in ("document_id", "title", "document_type", "legal_weight",
                    "status", "source_file")
        if key in interim
    }
    for key in ("source_url", "retrieved", "image"):
        if key in interim:
            cleaned[key] = interim[key]

    if doc_type == "faq":
        cleaned["faq_items"] = [
            {
                "question": normalise(item["question"]),
                "answer": normalise(item["answer"]),
                "topic": normalise(item["topic"]),
            }
            for item in interim["faq_items"]
        ]
    elif doc_type in ("notice", "press_release", "news"):
        cleaned["pages"] = [
            {"page": p["page"], "text": normalise(p["text"])}
            for p in interim["pages"]
        ]
    elif doc_type == "act":
        cleaned["pages"] = [clean_act_page(p) for p in interim["pages"]]
    elif doc_type == "circular":
        cleaned["pages"] = [clean_circular_page(p) for p in interim["pages"]]
    else:
        raise ValueError(f"No cleaning rule for document_type '{doc_type}'")
    return cleaned


def main() -> None:
    df = pd.read_csv(METADATA_CSV, encoding="utf-8-sig").fillna("")
    mine = df[df["assigned_to"] == ASSIGNEE]
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)

    for _, doc in mine.iterrows():
        src = INTERIM_DIR / f"{doc['document_id']}.json"
        if not src.exists():
            print(f"WARNING: missing interim file {src} — run 02_extract.py")
            continue
        with open(src, encoding="utf-8") as f:
            interim = json.load(f)
        cleaned = clean_document(doc, interim)
        out = CLEAN_DIR / f"{doc['document_id']}.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(cleaned, f, ensure_ascii=False, indent=1)

        if "faq_items" in cleaned:
            print(f"{doc['document_id']}: {len(cleaned['faq_items'])} Q&A pairs cleaned")
        else:
            n_margin = sum(len(p.get("margin_notes", [])) for p in cleaned["pages"])
            n_lines = sum(len(p["lines"]) for p in cleaned["pages"] if "lines" in p)
            extra = f", {n_margin} margin headings" if n_margin else ""
            print(f"{doc['document_id']}: {len(cleaned['pages'])} pages, {n_lines} lines{extra}")


if __name__ == "__main__":
    main()
