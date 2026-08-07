#!/usr/bin/env python3
"""Build a legal-full-text input set from reviewed narrative-review extraction."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def text(value: Any) -> str:
    return str(value or "").strip()


def doi_key(value: Any) -> str:
    value = text(value).casefold()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    return value.rstrip(" .;,")


def pmid_key(value: Any) -> str:
    match = re.search(r"\d{4,10}", text(value))
    return match.group(0) if match else ""


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def record_list(payload: Any, label: str) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        payload = payload.get("records", payload.get("studies", []))
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError(f"{label} must be a JSON list or object containing records/studies.")
    return payload


def is_verified(study: dict[str, Any]) -> bool:
    return study.get("verified") is True


def resolve(records: list[dict[str, Any]], studies: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, str]], int]:
    by_doi = {doi_key(record.get("doi")): record for record in records if doi_key(record.get("doi"))}
    by_pmid = {pmid_key(record.get("pmid")): record for record in records if pmid_key(record.get("pmid"))}
    selected: list[dict[str, Any]] = []
    unmatched: list[dict[str, str]] = []
    skipped_unverified = 0
    seen: set[tuple[str, str]] = set()

    for study in studies:
        if not is_verified(study):
            skipped_unverified += 1
            continue
        doi = doi_key(study.get("doi"))
        pmid = pmid_key(study.get("pmid"))
        record = by_doi.get(doi) if doi else None
        record = record or (by_pmid.get(pmid) if pmid else None)
        if not record:
            unmatched.append({"pmid": pmid, "doi": doi, "citation": text(study.get("citation"))})
            continue
        key = (doi_key(record.get("doi")), pmid_key(record.get("pmid")))
        if key in seen:
            continue
        seen.add(key)
        selected.append(record)
    return selected, unmatched, skipped_unverified


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Select verified included records from a narrative-review extraction."
    )
    parser.add_argument("records_json", type=Path, help="Narrative-review records.json")
    parser.add_argument("extraction_json", type=Path, help="Reviewed extraction.json")
    parser.add_argument("output_json", type=Path, help="Selected input for retrieve_fulltext.py")
    args = parser.parse_args()

    try:
        records = record_list(load_json(args.records_json), "records_json")
        studies = record_list(load_json(args.extraction_json), "extraction_json")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2

    selected, unmatched, skipped_unverified = resolve(records, studies)
    payload = {
        "records": selected,
        "selection": {
            "selection_rule": "verified extraction studies matched by DOI, then PMID",
            "source_records": str(args.records_json.resolve()),
            "source_extraction": str(args.extraction_json.resolve()),
            "selected_count": len(selected),
            "unmatched_count": len(unmatched),
            "skipped_unverified_count": skipped_unverified,
            "unmatched": unmatched,
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Selected verified included records: {len(selected)}")
    print(f"Unmatched verified studies: {len(unmatched)}")
    print(f"Skipped unverified studies: {skipped_unverified}")
    print(f"Output: {args.output_json.resolve()}")
    if not selected:
        print("No verified included studies were selected; do not start PDF retrieval.", file=sys.stderr)
        return 3
    if unmatched:
        print("Resolve unmatched verified studies before describing the download set as complete.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
