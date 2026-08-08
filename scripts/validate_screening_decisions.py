#!/usr/bin/env python3
"""Validate an AI or human JSONL screening-decision file against its candidate queue."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


VALID_DECISIONS = {"include", "exclude", "needs_fulltext"}
VALID_CONFIDENCE = {"", "low", "medium", "high"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path.name}:{number} must be a JSON object.")
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate screening decisions without changing them.")
    parser.add_argument("candidates_jsonl", type=Path)
    parser.add_argument("decisions_jsonl", type=Path)
    args = parser.parse_args()
    try:
        candidates = load_jsonl(args.candidates_jsonl)
        decisions = load_jsonl(args.decisions_jsonl)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    candidate_ids = {str(row.get("record_id") or "") for row in candidates}
    seen: set[str] = set()
    errors: list[str] = []
    counts = {decision: 0 for decision in VALID_DECISIONS}
    for number, row in enumerate(decisions, 1):
        record_id = str(row.get("record_id") or "")
        decision = row.get("decision")
        if record_id not in candidate_ids:
            errors.append(f"row {number}: unknown record_id {record_id!r}")
        if record_id in seen:
            errors.append(f"row {number}: duplicate decision for {record_id!r}")
        seen.add(record_id)
        if decision not in VALID_DECISIONS:
            errors.append(f"row {number}: invalid decision {decision!r}")
        else:
            counts[decision] += 1
        if decision == "exclude" and not str(row.get("exclusion_reason_id") or "").strip():
            errors.append(f"row {number}: excluded record has no exclusion_reason_id")
        if str(row.get("confidence") or "") not in VALID_CONFIDENCE:
            errors.append(f"row {number}: confidence must be low, medium, high, or empty")
        if row.get("reviewer_type") == "ai" and row.get("human_final") is True:
            errors.append(f"row {number}: an AI decision cannot be human_final")
    if errors:
        print("Screening decision validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 3
    print(f"Candidates: {len(candidates)}")
    print(f"Decisions: {len(decisions)}")
    for decision in sorted(counts):
        print(f"{decision}: {counts[decision]}")
    print(f"Undecided: {len(candidate_ids - seen)}")
    if not decisions:
        print("No decisions found; this is not a reviewed screening result.", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
