"""Annotation pipeline step 3: validate dataset records against the schema.

A dependency-free validator driven by annotation/dataset_schema.json — the
schema file stays the single source of truth for required fields, enums and
patterns (adding a value there is enough; nothing is duplicated here).
Also checks two things a generic JSON-Schema validator cannot:

  - id uniqueness across the file
  - provenance.chunk_id actually exists in the provisions catalog

Run from the repo root (any records file, e.g. candidates or a final split):
    python src/annotation_pipeline/03_validate_dataset.py data/annotation/candidates.jsonl
"""

import json
import re
import sys
from pathlib import Path

SCHEMA_PATH = Path("annotation/dataset_schema.json")
PROVISIONS_PATH = Path("data/annotation/provisions.jsonl")


def check(record: dict, schema: dict, where: str, errors: list) -> None:
    props = schema["properties"]
    for field in schema["required"]:
        if field not in record:
            errors.append(f"{where}: missing required field '{field}'")
    for field, value in record.items():
        spec = props.get(field)
        if spec is None:
            errors.append(f"{where}: unknown field '{field}'")
            continue
        if spec.get("type") == "string" and not isinstance(value, str):
            errors.append(f"{where}: '{field}' must be a string")
            continue
        if "minLength" in spec and isinstance(value, str) and len(value) < spec["minLength"]:
            errors.append(f"{where}: '{field}' shorter than {spec['minLength']} chars")
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"{where}: '{field}' value {value!r} not in {spec['enum']}")
        if "pattern" in spec and isinstance(value, str) and not re.fullmatch(spec["pattern"], value):
            errors.append(f"{where}: '{field}' value {value!r} does not match {spec['pattern']}")
        if spec.get("type") == "object" and isinstance(value, dict):
            check(value, spec, f"{where}.{field}", errors)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: 03_validate_dataset.py <records.jsonl> [...]")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    known_chunks = set()
    if PROVISIONS_PATH.exists():
        with open(PROVISIONS_PATH, encoding="utf-8") as f:
            known_chunks = {json.loads(line)["chunk_id"] for line in f}

    total_errors = 0
    for arg in sys.argv[1:]:
        errors, ids = [], {}
        n = 0
        with open(arg, encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                n += 1
                where = f"{Path(arg).name}:{line_no}"
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"{where}: invalid JSON ({exc})")
                    continue
                check(record, schema, where, errors)
                rid = record.get("id")
                if rid in ids:
                    errors.append(f"{where}: duplicate id {rid!r} (first at {ids[rid]})")
                ids.setdefault(rid, where)
                chunk_id = record.get("provenance", {}).get("chunk_id", "")
                if known_chunks and chunk_id not in known_chunks:
                    errors.append(f"{where}: provenance.chunk_id {chunk_id!r} "
                                  "not found in provisions catalog")
        verdict = "PASS" if not errors else "FAIL"
        print(f"{arg}: {verdict} — {n} records, {len(errors)} error(s)")
        for e in errors[:30]:
            print("  ERROR:", e)
        total_errors += len(errors)
    if total_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
