import csv
import os
import json
from datetime import datetime
from collections import defaultdict

def load_config():
    with open('config.json', 'r') as config_file:
        return json.load(config_file)

def parse_csv(file_path):
    data = {}
    with open(file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        # Headers are available in reader.fieldnames
        for row in reader:
            # Use Student column since that's what's in the CSV
            student_name = row.get('Student', '')
            if student_name:
                data[student_name] = row
    return data

def compare_grades(old_file, new_file, columns_to_compare):
    old_data = parse_csv(old_file)
    new_data = parse_csv(new_file)


    updates = []

    for student, new_row in new_data.items():
        if student in old_data:
            old_row = old_data[student]
            for column in columns_to_compare:
                if column in old_row and column in new_row:
                    # Convert to float for comparison, handling empty strings
                    old_value = float(old_row[column].strip()) if old_row[column].strip() else 0.0
                    new_value = float(new_row[column].strip()) if new_row[column].strip() else 0.0
                    if abs(new_value - old_value) > 0.01:  # Use small epsilon for float comparison
                        project_num = column.split('(')[0].strip().split(':')[0].split()[-1]
                        print(f"{student} - Project {project_num} - {old_value} -> {new_value}")
                        updates.append((student, column, str(old_value), str(new_value)))
                else:
                    if column not in old_row:
                        print(f"\nWarning: Column '{column}' not found in old file for student {student}")
                    if column not in new_row:
                        print(f"\nWarning: Column '{column}' not found in new file for student {student}")

    return updates

def get_latest_csv_files(root_directory):
    config = load_config()
    canvas_pattern = config['CanvasCsvPattern']
    
    canvas_files = []
    for dirpath, dirnames, filenames in os.walk(root_directory):
        for filename in filenames:
            # Look for files that end with -updated.csv
            if '_' + canvas_pattern + '-updated.csv' in filename:
                full_path = os.path.join(dirpath, filename)
                canvas_files.append((full_path, os.path.getmtime(full_path)))
    
    sorted_files = sorted(canvas_files, key=lambda x: x[1], reverse=True)
    return [f[0] for f in sorted_files[:2]] if len(sorted_files) >= 2 else None

def summarize_submissions_by_project(file_path, config):
    # Parse the CSV file
    data = parse_csv(file_path)
    
    # Get assignment columns from config
    assignments_map = config['ColumnMapping']['Assignments']
    canvas_columns = list(assignments_map.keys())
    
    # Initialize counters for each project
    project_submissions = defaultdict(int)
    project_total = defaultdict(int)
    
    # Count total students (excluding withdrawn/dropped)
    total_students = len(data)
    
    # Count submissions for each project
    for student, row in data.items():
        for canvas_col in canvas_columns:
            # Extract project number from the Canvas column name
            project_num = canvas_col.split('(')[0].strip().split(':')[0].split()[-1]
            
            # Increment total count for this project
            project_total[project_num] += 1
            
            # Check if the submission has a value (not blank, not just whitespace, and not '0')
            if canvas_col in row and row[canvas_col].strip() and row[canvas_col].strip() != '0':
                project_submissions[project_num] += 1
    
    # Sort projects by number
    sorted_projects = sorted(project_total.keys(), key=lambda x: int(x))
    
    # Create summary
    summary = []
    for project in sorted_projects:
        submitted = project_submissions[project]
        total = project_total[project]
        unsubmitted = total - submitted
        percentage = (submitted / total * 100) if total > 0 else 0
        summary.append({
            'project': project,
            'submitted': submitted,
            'unsubmitted': unsubmitted,
            'total': total,
            'percentage': percentage
        })
    
    return summary, total_students

def main():
    config = load_config()
    # Use Canvas assignment names (keys) instead of Codepath column names (values)
    columns_to_compare = list(config['ColumnMapping']['Assignments'].keys())

    data_directory = 'data'
    latest_files = get_latest_csv_files(data_directory)

    if not latest_files:
        print(f"Error: Could not find two Canvas CSV files in the {data_directory}/ directory or its subdirectories.")
        return

    new_file, old_file = latest_files
    print(f"\nComparing files:")
    print(f"Old file: {old_file}")
    print(f"New file: {new_file}\n")

    updates = compare_grades(old_file, new_file, columns_to_compare)

    # Create output filename based on new Canvas file name
    output_filename = new_file.rsplit('.', 1)[0] + '.out'

    with open(output_filename, 'w') as f:
        if updates:
            f.write("Updates found between:\n")
            f.write(f"  Old: {os.path.basename(old_file)}\n")
            f.write(f"  New: {os.path.basename(new_file)}\n\n")
            for student, column, old_value, new_value in updates:
                # Extract project number from the column name
                project_num = column.split('(')[0].strip().split(':')[0].split()[-1]
                f.write(f"{student} - Project {project_num} - {old_value} -> {new_value}\n")
            print(f"Updates have been written to {output_filename}")
        else:
            print("No updates found between the files.")
            f.write("No updates found in the specified columns.\n")
            print(f"No updates found. Result written to {output_filename}")
    
    # Generate and print summary by project
    summary, total_students = summarize_submissions_by_project(new_file, config)
    
    print("\n=== Submission Summary by Project ===")
    print(f"Total active students: {total_students}")
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"File analyzed: {os.path.basename(new_file)}")
    print("\n{:<10} | {:<9} | {:<12} | {:<5} | {:<10}".format("Project", "Submitted", "Unsubmitted", "Total", "Percentage"))
    print("-" * 60)
    
    for item in summary:
        print("{:<10} | {:<9} | {:<12} | {:<5} | {:<10}".format(
            f"Project {item['project']}", 
            item['submitted'], 
            item['unsubmitted'],
            item['total'], 
            f"{item['percentage']:.1f}%"
        ))
    
    # Append summary to output file
    with open(output_filename, 'a') as f:
        f.write("\n\n=== Submission Summary by Project ===\n")
        f.write(f"Total active students: {total_students}\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"File analyzed: {os.path.basename(new_file)}\n\n")
        f.write("{:<10} | {:<9} | {:<12} | {:<5} | {:<10}\n".format("Project", "Submitted", "Unsubmitted", "Total", "Percentage"))
        f.write("-" * 60 + "\n")
        
        for item in summary:
            f.write("{:<10} | {:<9} | {:<12} | {:<5} | {:<10}\n".format(
                f"Project {item['project']}", 
                item['submitted'], 
                item['unsubmitted'],
                item['total'], 
                f"{item['percentage']:.1f}%"
            ))

if __name__ == "__main__":
    main()
