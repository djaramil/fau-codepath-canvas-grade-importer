# End-of-semester processing

Weekly import stays in [`README.md`](../README.md). Do this after the last Codepath assignment is imported and Canvas finals are ready to post.

## 1. Last Codepath import

Same weekly process. `config.json` `Assignments` should include every Codepath column you are posting (projects + final project / GM columns). Do not map Canvas-only labs.

Run `python3 0-updater.py`, sanity-check `*-updated.csv`, upload to Canvas.

## 2. Export Canvas finals

Download grades from Canvas and keep a dated copy **before** you post letter grades:

```
data/Final-Grades-YYYY-MM-DDTHHMM_Canvas-COP4655_001_18078.csv
```

The `Final-Grades-` prefix is what `analyze_grades.py` looks for. Do not reuse the weekly `YYYY-MM-DDTHHMM_Canvas-...` name for this file or a later weekly drop will look like the finals file.

After you submit grades in Canvas, download again as:

```
data/Final-Grades-YYYY-MM-DDTHHMM_Grades-COP4655_001_18078-Uploaded.csv
```

(or `...-Post-Submit-...`) so you can diff what you submitted vs what Canvas stored.

## 3. Borderline letter grades — `analyze_grades.py`

```bash
python3 analyze_grades.py
```

Picks the latest `data/Final-Grades-*Canvas*.csv`. Uses **Final Score**, not Current Score.

Scale (same as Spring 2026 / this syllabus):

| Letter | Min |
|---|---|
| A | 95 |
| A- | 90 |
| B+ | 86 |
| B | 82 |
| B- | 79 |
| C+ | 75 |
| C | 70 |
| D | 60 |
| F | 0 |

**Borderline** = within **0.6% below** the next cutoff up (e.g. 89.5 is B+, 0.5% from A-). Also prints attendance % by summing every Canvas column whose header contains `Attendance`.

Stdout sections:

- grade distribution (count, avg, range)
- borderline list with distance-to-cutoff and attendance
- full roster by letter grade

Copy the borderline table into `borderline_students.md` if you want a record. That file is an artifact — delete it at next-semester reset, do not treat it as source.

## 4. Post-submit check — `5-compare_final_grades.py`

Compares two Canvas finals CSVs so you can catch a submit that didn't stick. Paths are **hardcoded** at the bottom of the script. Point them at:

- pre-submit `Final-Grades-*Canvas*.csv`
- post-submit `Final-Grades-*Uploaded.csv` / `*Grades-*`

Then:

```bash
python3 5-compare_final_grades.py
```

## 5. Codepath completers — `6-find_codepath_completers_in_roster.py`

Optional. Cross-checks Codepath certificate / completer status against the roster. Needs the Codepath CSV (and completers export if you use one). Update paths in the script before running.

## 6. Archive before the next copy of this repo

`data/` is gitignored. Copy this folder's `data/` (or at least the `Final-Grades-*` files) into the course folder that owns the term (`Mobile-App-Fall-2026/Grades/data` stays here; do not rely on the next semester's working copy).

Then follow [`docs/new-semester.md`](new-semester.md) in the new course folder.
