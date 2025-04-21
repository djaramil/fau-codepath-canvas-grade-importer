import csv
import os
import json
from datetime import datetime
from io import StringIO

def load_config():
    with open('config.json', 'r') as config_file:
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
    # Print headers to debug
    print(f"\nHeaders in {os.path.basename(file_path)}:")
    print(list(reader.fieldnames))
    
    for row in reader:
        student_name = row.get('Full Name', '')
        # Skip students who have dropped
        certificate_status = row.get('CodePath Certificate Status', '').strip()
        if student_name and certificate_status != 'Dropped':
            data[student_name] = row
    return data

def find_missing_submissions(data, headers, config):
    missing_assignments = {}
    project_stats = {}
    
    # Get assignment columns from config - use the Codepath column names (values)
    assignments_map = config['ColumnMapping']['Assignments']
    codepath_columns = list(assignments_map.values())
    
    # Initialize project stats dictionary
    for canvas_name, codepath_col in assignments_map.items():
        project_name = canvas_name.split(':')[0].strip()
        project_stats[project_name] = {'missing': 0, 'total': 0}
    
    print("\nChecking assignments:", codepath_columns)
    
    total_students = 0
    for student, row in data.items():
        # Double check status (in case it's checked at a different point)
        certificate_status = row.get('CodePath Certificate Status', '').strip()
        if certificate_status == 'Dropped':
            continue
            
        total_students += 1
        student_missing = []
        
        for codepath_col in codepath_columns:
            # Check if the column exists in the data
            if codepath_col in row:
                # Find the Canvas assignment name for reporting
                canvas_name = next(k for k, v in assignments_map.items() if v == codepath_col)
                project_name = canvas_name.split(':')[0].strip()
                
                # Increment total count for this project
                project_stats[project_name]['total'] += 1
                
                # Check if the submission is blank or only whitespace or '0'
                if not row[codepath_col].strip() or row[codepath_col].strip() == '0':
                    student_missing.append(canvas_name)
                    # Increment missing count for this project
                    project_stats[project_name]['missing'] += 1
            else:
                print(f"Warning: Assignment column '{codepath_col}' not found in CSV for student {student}")
        
        if student_missing:
            missing_assignments[student] = student_missing
    
    return missing_assignments, codepath_columns, project_stats, total_students

def get_latest_csv_file(root_directory, config):
    canvas_files = []
    pattern = config.get('CodepathCsvPattern', '')
    if not pattern:
        raise ValueError("CodepathCsvPattern not found in config.json")
        
    for dirpath, dirnames, filenames in os.walk(root_directory):
        for filename in filenames:
            # Skip files that are output files from previous runs
            if any(suffix in filename for suffix in ['-missing.csv', '-not-submitted.csv']):
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
    
    # Find missing submissions
    missing_assignments, checked_columns, project_stats, total_students = find_missing_submissions(data, headers, config)
    
    # Generate report with updated naming
    output_filename = os.path.splitext(file_path)[0] + '-not-submitted.csv'
    
    # Write results to both console and file
    print("\nNot Submitted Assignments Report:")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"File analyzed: {os.path.basename(file_path)}")
    print("\nFindings:")
    
    # Write to CSV file
    with open(output_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(['Student', 'Not Submitted Assignments'])
        
        # Write data and print to console
        if missing_assignments:
            for student, assignments in missing_assignments.items():
                writer.writerow([student, ', '.join(assignments)])
                print(f"\nStudent: {student}")
                print("Not submitted assignments:")
                for assignment in assignments:
                    print(f"  - {assignment}")
        else:
            print("No unsubmitted assignments found!")
            writer.writerow(['No unsubmitted assignments found', ''])
        
        # Add empty rows as separator
        writer.writerow([])
        writer.writerow([])
        
        # Add project statistics summary to CSV
        writer.writerow(['Project Submission Statistics'])
        writer.writerow(['Project', 'Submitted', 'Unsubmitted', 'Total', 'Percentage'])
        
        for project_name, stats in sorted(project_stats.items()):
            submitted = stats['total'] - stats['missing']
            unsubmitted = stats['missing']
            percentage = (submitted / stats['total']) * 100 if stats['total'] > 0 else 0
            writer.writerow([project_name, submitted, unsubmitted, stats['total'], f"{percentage:.1f}%"])
    
    print(f"\nDetailed report has been written to: {os.path.basename(output_filename)}")
    
    # Print project statistics table
    print("\nProject Submission Statistics:")
    print("-" * 75)
    print(f"{'Project':<12} | {'Submitted':<10} | {'Unsubmitted':<12} | {'Total':<8} | {'Percentage':<10}")
    print("-" * 75)
    
    # Prepare statistics table content for both console and file
    stats_table = []
    stats_table.append("Project Submission Statistics:")
    stats_table.append("-" * 75)
    stats_table.append(f"{'Project':<12} | {'Submitted':<10} | {'Unsubmitted':<12} | {'Total':<8} | {'Percentage':<10}")
    stats_table.append("-" * 75)
    
    for project_name, stats in sorted(project_stats.items()):
        submitted = stats['total'] - stats['missing']
        unsubmitted = stats['missing']
        percentage = (submitted / stats['total']) * 100 if stats['total'] > 0 else 0
        line = f"{project_name:<12} | {submitted:<10} | {unsubmitted:<12} | {stats['total']:<8} | {percentage:.1f}%"
        print(line)
        stats_table.append(line)
    
    stats_table.append("-" * 75)
    print("-" * 75)
    
    # Write statistics to updated.out file
    updated_out_file = os.path.join(os.path.dirname(file_path), os.path.basename(file_path).replace('Codepath', 'Canvas') + '-updated.out')
    
    # Check if file exists and append to it, or create new file
    with open(updated_out_file, 'a') as f:
        f.write('\n\n' + '\n'.join(stats_table))

if __name__ == "__main__":
    main()
