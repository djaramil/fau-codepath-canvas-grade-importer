import csv
import os
import json
from datetime import datetime

def load_config():
    with open('config.json', 'r') as config_file:
        return json.load(config_file)

def parse_csv(file_path):
    data = {}
    with open(file_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        # Print headers to debug
        print(f"\nHeaders in {os.path.basename(file_path)}:")
        print(list(reader.fieldnames))
        for row in reader:
            # Use Student column since that's what's in the CSV
            student_name = row.get('Student', '')
            if student_name:
                data[student_name] = row
    return data

def compare_grades(old_file, new_file, columns_to_compare):
    old_data = parse_csv(old_file)
    new_data = parse_csv(new_file)

    print("\nColumns we're looking for:")
    print(columns_to_compare)

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
                        print(f"\nFound difference for {student} in {column}:")
                        print(f"  Old: {old_value}")
                        print(f"  New: {new_value}")
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
            # Only match files that are exactly [timestamp]_[pattern].csv
            # This excludes -missing, -updated, or any other variations
            if '_' + canvas_pattern + '.csv' in filename:
                full_path = os.path.join(dirpath, filename)
                canvas_files.append((full_path, os.path.getmtime(full_path)))
    
    sorted_files = sorted(canvas_files, key=lambda x: x[1], reverse=True)
    return [f[0] for f in sorted_files[:2]] if len(sorted_files) >= 2 else None

def main():
    config = load_config()
    # Use Canvas assignment names (keys) instead of Codepath column names (values)
    columns_to_compare = list(config['ColumnMapping']['Assignments'].keys())
    print(f"Columns to compare: {columns_to_compare}")

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
            f.write(f"Updates found between {os.path.basename(old_file)} (old) and {os.path.basename(new_file)} (new):\n")
            for student, column, old_value, new_value in updates:
                f.write(f"Student: {student}\n")
                f.write(f"  {column}: {old_value} -> {new_value}\n")
                f.write("\n")
            print(f"Updates have been written to {output_filename}")
        else:
            print("No updates found between the files.")
            f.write("No updates found in the specified columns.\n")
            print(f"No updates found. Result written to {output_filename}")

if __name__ == "__main__":
    main()
