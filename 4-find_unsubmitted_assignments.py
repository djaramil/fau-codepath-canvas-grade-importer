import csv
import os
import json
import re
from datetime import datetime
from io import StringIO

def build_email_templates(project_name):
    incomplete_template = f"""Subject: ACTION REQUIRED: {project_name} — incomplete submission (0)

You received a 0 on {project_name} because your Codepath submission was graded as incomplete. That is not the same as missing — it was submitted, but it did not follow the assignment instructions, so it was not scored.
You should have already received an email to your FAU account with a link to the grading report. That report is the source of truth for your submission. Read it.
Typical reasons a submission is marked incomplete / 0:
- Uploading a zip of your code to GitHub instead of a proper repo
- Pushing LabX as ProjectX (even if the code was updated — if the project is still named LabX, it is not accepted)
- Uploading a LabX video for a ProjectX submission
- Video does not show all implemented features
- README does not mark what you implemented
- Missing README, missing animated GIF, and/or tasks completed not marked in the README
Full grading process (when we grade, resubmits, what gets a 0):
https://canvas.fau.edu/courses/202165/files/48437643?module_item_id=6817598
Resubmissions are allowed only within the grading window. The {project_name} grading window has closed. Updates on GitHub, the README, or the video are not regraded unless you resubmit through the Codepath portal.
I do not accept work after the deadline. If anything in the grading report is unclear, ask on the Codepath Discord channel now — don't wait."""

    missing_zero_template = f"""Subject: ACTION REQUIRED: {project_name} — 0 (no submission recorded)

You received a 0 on {project_name} because no {project_name} submission was recorded in the Codepath portal.
You should have already received an email to your FAU account with a link to the grading report. That report is the source of truth for your submission. Read it.

The {project_name} grading window has closed, so you cannot submit or resubmit {project_name} now. Updates on GitHub, the README, or the video are not regraded after the deadline.

If you believe you submitted {project_name} before the deadline, ask on the Codepath Discord channel immediately and include evidence of the submission. I do not accept work after the deadline."""
    return incomplete_template, missing_zero_template

def load_config():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json'), 'r') as config_file:
        return json.load(config_file)

def remove_lines_before_headers(file_path, headers):
    with open(file_path, "r") as file:
        lines = file.readlines()

    header_index = next(
        (
            i
            for i, line in enumerate(lines)
            if all(header in line for header in headers)
        ),
        -1,
    )

    if header_index == -1:
        print(f"Headers {headers} not found in the file {file_path}.")
        exit(-1)
        
    # Get the header line and remove empty first column if it exists
    header_line = lines[header_index].lstrip(',')
    data_lines = [line.lstrip(',') for line in lines[header_index + 1:]]
    
    return [header_line] + data_lines

def parse_csv(file_path, config):
    data = {}
    
    # Get the cleaned lines with proper headers
    lines = remove_lines_before_headers(file_path, config["HeadersToLookFor"])
    
    # Use StringIO to create a file-like object from the lines
    csv_data = StringIO(''.join(lines))
    
    reader = csv.DictReader(csv_data)
    
    for row in reader:
        student_name = row.get('Full Name', '')
        # Skip students who have dropped
        certificate_status = row.get('CodePath Certificate Status', '').strip()
        if student_name and student_name != '#N/A' and certificate_status != 'Dropped':
            data[student_name] = row
    return data


def load_canvas_emails(file_path):
    if not file_path or not os.path.exists(file_path):
        return set()
    with open(file_path, "r", newline="") as canvas_file:
        return {
            (row.get("SIS Login ID") or "").strip().lower()
            for row in csv.DictReader(canvas_file)
            if (row.get("SIS Login ID") or "").strip()
        }


def status_column_for(points_col):
    """ASN - 1 Points -> ASN - 1 Status; GM - 7 Score -> GM - 7 Status"""
    if points_col.endswith(" Points"):
        return points_col[: -len(" Points")] + " Status"
    if points_col.endswith(" Score"):
        return points_col[: -len(" Score")] + " Status"
    return None


def classify_submission(row, points_col):
    """Complete (C), incomplete (I / scored 0), or missing (M / blank)."""
    points = (row.get(points_col) or "").strip()
    status_col = status_column_for(points_col)
    status = (row.get(status_col) or "").strip().upper() if status_col else ""

    if status == "I":
        return "incomplete"
    if status == "M":
        return "missing"
    if status == "C":
        return "submitted"
    if not points:
        return "missing"
    if points == "0":
        return "incomplete"
    return "submitted"


