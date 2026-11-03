#!/usr/bin/env python3
"""Download the Canvas gradebook and CodePath spreadsheet exports.

The first run opens a Playwright browser. Authentication state is saved in
an ignored local file so later runs can reuse the Canvas and Google sessions.
If either site expires the session, log in in the opened browser and continue.
"""

import argparse
import re
from datetime import datetime
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, sync_playwright


COURSE_ID = "COP4655_001_18078"
CANVAS_URL = "https://canvas.fau.edu/courses/202165/gradebook?cid=4e69fa96-ff33-4748-bc3c-36479212eac2"
CODEPATH_SHEET_ID = "1qZvNaYp28qw108fh4SyXGbQZO8lkX7uqZzH923Y3jqE"
CODEPATH_SHEET_GID = "1915715505"
CANVAS_ACCOUNT_EMAIL = "djaramil@fau.edu"
GOOGLE_ACCOUNT_EMAIL = "djaramil@fau.edu"

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
AUTH_STATE_PATH = DATA_DIR / ".playwright-auth-state.json"


def remove_partial_downloads() -> None:
    for partial_file in DATA_DIR.glob("*.crdownload"):
        partial_file.unlink()


def wait_for_login_if_needed(page: Page, site_name: str) -> None:
    """Pause for a manual login when the site redirects to an auth page.

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

    # SSO sessions can auto-redirect through login/SSO URLs; give them time to
    # resolve, clicking through FAU SSO interstitials along the way.
    for _ in range(30):
        if not needs_auth():
            return
        dismiss_sso_interstitial()
        page.wait_for_timeout(1_000)

    if site_name in ("Canvas", "Google Sheets"):
        email_field = page.locator(
            'input[type="email"], input[name="identifier"], input[name="username"]'
        ).first
        if email_field.is_visible(timeout=3_000):
            account_email = (
                CANVAS_ACCOUNT_EMAIL if site_name == "Canvas" else GOOGLE_ACCOUNT_EMAIL
            )
            if not email_field.input_value():
                email_field.fill(account_email)
            next_button = page.get_by_role(
                "button", name=re.compile(r"^(Next|Continue|Log In)$", re.IGNORECASE)
            ).first
            if next_button.is_visible(timeout=3_000):
                next_button.click()

    print(f"{site_name} requires authentication in the browser window.")
    input("Finish the password/MFA steps, then press Enter here to continue: ")

    # Post-login SSO bounces can land on interstitials again; settle them too.
    for _ in range(30):
        if not needs_auth():
            return
        dismiss_sso_interstitial()
        page.wait_for_timeout(1_000)


def canvas_filename(download_name: str) -> tuple[str, str]:
    """Create the project's canonical Canvas filename from Canvas's download."""
    timestamp_match = re.search(r"\d{4}-\d{2}-\d{2}T\d{4}", download_name)
    timestamp = timestamp_match.group(0) if timestamp_match else datetime.now().strftime("%Y-%m-%dT%H%M")

    extension = Path(download_name).suffix.lower() or ".csv"
    return f"{timestamp}_Canvas-{COURSE_ID}{extension}", timestamp


def download_canvas(context: BrowserContext) -> tuple[Path, str]:
    page = context.new_page()
    print("Opening Canvas gradebook...")
    for _ in range(3):
        page.goto(CANVAS_URL, wait_until="domcontentloaded")
        wait_for_login_if_needed(page, "Canvas")
        if "/gradebook" in page.url:
            break
    page.wait_for_load_state("networkidle")

    export_button = page.get_by_role("button", name=re.compile(r"^Export"))
    export_button.wait_for(state="visible", timeout=30_000)
    export_button.click()

    export_entire = page.get_by_text("Export Entire Gradebook", exact=True)
    export_entire.wait_for(state="visible", timeout=10_000)
    with page.expect_download(timeout=60_000) as download_info:
        export_entire.click()

    download = download_info.value
    filename, timestamp = canvas_filename(download.suggested_filename)
    destination = DATA_DIR / filename
    download.save_as(destination)
    page.close()
    print(f"Downloaded Canvas: {destination.name}")
    return destination, timestamp


def download_codepath(context: BrowserContext, timestamp: str) -> list[Path]:
    page = context.new_page()
    sheet_url = f"https://docs.google.com/spreadsheets/d/{CODEPATH_SHEET_ID}/edit?gid={CODEPATH_SHEET_GID}"
    print("Opening CodePath spreadsheet...")
    for _ in range(3):
        page.goto(sheet_url, wait_until="domcontentloaded")
        wait_for_login_if_needed(page, "Google Sheets")
        if CODEPATH_SHEET_ID in page.url:
            break

    export_files = []
    for format_name, extension in (("csv", ".csv"), ("xlsx", ".xlsx")):
        export_url = (
            f"https://docs.google.com/spreadsheets/d/{CODEPATH_SHEET_ID}/export"
            f"?format={format_name}&gid={CODEPATH_SHEET_GID}"
        )
        destination = DATA_DIR / f"{timestamp}_Codepath-{COURSE_ID}{extension}"
        print(f"Downloading CodePath {format_name.upper()}...")
        response = context.request.get(export_url, timeout=60_000)
        if response.status in (401, 403):
            page.bring_to_front()
            print("Google Sheets authentication is required in the browser window.")
            input("Finish Google login/MFA, then press Enter here to retry: ")
            page.goto(sheet_url, wait_until="domcontentloaded")
            wait_for_login_if_needed(page, "Google Sheets")
            response = context.request.get(export_url, timeout=60_000)
        if not response.ok:
            raise RuntimeError(
                f"Google Sheets returned HTTP {response.status} for the {format_name.upper()} export. "
                "Check that the sheet is accessible to the logged-in account."
            )
        destination.write_bytes(response.body())
        export_files.append(destination)
        print(f"Downloaded CodePath: {destination.name}")

    page.close()
    return export_files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without opening a visible browser (requires existing login state).",
    )
    args = parser.parse_args()

    DATA_DIR.mkdir(exist_ok=True)
    remove_partial_downloads()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=args.headless)
        context_options = {"accept_downloads": True}
        if AUTH_STATE_PATH.exists():
            context_options["storage_state"] = str(AUTH_STATE_PATH)
        context = browser.new_context(**context_options)
        try:
            _, timestamp = download_canvas(context)
            download_codepath(context, timestamp)
        finally:
            try:
                context.storage_state(path=str(AUTH_STATE_PATH))
            except Exception:
                pass
            context.close()
            browser.close()

    print(f"All downloads saved in {DATA_DIR}")


if __name__ == "__main__":
    main()
