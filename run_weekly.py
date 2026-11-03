#!/usr/bin/env python3
"""One-command weekly grade import: download, process, offer upload.

Runs `0-download_gradebooks.py` (headed, so SSO/MFA can be done in the opened
browser), then `1-process_grades.py`, prints the review report tail, and asks
before launching `5-upload_gradebook.py`.

Usage:
    python3 run_weekly.py
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"


def latest_report() -> Path | None:
    reports = sorted(DATA_DIR.glob("*-updated.out"), key=lambda p: p.stat().st_mtime)
    return reports[-1] if reports else None


def run(script: str) -> bool:
    result = subprocess.run([sys.executable, str(SCRIPT_DIR / script)])
    return result.returncode == 0


def main() -> None:
    print("=== Step 1/3: Download gradebooks ===")
    if not run("0-download_gradebooks.py"):
        sys.exit("Download failed — see errors above.")

    print("\n=== Step 2/3: Process grades ===")
    if not run("1-process_grades.py"):
        sys.exit("Processing failed — see errors above.")

    report = latest_report()
    if report:
        print(f"\nReview report: {report}")

    print("\n=== Step 3/3: Upload ===")
    answer = input("Open the Canvas uploader now? [y/N] ").strip().lower()
    if answer == "y":
        run("5-upload_gradebook.py")
    else:
        print("Skipped. Upload later with: python3 5-upload_gradebook.py")


if __name__ == "__main__":
    main()
