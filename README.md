# fau-codepath-canvas-grade-importer

Weekly Codepath → Canvas grade import for **COP4655 001 18078** (iOS102 Fall 2026). The Canvas export also includes the combined grad section **COT5930 003 21217**; keep the filename / `config.json` patterns on COP4655.

Requires Python 3.13. New-semester reset: [`docs/new-semester.md`](docs/new-semester.md). End of term: [`docs/end-of-semester.md`](docs/end-of-semester.md).

## Weekly import

1. Export Canvas grades. Rename `Grades` → `Canvas`:

   `2026-09-14T2229_Grades-COP4655_001_18078.csv` → `2026-09-14T2229_Canvas-COP4655_001_18078.csv`

2. From the Codepath gradebook spreadsheet: **File → Download → CSV** and **XLS** (XLS is the archive copy):

   `2026-09-14T2229_Codepath-COP4655_001_18078.csv`  
   `2026-09-14T2229_Codepath-COP4655_001_18078.xlsx`

3. Put all three in `data/`. Timestamp must match. CSVs are gitignored.

4. If a new Codepath assignment is **due and being imported**, add it to `config.json` `Assignments`. Do not map a Canvas column whose Codepath assignment is not due yet — that writes zeros over Canvas.

5. Run:

   ```
   python3 0-updater.py
   ```

6. Review `data/*-updated.out`, then upload `data/*-updated.csv` back into Canvas.

`0-updater.py` runs:

1. `1-codepath-canvas-updater.py` — match on email (`SIS Login ID` ↔ Codepath `Email`), copy mapped scores into a Canvas upload CSV
2. `2-compare_grades.py` — diff vs the previous Canvas export (needs two Canvas files; skip on the first run of the semester)
3. `3-find_unsubmitted_assignments.py` — split **submitted (C) / incomplete (I) / missing (M)**

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
  | Proj 2 | 2819784 | `ASN - 2 Points` (due Sep 27 — unmapped until then) |

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
| `5-compare_final_grades.py` | End of term — pre-submit vs post-submit Canvas finals (hardcoded paths) |
| `6-find_codepath_completers_in_roster.py` | End of term — certificate / completer check |

Details: [`docs/end-of-semester.md`](docs/end-of-semester.md).
