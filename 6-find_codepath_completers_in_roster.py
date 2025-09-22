#!/usr/bin/env python3
import csv
import os
import json
from io import StringIO

def load_config():
    """Load configuration from config.json file"""
    with open('config.json', 'r') as config_file:
        return json.load(config_file)

def remove_lines_before_headers(file_path, headers):
    """Remove lines before the header row in a CSV file"""
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

def parse_csv(file_path, config, is_codepath_csv=True):
    """Parse a CSV file and return data as a dictionary"""
    data = {}
    
    # Get the cleaned lines with proper headers
    lines = remove_lines_before_headers(file_path, config["HeadersToLookFor"])
    
    # Use StringIO to create a file-like object from the lines
    csv_data = StringIO(''.join(lines))
    
    reader = csv.DictReader(csv_data)
    print(f"\nHeaders in {os.path.basename(file_path)}:")
    print(list(reader.fieldnames))
    
    for row in reader:
        student_name = row.get('Full Name', '')
        # Skip students who have dropped if it's a CodePath CSV
        if is_codepath_csv:
            certificate_status = row.get('CodePath Certificate Status', '').strip()
            if student_name and certificate_status != 'Dropped':
                data[student_name] = row
        else:
            # For the completers CSV, just add all students
            if student_name:
                data[student_name] = row
    
    return data

def parse_completers_csv(file_path):
    """Parse the CodePath_Completers_with_Selections.csv file"""
    data = {}
    
    with open(file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        print(f"\nHeaders in {os.path.basename(file_path)}:")
        print(list(reader.fieldnames))
        
        for row in reader:
            # Assuming 'Name' is the field containing student names
            student_name = row.get('Name', '')
            if student_name:
                data[student_name] = row
    
    return data

def get_latest_csv_file(root_directory, config):
    """Get the latest CodePath CSV file based on modification time"""
    codepath_files = []
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
                codepath_files.append((full_path, os.path.getmtime(full_path)))
    
    if not codepath_files:
        raise FileNotFoundError(f"No CSV files matching pattern '{pattern}' found in the directory")
        
    # Get the most recent file
    latest_file = max(codepath_files, key=lambda x: x[1])[0]
    print(f"Found latest Codepath file: {os.path.basename(latest_file)}")
    return latest_file

def get_script_directory():
    """Get the directory where the script is located"""
    return os.path.dirname(os.path.abspath(__file__))

def main():
    # Load configuration
    config = load_config()
    
    # Get the script directory and data directory
    script_dir = get_script_directory()
    data_dir = os.path.join(script_dir, 'data')
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"Data directory not found at: {data_dir}")
    
    # Get the latest CodePath CSV file
    latest_codepath_file = get_latest_csv_file(data_dir, config)
    print(f"\nUsing latest CodePath roster file: {os.path.basename(latest_codepath_file)}")
    
    # Parse the latest CodePath CSV file
    codepath_data = parse_csv(latest_codepath_file, config, is_codepath_csv=True)
    print(f"Found {len(codepath_data)} active students in the CodePath roster")
    
    # Path to the CodePath Completers CSV file
    completers_file = os.path.join(data_dir, 'CodePath_Completers_with_Selections.csv')
    if not os.path.exists(completers_file):
        raise FileNotFoundError(f"CodePath Completers file not found at: {completers_file}")
    
    # Parse the CodePath Completers CSV file
    completers_data = parse_completers_csv(completers_file)
    print(f"Found {len(completers_data)} students in the CodePath Completers file")
    
    # Find students who are in both files
    students_in_both = []
    students_not_in_roster = []
    
    for student_name in completers_data.keys():
        if student_name in codepath_data:
            students_in_both.append(student_name)
        else:
            students_not_in_roster.append(student_name)
    
    # Print results
    print("\nResults:")
    print(f"Total students in CodePath Completers file: {len(completers_data)}")
    print(f"Students from Completers file who are in your CodePath roster: {len(students_in_both)}")
    
    print("\nStudents from Completers file who are in your CodePath roster:")
    for i, student in enumerate(sorted(students_in_both), 1):
        print(f"{i}. {student}")
    
    print("\nStudents from Completers file who are NOT in your CodePath roster:")
    for i, student in enumerate(sorted(students_not_in_roster), 1):
        print(f"{i}. {student}")
    
    # Write results to a CSV file
    output_file = os.path.join(script_dir, 'codepath_completers_comparison.csv')
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Student Name', 'In CodePath Roster'])
        
        for student in sorted(completers_data.keys()):
            writer.writerow([student, 'Yes' if student in codepath_data else 'No'])
    
    print(f"\nResults have been written to: {os.path.basename(output_file)}")

if __name__ == "__main__":
    main()