def build_issue_table(incomplete_assignments, missing_assignments, data, assignment_names):
    students = sorted(
        set(incomplete_assignments) | set(missing_assignments),
        key=str.casefold,
    )
    display_assignment_names = [
        re.sub(r"\s*\([^)]*\)", "", assignment).strip()
        for assignment in assignment_names
    ]
    if not students:
        return []

    headers = ["Student", "Email"] + display_assignment_names
    rows = []
    for student in students:
        row = [student, data.get(student, {}).get("Email", "").strip()]
        for assignment in assignment_names:
            if assignment in incomplete_assignments.get(student, []):
                row.append("I")
            elif assignment in missing_assignments.get(student, []):
                row.append("M")
            else:
                row.append("—")
        rows.append(row)

    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(value)) for width, value in zip(widths, row)]

    def format_row(row):
        return " | ".join(
            value.center(width) if index >= 2 else value.ljust(width)
            for index, (value, width) in enumerate(zip(row, widths))
        )

    separator = "-+-".join("-" * width for width in widths)
    return [format_row(headers), separator] + [format_row(row) for row in rows]


def find_missing_submissions(data, headers, config):
    missing_assignments = {}
    incomplete_assignments = {}
    project_stats = {}
    
    # Get assignment columns from config - use the Codepath column names (values)
    assignments_map = config['ColumnMapping']['Assignments']
    codepath_columns = list(assignments_map.values())
    
    # Initialize project stats dictionary
    for canvas_name, codepath_col in assignments_map.items():
        project_name = canvas_name.split(':')[0].strip()
        project_stats[project_name] = {'submitted': 0, 'incomplete': 0, 'missing': 0, 'total': 0}
    
    print("\nChecking assignments:", codepath_columns)
    
    total_students = 0
    for student, row in data.items():
        # Double check status (in case it's checked at a different point)
        certificate_status = row.get('CodePath Certificate Status', '').strip()
        if certificate_status == 'Dropped':
            continue
            
        total_students += 1
        student_missing = []
        student_incomplete = []
        
        for codepath_col in codepath_columns:
            # Check if the column exists in the data
            if codepath_col in row:
                # Find the Canvas assignment name for reporting
                canvas_name = next(k for k, v in assignments_map.items() if v == codepath_col)
                project_name = canvas_name.split(':')[0].strip()
                
                project_stats[project_name]['total'] += 1
                kind = classify_submission(row, codepath_col)
                project_stats[project_name][kind] += 1
                if kind == "missing":
                    student_missing.append(canvas_name)
                elif kind == "incomplete":
                    student_incomplete.append(canvas_name)
            else:
                print(f"Warning: Assignment column '{codepath_col}' not found in CSV for student {student}")
        
        if student_missing:
            missing_assignments[student] = student_missing
        if student_incomplete:
            incomplete_assignments[student] = student_incomplete
    
    return missing_assignments, incomplete_assignments, codepath_columns, project_stats, total_students

def get_latest_csv_file(root_directory, config):
    canvas_files = []
    pattern = config.get('CodepathCsvPattern', '')
    if not pattern:
        raise ValueError("CodepathCsvPattern not found in config.json")
        
    for dirpath, dirnames, filenames in os.walk(root_directory):
        for filename in filenames:
            # Skip files that are output files from previous runs
            if any(suffix in filename for suffix in ['-missing.csv', '-not-submitted.csv', '-submission-summary.csv']):
                continue
                
            if pattern in filename and filename.endswith('.csv'):
                full_path = os.path.join(dirpath, filename)
                canvas_files.append((full_path, os.path.getmtime(full_path)))
    
    if not canvas_files:
        raise FileNotFoundError(f"No CSV files matching pattern '{pattern}' found in the directory")
        
    # Get the most recent file
    latest_file = max(canvas_files, key=lambda x: x[1])[0]
    print(f"Found latest Codepath file: {os.path.basename(latest_file)}")
    return latest_file

def get_script_directory():
    """Get the directory where the script is located"""
    return os.path.dirname(os.path.abspath(__file__))

