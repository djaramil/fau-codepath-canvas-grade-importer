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
AUTH_STATE_PATH = DATA_DIR / ".playwright-auth-state.json"
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
    """Wait out SSO redirects and pause for a manual login if needed.

    FAU SSO interstitial task screens ("FINISH LATER") are clicked through
    automatically.
    """
    def needs_auth() -> bool:
        try:
            if page.locator('input[type="password"]').is_visible(timeout=500):
                return True
        except Exception:
            pass
        url = page.url.lower()
        return "login" in url or "sso.fau.edu" in url

    def dismiss_sso_interstitial() -> None:
        try:
            finish_later = page.get_by_role(
                "button", name=re.compile(r"finish later", re.IGNORECASE)
            )
            if finish_later.is_visible(timeout=500):
                finish_later.click()
        except Exception:
            pass

    for _ in range(30):
        if not needs_auth():
            return
        dismiss_sso_interstitial()
        page.wait_for_timeout(1_000)

    input("Finish Canvas password/MFA login, then press Enter here to continue: ")

    for _ in range(30):
        if not needs_auth():
            return
        dismiss_sso_interstitial()
        page.wait_for_timeout(1_000)


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


def find_button(page: Page, pattern: str):
    controls = page.locator(
        "button:visible, input[type='submit']:visible, input[type='button']:visible"
    )
    labels = re.compile(pattern, re.IGNORECASE)
    for index in range(controls.count() - 1, -1, -1):
        control = controls.nth(index)
        label = control.get_attribute("value") or control.inner_text()
        if labels.search((label or "").strip()):
            return control
    return None


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
        browser = playwright.chromium.launch(headless=False)
        context_options = {"accept_downloads": True}
        if AUTH_STATE_PATH.exists():
            context_options["storage_state"] = str(AUTH_STATE_PATH)
        context = browser.new_context(**context_options)
        try:
            page = context.new_page()
            for _ in range(3):
                page.goto(CANVAS_URL, wait_until="domcontentloaded")
                wait_for_login_if_needed(page)
                if "/gradebook" in page.url:
                    break
            page.wait_for_load_state("networkidle")

            import_button = page.get_by_role("button", name=re.compile(r"^Import$", re.IGNORECASE))
            import_button.wait_for(state="visible", timeout=30_000)
            import_button.click()
            choose_file(page, file_path)

            print("The file is selected in Canvas but has not been imported yet.")
            if input(f'Type "{CONFIRMATION}" to perform the Canvas import: ') != CONFIRMATION:
                print("Upload cancelled before the final Canvas action.")
                return

            # Canvas gradebook import is two steps: "Upload Data" sends the CSV,
            # then a preview appears with "Save Changes" to commit the import.
            upload_button = page.get_by_role(
                "button", name=re.compile(r"upload data", re.IGNORECASE)
            ).first
            try:
                upload_button.wait_for(state="visible", timeout=30_000)
            except Exception:
                upload_button = find_button(
                    page, r"^(Upload Data|Upload|Process)$"
                )
            if upload_button is None or not upload_button.is_visible():
                raise RuntimeError(
                    "Canvas did not show an upload control. "
                    "Review the Canvas page and complete the import manually if needed."
                )
            upload_button.click()
            print("CSV uploaded. Waiting for the preview / save control...")

            final_button = None
            for _ in range(60):
                final_button = page.get_by_role(
                    "button",
                    name=re.compile(r"save changes|save|submit", re.IGNORECASE),
                ).first
                try:
                    if final_button.is_visible(timeout=500):
                        break
                except Exception:
                    final_button = None
                page.wait_for_timeout(1_000)
            if final_button is None:
                raise RuntimeError(
                    "Canvas did not show a final save control after upload. "
                    "Review the Canvas page and complete the import manually if needed."
                )
            final_button.click()
            print("Canvas import action submitted. Review Canvas for its completion status.")
        finally:
            try:
                context.storage_state(path=str(AUTH_STATE_PATH))
            except Exception:
                pass
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
