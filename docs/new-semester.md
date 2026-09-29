# New semester reset

Do this once when this repo is copied into a new course folder. Weekly import is in [`README.md`](../README.md).

This repo is reused every term. `data/` is gitignored; last term's CSVs will still be on disk until you wipe them.

## 1. Confirm last term is archived elsewhere

Do **not** wipe `data/` until a copy exists in that course's own `Grades/data/`.

Fall 2026 setup used:

| Term | Folder | Course pattern |
|---|---|---|
| Fall 2025 mobile | `Mobile-App-Fall-2025/Grades` | `COP4655_001_13208` |
| Spring 2026 web | `FullStackWeb-Spring-2026/Grades` | `COP4808_001_13815` |
| Fall 2026 mobile (this folder) | `Mobile-App-Fall-2026/Grades` | `COP4655_001_18078` |

## 2. Wipe last term's working files

```bash
rm -f data/*.{csv,xlsx,out} next-semester/*.csv
```

Keep the `data/` directory. Delete leftover end-of-term artifacts (`borderline_students.md`, `Final-Grades-*` copies you don't need). Leave the Python scripts, including `analyze_grades.py`.

## 3. Point config at the new Canvas export name

Canvas downloads as `YYYY-MM-DDTHHMM_Grades-<COURSE>_<SEC>_<CRN>.csv`. Rename `Grades` → `Canvas` for every import.

`config.json`:

```json
{
    "CanvasCsvPattern": "Canvas-<COURSE>_<SEC>_<CRN>",
    "CodepathCsvPattern": "Codepath-<COURSE>_<SEC>_<CRN>",
    "HeadersToLookFor": ["Member ID", "Full Name"],
    "ColumnMapping": {
        "Email": "Email",
        "Status": "Status",
        "SIS Login ID": "SIS Login ID",
        "Assignments": {}
    }
}
```

Leave `Assignments` empty until the first Codepath assignment is due **and** you have the Canvas column ID from a grades export header (`Proj 1 (2819783)`).

Combined sections (undergrad + grad) still use **one** filename / pattern — whatever Canvas puts in the download name. Fall 2026: COP4655 + COT5930 in one file, pattern stays `COP4655_001_18078`.

Labs are Canvas-only. Do not map them to `ASN - N Points`.

## 4. First exports into `data/`

Same naming as weekly:

```
YYYY-MM-DDTHHMM_Canvas-<COURSE>_<SEC>_<CRN>.csv
YYYY-MM-DDTHHMM_Codepath-<COURSE>_<SEC>_<CRN>.csv
YYYY-MM-DDTHHMM_Codepath-<COURSE>_<SEC>_<CRN>.xlsx
```

Open the Canvas header row, copy the project column names **exactly** (including the ID). Open Codepath row with `Member ID` / `Full Name` and confirm `ASN - 1 Points` (and later `GM - N Score`).

Map **only due assignments**:

```json
"Assignments": {
    "Proj 1 (2819783)": "ASN - 1 Points"
}
```

If Canvas already has Proj 2 but Codepath ASN-2 is not due, leave it out. Mapping it will stamp 0s into Canvas for everyone.

## 5. Update hardcoded paths

| File | What to change |
|---|---|
| `README.md` | Course pattern, assignment table, example filenames |
| `compare_returning_students.py` | New roster/Canvas file vs previous term's final Canvas export |
| `1-process_grades.py` | Comment is just a reminder; real mapping is `config.json` |
| `6-compare_final_grades.py` | End of term only — hardcoded paths, see [`end-of-semester.md`](end-of-semester.md) |
| `analyze_grades.py` | End of term — auto-picks `data/Final-Grades-*Canvas*.csv`; no path edit unless the naming convention changes |

## 6. Returning students

`compare_returning_students.py` matches on `SIS Login ID` (email), case-insensitive.

Compare against the **previous Codepath course in the sequence**, not the same-number course a year ago, unless you specifically want retakes.

Fall 2026: 25/162 from Spring 2026 COP4808 (15.4%). 0 retakes from Fall 2025 COP4655.

## 7. First pipeline run

```bash
python3 1-process_grades.py
```

Expected on run 1: step 2 cannot diff (only one Canvas file). Step 1 + 3 still run.

Check:

- `*-updated.csv` before Canvas upload
- Codepath-not-in-Canvas emails (`#N/A` is a junk row; others are drops or email mismatches)
- Incomplete (I/0) vs missing (M) lists in the `.out`

Email those two groups separately. Incomplete can still resubmit until drop-dead. Missing has not submitted; after drop-dead a 0 is final.

## 8. After that

Weekly process in the README. Add the next `Assignments` entry when that project is due, using the Canvas ID from a fresh grades export — IDs change every semester.

End-of-term borderline / finals posting: [`end-of-semester.md`](end-of-semester.md).