def main():
    config = load_config()
    # Use Codepath column names (values) instead of Canvas names (keys)
    columns_to_compare = list(config['ColumnMapping']['Assignments'].values())
    print(f"Columns to compare: {columns_to_compare}")

    # Get the latest Canvas file using pattern from config
    script_dir = get_script_directory()
    root_directory = os.path.join(script_dir, 'data')
    if not os.path.exists(root_directory):
        raise FileNotFoundError(f"Data directory not found at: {root_directory}")
        
    file_path = get_latest_csv_file(root_directory, config)
    print(f"\nAnalyzing file: {os.path.basename(file_path)}")
    
    # Parse the CSV file with config for headers
    data = parse_csv(file_path, config)
    canvas_pattern = config.get('CanvasCsvPattern', '')
    timestamp_part = os.path.basename(file_path).split('_')[0]
    canvas_updated_file = os.path.join(
        root_directory, f"{timestamp_part}_{canvas_pattern}-updated.csv"
    )
    canvas_emails = load_canvas_emails(canvas_updated_file)
    
    # Get the headers from the cleaned data
    with open(file_path, 'r') as csvfile:
        lines = remove_lines_before_headers(file_path, config["HeadersToLookFor"])
        reader = csv.DictReader(StringIO(''.join(lines)))
        headers = list(reader.fieldnames)
    
    # Find missing / incomplete submissions
    missing_assignments, incomplete_assignments, checked_columns, project_stats, total_students = find_missing_submissions(data, headers, config)
    
    assignment_names = list(config['ColumnMapping']['Assignments'].keys())
    last_assignment = assignment_names[-1]
    last_project_name = re.sub(r"\s*\([^)]*\)", "", last_assignment).strip()
    last_project_name = re.sub(r"^Proj\s+", "Project ", last_project_name)
    last_incomplete_assignments = {
        student: [last_assignment]
        for student, assignments in incomplete_assignments.items()
        if last_assignment in assignments
    }
    last_missing_assignments = {
        student: [last_assignment]
        for student, assignments in missing_assignments.items()
        if last_assignment in assignments
    }
    incomplete_email_template, missing_zero_email_template = build_email_templates(
        last_project_name
    )
    incomplete_table = build_issue_table(
        last_incomplete_assignments,
        {},
        data,
        [last_assignment],
    )
    missing_table = build_issue_table(
        {},
        last_missing_assignments,
        data,
        [last_assignment],
    )

    # Write results to console
    print("\nNot Submitted / Incomplete Assignments Report:")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"File analyzed: {os.path.basename(file_path)}")
    print("\nFindings:")
    print("\n--- Incomplete ---")
    print("\n".join(incomplete_table) if incomplete_table else "No incomplete assignments found!")
    print("\n--- Missing ---")
    print("\n".join(missing_table) if missing_table else "No missing assignments found!")

    incomplete_email_rows = sorted([
        (student, data.get(student, {}).get("Email", "").strip())
        for student in last_incomplete_assignments
    ], key=lambda row: row[0].casefold())
    incomplete_email_rows = [
        (student, email) for student, email in incomplete_email_rows if email
    ]
    print("\n--- Incomplete students: separate email list ---")
    if incomplete_email_rows:
        for student, email in incomplete_email_rows:
            print(f"{student} — {email}")
        print("\nOutlook list:")
        print("; ".join(email for _, email in incomplete_email_rows))
    else:
        print("No incomplete students found!")

    missing_zero_assignments = {
        student: assignments
        for student, assignments in last_missing_assignments.items()
        if (data.get(student, {}).get("Email", "").strip().lower() in canvas_emails)
    }
    missing_zero_email_rows = sorted([
        (student, data.get(student, {}).get("Email", "").strip())
        for student in missing_zero_assignments
    ], key=lambda row: row[0].casefold())
    missing_zero_email_rows = [
        (student, email) for student, email in missing_zero_email_rows if email
    ]
    print("\n--- Missing with zero: separate email list ---")
    if missing_zero_email_rows:
        for student, email in missing_zero_email_rows:
            print(f"{student} — {email}")
        print("\nOutlook list:")
        print("; ".join(email for _, email in missing_zero_email_rows))
    else:
        print("No missing-with-zero students found!")

    print("\n--- Incomplete email template ---\n")
    print(incomplete_email_template)
    print("\n--- Missing-with-zero email template ---\n")
    print(missing_zero_email_template)
    
    # Get Canvas student count for comparison
    canvas_pattern = config.get('CanvasCsvPattern', '')
    canvas_student_count = None
    if canvas_pattern:
        codepath_basename = os.path.basename(file_path)
        timestamp_part = codepath_basename.split('_')[0]
        canvas_updated_file = os.path.join(root_directory, f"{timestamp_part}_{canvas_pattern}-updated.csv")
        if os.path.exists(canvas_updated_file):
            with open(canvas_updated_file, 'r') as f:
                canvas_reader = csv.DictReader(f)
                canvas_student_count = sum(1 for _ in canvas_reader)
    
    # Print project statistics table
    print("\n=== Project Submission Statistics ===")
    print(f"Total students in Codepath: {total_students}")
    if canvas_student_count:
        print(f"Total students in Canvas: {canvas_student_count}")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"File analyzed: {os.path.basename(file_path)}")
    print()
    table_width = 108
    header_line = f"{'Project':<17} | {'Submitted':<10} | {'Incomplete':<11} | {'Unsubmitted':<12} | {'Total':<8} | {'Percentage':<10}"
    print("-" * table_width)
    print(header_line)
    print("-" * table_width)
    
    # Prepare statistics table content for both console and file
    stats_table = []
    stats_table.append("=== Project Submission Statistics ===")
    stats_table.append(f"Total students in Codepath: {total_students}")
    if canvas_student_count:
        stats_table.append(f"Total students in Canvas: {canvas_student_count}")
    stats_table.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    stats_table.append(f"File analyzed: {os.path.basename(file_path)}")
    stats_table.append("")
    stats_table.append("-" * table_width)
    stats_table.append(header_line)
    stats_table.append("-" * table_width)
    
    for project_name, stats in sorted(project_stats.items()):
        submitted = stats['submitted']
        incomplete = stats['incomplete']
        unsubmitted = stats['missing']
        percentage = (submitted / stats['total']) * 100 if stats['total'] > 0 else 0
        line = f"{project_name:<17} | {submitted:<10} | {incomplete:<11} | {unsubmitted:<12} | {stats['total']:<8} | {percentage:.1f}%"
        print(line)
        stats_table.append(line)
    
    stats_table.append("-" * table_width)
    stats_table.append("")
    stats_table.append("--- Incomplete students: separate email list ---")
    if incomplete_email_rows:
        stats_table.extend(
            f"{student} — {email}" for student, email in incomplete_email_rows
        )
        stats_table.append("")
        stats_table.append("Outlook list:")
        stats_table.append("; ".join(email for _, email in incomplete_email_rows))
    else:
        stats_table.append("No incomplete students found!")
    stats_table.append("")
    stats_table.append("--- Missing with zero: separate email list ---")
    if missing_zero_email_rows:
        stats_table.extend(
            f"{student} — {email}" for student, email in missing_zero_email_rows
        )
        stats_table.append("")
        stats_table.append("Outlook list:")
        stats_table.append("; ".join(email for _, email in missing_zero_email_rows))
    else:
        stats_table.append("No missing-with-zero students found!")
    stats_table.append("")
    stats_table.append("--- Incomplete email template ---")
    stats_table.extend(incomplete_email_template.splitlines())
    stats_table.append("")
    stats_table.append("--- Missing-with-zero email template ---")
    stats_table.extend(missing_zero_email_template.splitlines())
    print("-" * table_width)
    
    # Append to .out file (matching the Canvas updated file pattern)
    # Convert Codepath filename to Canvas pattern for .out file
    canvas_pattern = config.get('CanvasCsvPattern', '')
    if canvas_pattern:
        # Extract timestamp from Codepath filename
        codepath_basename = os.path.basename(file_path)
        # Try to find a matching Canvas updated file
        timestamp_part = codepath_basename.split('_')[0]  # Get timestamp like '2025-10-20T2058'
        out_filename = os.path.join(root_directory, f"{timestamp_part}_{canvas_pattern}-updated.out")
        
        # Check if the .out file exists before appending
        if os.path.exists(out_filename):
            with open(out_filename, 'a') as f:
                f.write("\n\n" + "="*60 + "\n")
                f.write("NOT SUBMITTED ASSIGNMENTS REPORT\n")
                f.write("="*60 + "\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"File analyzed: {os.path.basename(file_path)}\n\n")
                
                f.write("Findings:\n\n")
                f.write("--- Incomplete ---\n")
                if incomplete_table:
                    f.write("\n".join(incomplete_table) + "\n")
                else:
                    f.write("No incomplete assignments found!\n")
                f.write("\n--- Missing ---\n")
                if missing_table:
                    f.write("\n".join(missing_table) + "\n")
                else:
                    f.write("No missing assignments found!\n")
                
                # Add statistics table
                f.write("\n")
                for line in stats_table:
                    f.write(line + "\n")
            
            print(f"\nReport appended to {out_filename}")
        else:
            print(f"\nNote: .out file not found at {out_filename}, skipping append")

if __name__ == "__main__":
    main()
