# fau-codepath-canvas-grade-importer

Weekly Codepath → Canvas grade import for **COP4655 001 18078** (iOS102 Fall 2026). The Canvas export also includes the combined grad section **COT5930 003 21217**; keep the filename / `config.json` patterns on COP4655.

Requires Python 3.13. New-semester reset: [`docs/new-semester.md`](docs/new-semester.md). End of term: [`docs/end-of-semester.md`](docs/end-of-semester.md).

## Weekly import

1. Download fresh Canvas and CodePath grade files automatically:

   ```
   python3 0-download_gradebooks.py
   ```

   The script exports Canvas first, then downloads the CodePath spreadsheet as both CSV and XLSX. It saves matching timestamped files in `data/`. The script can fill the Google account ID automatically, but passwords and MFA remain manual. The login state is kept in `data/.playwright-chromium-profile/`.

2. If a new CodePath assignment is **due and being imported**, add it to `config.json` `Assignments`. Do not map a Canvas column whose CodePath assignment is not due yet — that writes zeros over Canvas.

3. Process the latest matching files:

   ```
   python3 1-process_grades.py
   ```

   This creates `data/*-updated.csv` and the review report `data/*-updated.out`.

4. Review the CSV and `.out` report. When ready, upload the processed CSV through the confirmation-gated Canvas uploader:

   ```
   python3 5-upload_gradebook.py
   ```

   The uploader requires typing `UPLOAD TO CANVAS` twice: once before opening the upload flow and again immediately before the final Canvas import action. It never uploads without those confirmations.

`1-process_grades.py` runs:

1. `2-codepath-canvas-updater.py` — match on email (`SIS Login ID` ↔ CodePath `Email`), copy mapped scores into a Canvas upload CSV
2. `3-compare_grades.py` — diff vs the previous Canvas export (needs two Canvas files; skip on the first run of the semester)
3. `4-find_unsubmitted_assignments.py` — split **submitted (C) / incomplete (I) / missing (M)**

## config.json

```json
{
    "CanvasCsvPattern": "Canvas-COP4655_001_18078",
    "CodepathCsvPattern": "Codepath-COP4655_001_18078",
    "HeadersToLookFor": ["Member ID", "Full Name"],
    "ColumnMapping": {
        "Email": "Email",
        "Status": "Status",
        "SIS Login ID": "SIS Login ID",
        "Assignments": {
            "Proj 1 (2819783)": "ASN - 1 Points"
        }
    }
}
```

- Patterns match `data/*_<pattern>.csv`. The latest timestamp wins.
- Assignment key = Canvas column **including** the numeric ID in parentheses.
- Assignment value = Codepath points/score column (`ASN - N Points` or `GM - N Score`).
- Add projects as they go live. Current Canvas IDs (do not map until due):

  | Canvas | ID | Codepath |
  |---|---|---|
  | Lab 0 | 2808311 | Canvas-only, not imported |
  | Lab 1 | 2819773 | Canvas-only |
  | Lab 2 | 2819774 | Canvas-only |
  | Proj 1 | 2819783 | `ASN - 1 Points` |
  | Proj 2 | 2819784 | `ASN - 2 Points` (mapped after Sep 27 due date) |

## Outputs

| File | What |
|---|---|
| `*-updated.csv` | Canvas upload file |
| `*-updated.out` | missing-from-Canvas emails, zeros on last mapped project, incomplete vs missing lists, stats table |
| Codepath temp CSV | stripped and deleted on success |

Step 1 still prints emails in Codepath but not Canvas. Investigate: email mismatch, dropped, or junk row (`#N/A`). Withdrawn / Dropped Codepath rows are skipped.

## Incomplete vs missing

Codepath status on each assignment:

- **C** — complete, has a score → **Submitted**
- **I** — submitted, scored 0 (instructions / README / video / zip / LabX-as-ProjX) → **Incomplete**
- **M** or blank — never submitted → **Unsubmitted**

The stats table in the `.out` is:

```
Project           | Submitted  | Incomplete  | Unsubmitted  | Total    | Percentage
```

Percentage is complete / total. Incomplete is **not** lumped into unsubmitted.

I students can resubmit through the Codepath portal **only inside the assignment window** (deadline + drop-dead). GitHub / README / video updates are not regraded unless they resubmit in the portal. Grading runs Sunday nights after 11:59pm.

Grading process doc in Canvas: https://canvas.fau.edu/courses/202165/files/48437643?module_item_id=6817598

## Other scripts

| Script | When |
|---|---|
| `compare_returning_students.py` | New semester — overlap vs previous Codepath course |
| `analyze_grades.py` | End of term — letter-grade distribution + 0.6% borderline list from `data/Final-Grades-*Canvas*.csv` |
| `6-compare_final_grades.py` | End of term — pre-submit vs post-submit Canvas finals (hardcoded paths) |
| `7-find_codepath_completers_in_roster.py` | End of term — certificate / completer check |

Details: [`docs/end-of-semester.md`](docs/end-of-semester.md).
