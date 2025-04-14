import csv
import os
import json
from datetime import datetime
from collections import defaultdict

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
    
    # Create a file-like object from the lines
    csv_data = '\n'.join(lines)
    
    # Write to a temporary file
    temp_file = file_path + '.temp'
    with open(temp_file, 'w') as f:
        f.write(csv_data)
    
    # Read from the temporary file
    with open(temp_file, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            student_name = row.get('Full Name', '')
            # Skip students who have withdrawn or dropped
            status = row.get('Status', '').strip()
            certificate_status = row.get('CodePath Certificate Status', '').strip()
            if student_name and status != 'Withdrawn' and certificate_status != 'Dropped':
                data[student_name] = row
    
    # Remove temporary file
    os.remove(temp_file)
    return data

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

def summarize_submissions_by_project(data, config):
    # Get assignment columns from config - use the Canvas column names (keys) for display
    assignments_map = config['ColumnMapping']['Assignments']
    codepath_columns = list(assignments_map.values())
    canvas_columns = list(assignments_map.keys())
    
    # Initialize counters for each project
    project_submissions = defaultdict(int)
    project_total = defaultdict(int)
    
    # Count total students (excluding withdrawn/dropped)
    total_students = len(data)
    
    # Count submissions for each project
    for student, row in data.items():
        for i, codepath_col in enumerate(codepath_columns):
            # Check if the column exists in the data
            if codepath_col in row:
                # Extract project number from the Canvas column name
                canvas_col = canvas_columns[i]
                project_num = canvas_col.split('(')[0].strip().split(':')[0].split()[-1]
                
                # Increment total count for this project
                project_total[project_num] += 1
                
                # Check if the submission has a value (not blank, not just whitespace, and not '0')
                if row[codepath_col].strip() and row[codepath_col].strip() != '0':
                    project_submissions[project_num] += 1
    
    # Sort projects by number
    sorted_projects = sorted(project_total.keys(), key=lambda x: int(x))
    
    # Create summary
    summary = []
    for project in sorted_projects:
        submitted = project_submissions[project]
        total = project_total[project]
        percentage = (submitted / total * 100) if total > 0 else 0
        summary.append({
            'project': project,
            'submitted': submitted,
            'total': total,
            'percentage': percentage
        })
    
    return summary, total_students

def main():
    config = load_config()
    
    # Get the latest Codepath file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_directory = os.path.join(script_dir, 'data')
    if not os.path.exists(root_directory):
        raise FileNotFoundError(f"Data directory not found at: {root_directory}")
        
    file_path = get_latest_csv_file(root_directory, config)
    print(f"\nAnalyzing file: {os.path.basename(file_path)}")
    
    # Parse the CSV file
    data = parse_csv(file_path, config)
    
    # Generate summary by project
    summary, total_students = summarize_submissions_by_project(data, config)
    
    # Print summary
    print("\n=== Submission Summary by Project ===")
    print(f"Total active students: {total_students}")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"File analyzed: {os.path.basename(file_path)}")
    print("\nProject | Submitted | Total | Percentage")
    print("--------|-----------|-------|------------")
    
    for item in summary:
        print(f"Project {item['project']} | {item['submitted']} | {item['total']} | {item['percentage']:.1f}%")
    
    # Write summary to CSV
    output_filename = os.path.splitext(file_path)[0] + '-submission-summary.csv'
    with open(output_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Project', 'Submitted', 'Total', 'Percentage'])
        for item in summary:
            writer.writerow([
                f"Project {item['project']}", 
                item['submitted'], 
                item['total'], 
                f"{item['percentage']:.1f}%"
            ])
    
    print(f"\nDetailed summary has been written to: {os.path.basename(output_filename)}")

if __name__ == "__main__":
    main()
