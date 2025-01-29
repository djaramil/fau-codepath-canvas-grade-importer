# fau-codepath-canvas-grade-importer

Nodejs code that reads exported csv file from Codepath gradebook and reads exported data from Canvas, matches the student and updates the grade into a new Canvas CSV file which you will use to upload back into Canvas.  Download current grades from Canvas and Codepath into the data directory using the following instructions

## Export current grades from Canvas
Give the filename this kind of format and replace Grades with Canvas: 2025-01-28T2302_Grades-COT5930_012_16128.csv -> 2025-01-28T2302_Canvas-COT5930_012_16128.csv

## Export current grades from Codepath spreadsheet
File / Download / CSV -  Contains the current sheet with the latest gradebook data for that date
2025-01-28T2302_Codepath-COT5930_012_16128.csv

File / Download / XLS - save as reference - has all data for that date
Give the filename this kind of format and replace Grades with Codepath: 2025-01-28T2302_Codepath-COT5930_012_16128.xlsx

Update config.json with the following:
CanvasCsvPattern: 2025-01-28T2302_Canvas-COT5930_012_16128.csv
CodepathCsvPattern: 2025-01-28T2302_Codepath-COT5930_012_16128.csv
HeadersToLookFor: ["Member ID", "Full Name"]

Update Assignments with the column names from Canvas including the code # in parentheses and the grade column name from Codepath.

    "Assignments": {
        "Project 1: Scavenger Hunt (2033669)": "ASN - 1 Points",
        "Project 2: BeReal Clone PT 1 (2033676)": "ASN - 2 Points",
        "Project 3: BeReal PT 2 (2033716)": "ASN - 3 Points",
        "Project 4: Memory Game (2034487)": "ASN - 4 Points",
        "Project 5: Trivia Game (2034520)": "ASN - 5 Points",
        "Project 6: TranslateMe (2034742)": "ASN - 6 Points",
        "Unit 7 - Final Project Part 3: Third Milestone (2172876)": "GM - 7 Score",
        "Unit 8 - Final Project Part 4: Fourth Milestone (2035120)": "GM - 8 Score",
        "Unit 9 - Final Project Part 5: Fifth Milestone (2035167)": "GM - 9 Score"
    }
}

## Installation / running the program
Requires Python 3.13.0
python codepath-canvas-updater.py

Example output:

```
Grades % python3 codepath-canvas-updater.py
Using Canvas file: data/2025-01-28T2302_Canvas-COT5930_012_16128.csv
Using Codepath file: data/2025-01-28T2302_Codepath-COT5930_012_16128.csv
The file has been saved without the lines before the headers to: data/2025-01-28T2302_Codepath-COT5930_012_16128-temp.csv
Results written to data/2025-01-28T2302_Canvas-COT5930_012_16128-updated.csv
Emails that are not in the student roster written to data/2025-01-28T2302_Canvas-COT5930_012_16128-missing.csv
Temporary file data/2025-01-28T2302_Codepath-COT5930_012_16128-temp.csv has been removed.
```

Check the *-missing.csv file - contains emails that are not in the student roster.  These need to be investigated - can be mismatching email address or students that have dropped from the class.

Check the *-updated.csv file - contains the updated Canvas file that you can upload back into Canvas.
