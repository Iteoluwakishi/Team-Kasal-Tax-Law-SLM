# Validation report — NRS corpus (Abdul)

Result: **PASS** — 0 error(s), 7 warning(s), 563 chunks across 24 documents.

## Statistics

| source | documents | chunks | total_chars | mean_chunk_chars | min_chunk_chars | max_chunk_chars | chunks_with_heading |
|---|---|---|---|---|---|---|---|
| NRSEA | 1 | 67 | 44624 | 666 | 63 | 4070 | 44 |
| JRBA | 1 | 98 | 59096 | 603 | 67 | 3436 | 64 |
| Circulars | 10 | 287 | 236309 | 823 | 42 | 2898 | 287 |
| FAQs | 1 | 97 | 23386 | 241 | 75 | 648 | 97 |
| Notices | 4 | 4 | 4501 | 1125 | 371 | 2244 | 4 |
| Press releases | 3 | 5 | 7875 | 1575 | 147 | 2661 | 5 |
| News | 4 | 5 | 5281 | 1056 | 184 | 2685 | 5 |

## Errors

- none

## Warnings

- identical text across documents: jrba_2025#066 (jrba.jsonl:67) == nrsea_2025#049 (nrsea.jsonl:50)
- identical text across documents: jrba_2025#068 (jrba.jsonl:69) == nrsea_2025#051 (nrsea.jsonl:52)
- identical text across documents: circular_2026_05#019 (nrs_guidance.jsonl:95) == circular_2026_03#030 (nrs_guidance.jsonl:54)
- nrs_news_106: no chunks — image-only source (poster kept in data/raw/guidance/images/, OCR pending)
- nrs_news_131: no chunks — image-only source (poster kept in data/raw/guidance/images/, OCR pending)
- nrs_press_release_135: no chunks — image-only source (poster kept in data/raw/guidance/images/, OCR pending)
- nrs_press_release_130: no chunks — image-only source (poster kept in data/raw/guidance/images/, OCR pending)
