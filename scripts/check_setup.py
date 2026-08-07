#!/usr/bin/env python3
"""Offline readiness check for the literature-review-pdfs skill."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_FILES = (
    ROOT / "SKILL.md",
    ROOT / "requirements.txt",
    ROOT / "scripts" / "run_pipeline.py",
    ROOT / "scripts" / "prepare_fulltext_input.py",
    ROOT / "scripts" / "retrieve_fulltext.py",
)
HELP_SCRIPTS = (
    ROOT / "scripts" / "run_pipeline.py",
    ROOT / "scripts" / "prepare_fulltext_input.py",
    ROOT / "scripts" / "retrieve_fulltext.py",
)


def mark(ok: bool, message: str) -> None:
    print(f"[{'OK' if ok else 'X '}] {message}")


def main() -> int:
    failed = False
    version_ok = sys.version_info >= (3, 10)
    mark(version_ok, f"Python {sys.version.split()[0]} (need 3.10+)")
    failed |= not version_ok

    for path in REQUIRED_FILES:
        exists = path.is_file()
        mark(exists, f"Found {path.relative_to(ROOT)}")
        failed |= not exists

    try:
        import openpyxl  # type: ignore
        mark(True, f"openpyxl {openpyxl.__version__}")
    except ImportError:
        mark(False, "openpyxl is not installed. Run: py -3 -m pip install -r requirements.txt")
        failed = True

    email = os.environ.get("NCBI_EMAIL", "").strip()
    email_ok = bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))
    mark(email_ok, "NCBI_EMAIL is set" if email_ok else "NCBI_EMAIL is not set or is not a valid email")
    if not email_ok:
        print('     Before searching PubMed, run: $env:NCBI_EMAIL = "you@example.org"')

    for script in HELP_SCRIPTS:
        if not script.is_file():
            continue
        try:
            result = subprocess.run(
                [sys.executable, str(script), "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            ok = result.returncode == 0
        except OSError as exc:
            ok = False
            print(f"     Could not start the current Python interpreter: {exc}")
        mark(ok, f"Offline command check: scripts/{script.name} --help")
        failed |= not ok

    if failed:
        print("\nSetup is incomplete. Fix the items marked [X ] and run this check again.")
        return 1
    if not email_ok:
        print("\nThe skill is installed. Set NCBI_EMAIL before your first PubMed search.")
        return 0
    print("\nReady. You can start with examples/query.scoping.example.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
