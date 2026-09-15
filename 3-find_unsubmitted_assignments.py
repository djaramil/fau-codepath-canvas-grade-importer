import csv
import os
import json
from datetime import datetime
from io import StringIO

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
    
    # Get the headers from the cleaned data
    with open(file_path, 'r') as csvfile:
        lines = remove_lines_before_headers(file_path, config["HeadersToLookFor"])
        reader = csv.DictReader(StringIO(''.join(lines)))
        headers = list(reader.fieldnames)
    
    # Find missing / incomplete submissions
    missing_assignments, incomplete_assignments, checked_columns, project_stats, total_students = find_missing_submissions(data, headers, config)
    
    # Write results to console
    print("\nNot Submitted / Incomplete Assignments Report:")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"File analyzed: {os.path.basename(file_path)}")
    print("\nFindings:")

    if incomplete_assignments:
        print("\n--- Incomplete (submitted, scored 0) ---")
        for student, assignments in incomplete_assignments.items():
            print(f"\nStudent: {student}")
            print("Incomplete assignments:")
            for assignment in assignments:
                print(f"  - {assignment}")
    else:
        print("\nNo incomplete assignments found!")

    if missing_assignments:
        print("\n--- Not submitted (missing) ---")
        for student, assignments in missing_assignments.items():
            print(f"\nStudent: {student}")
            print("Not submitted assignments:")
            for assignment in assignments:
                print(f"  - {assignment}")
    else:
        print("\nNo unsubmitted assignments found!")
    
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
                if incomplete_assignments:
                    f.write("--- Incomplete (submitted, scored 0) ---\n\n")
                    for student, assignments in incomplete_assignments.items():
                        f.write(f"Student: {student}\n")
                        f.write("Incomplete assignments:\n")
                        for assignment in assignments:
                            f.write(f"  - {assignment}\n")
                        f.write("\n")
                else:
                    f.write("No incomplete assignments found!\n\n")

                if missing_assignments:
                    f.write("--- Not submitted (missing) ---\n\n")
                    for student, assignments in missing_assignments.items():
                        f.write(f"Student: {student}\n")
                        f.write("Not submitted assignments:\n")
                        for assignment in assignments:
                            f.write(f"  - {assignment}\n")
                        f.write("\n")
                else:
                    f.write("No unsubmitted assignments found!\n")
                
                # Add statistics table
                f.write("\n")
                for line in stats_table:
                    f.write(line + "\n")
            
            print(f"\nReport appended to {out_filename}")
        else:
            print(f"\nNote: .out file not found at {out_filename}, skipping append")

if __name__ == "__main__":
    main()
