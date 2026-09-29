#!/usr/bin/env python3
"""Upload the latest processed Canvas CSV after explicit confirmation.

The script opens the Canvas gradebook, selects the latest *-updated.csv file,
and stops for confirmation immediately before the final Canvas import action.
It never submits a file without the user typing the confirmation phrase.
"""

import argparse
import re
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


CANVAS_URL = "https://canvas.fau.edu/courses/202165/gradebook?cid=4e69fa96-ff33-4748-bc3c-36479212eac2"
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
BROWSER_PROFILE_DIR = DATA_DIR / ".playwright-chromium-profile"
CONFIRMATION = "UPLOAD TO CANVAS"


def latest_updated_csv() -> Path:
    files = [
        path for path in DATA_DIR.glob("*_Canvas-*-updated.csv")
        if path.is_file()
    ]
    if not files:
        raise FileNotFoundError("No processed Canvas CSV files were found in data/")
    return max(files, key=lambda path: path.stat().st_mtime)


def wait_for_login_if_needed(page: Page) -> None:
    login_visible = page.locator('input[type="password"]').is_visible(timeout=3_000)
    if not login_visible and "login" not in page.url.lower():
        return
    input("Finish Canvas password/MFA login, then press Enter here to continue: ")


def choose_file(page: Page, file_path: Path) -> None:
    file_input = page.locator('input[type="file"]').first
    try:
        file_input.wait_for(state="attached", timeout=5_000)
    except Exception:
        choose_file_button = page.get_by_role(
            "button", name=re.compile(r"Choose File|Browse", re.IGNORECASE)
        ).first
        choose_file_button.click()
        file_input.wait_for(state="attached", timeout=10_000)
    file_input.set_input_files(str(file_path))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        type=Path,
        help="Specific processed Canvas CSV to upload instead of the latest one.",
    )
    args = parser.parse_args()
    file_path = args.file.resolve() if args.file else latest_updated_csv()
    if not file_path.exists():
        raise FileNotFoundError(f"Upload file not found: {file_path}")

    print(f"Selected upload file: {file_path}")
    print("Review the CSV and the corresponding .out report before continuing.")
    if input(f'Type "{CONFIRMATION}" to open the Canvas upload flow: ') != CONFIRMATION:
        print("Upload cancelled.")
        return

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(BROWSER_PROFILE_DIR),
            accept_downloads=True,
            headless=False,
        )
        try:
            page = context.new_page()
            page.goto(CANVAS_URL, wait_until="domcontentloaded")
            wait_for_login_if_needed(page)
            page.wait_for_load_state("networkidle")

            import_button = page.get_by_role("button", name=re.compile(r"^Import$", re.IGNORECASE))
            import_button.wait_for(state="visible", timeout=30_000)
            import_button.click()
            choose_file(page, file_path)

            print("The file is selected in Canvas but has not been imported yet.")
            if input(f'Type "{CONFIRMATION}" to perform the Canvas import: ') != CONFIRMATION:
                print("Upload cancelled before the final Canvas action.")
                return

            final_button = page.get_by_role(
                "button", name=re.compile(r"^(Upload|Process|Import)$", re.IGNORECASE)
            ).last
            final_button.wait_for(state="visible", timeout=15_000)
            final_button.click()
            print("Canvas import action submitted. Review Canvas for its completion status.")
        finally:
            try:
                context.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
