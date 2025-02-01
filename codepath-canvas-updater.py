import json
import csv
import os
import tempfile
import shutil
import glob


def get_latest_csv(pattern, directory="data/"):
    # Find all files matching the pattern in the specified directory
    files = glob.glob(os.path.join(directory, f"*_{pattern}.csv"))
    if not files:
        raise FileNotFoundError(f"No files found matching pattern: {pattern}")
    
    # Sort by timestamp (assuming timestamp is at start of filename)
    latest_file = max(files)
    return latest_file


def remove_lines_before_headers(codepath_csv_filename, headers):
    with open(codepath_csv_filename, "r") as file:
        lines = file.readlines()

    header_index = next(
        (
            i
            for i, line in enumerate(lines)
            if all(header in line for header in headers)
        ),
        -1,
    )

    if header_index != -1:
        # Create a temporary file name
        temp_filename = codepath_csv_filename.rsplit(".", 1)[0] + "-temp.csv"

        # Write to the temporary file, removing the empty first column
        with open(temp_filename, "w") as temp_file:
            # Get the header line and remove empty first column if it exists
            header_line = lines[header_index].lstrip(',')  
            temp_file.write(header_line)
            
            # Process remaining lines
            for line in lines[header_index + 1:]:
                # Remove empty first column if it exists
                line = line.lstrip(',')
                temp_file.write(line)

        print(f"Cleared headers from codepath file: {temp_filename}")
        return temp_filename
    else:
        print(f"Headers {headers} not found in the file {codepath_csv_filename}.")
        exit(-1)


def main():
    try:
        # Read the configuration file
        with open("config.json", "r") as config_file:
            config = json.load(config_file)

        # Get the latest CSV files based on patterns
        try:
            canvas_csv_filename = get_latest_csv(config["CanvasCsvPattern"])
            codepath_csv_filename = get_latest_csv(config["CodepathCsvPattern"])
            print(f"Using Canvas file: {canvas_csv_filename}")
            print(f"Using Codepath file: {codepath_csv_filename}")
        except FileNotFoundError as e:
            print(f"Error finding CSV files: {str(e)}")
            return

        output_csv_filename = canvas_csv_filename.replace(".csv", "-updated.csv")
        missing_emails_filename = output_csv_filename.replace(
            "-updated.csv", "-missing.csv"
        )

        # Column name mapping
        column_mapping = config["ColumnMapping"]

        # Headers to look for
        headers_to_look_for = config["HeadersToLookFor"]
        temp_codepath_csv_filename = remove_lines_before_headers(
            codepath_csv_filename, headers_to_look_for
        )

        # Read the emails and store them in a list
        canvas_data = []
        with open(canvas_csv_filename, "r") as canvas_file:
            canvas_reader = csv.DictReader(canvas_file)
            canvas_data = list(canvas_reader)

        if not canvas_data:
            print("No valid data found in the Canvas file.")
            return

        # Print canvas data for debugging
        # print("Canvas students:")
        canvas_emails = set()
        for row in canvas_data:
            email = row[column_mapping["SIS Login ID"]].lower()
            canvas_emails.add(email)
            if "jdoischen" in email:
                print(f"Found in Canvas: {email}")

        # First get all Canvas emails for comparison
        canvas_emails = set()
        #print("\nCanvas students:")
        for row in canvas_data:
            email = row[column_mapping["SIS Login ID"]].lower()
            canvas_emails.add(email)
            #print(f"Added to Canvas set: {email}")

        updated_data = []
        emails_without_grades = []
        processed_emails = set()

        # print("\nProcessing CodePath students:")
        # Process CodePath students
        with open(temp_codepath_csv_filename, "r", newline='') as codepath_file:
            # Read all lines and process them
            lines = codepath_file.readlines()
            header = lines[0].strip()
            data_lines = [line.strip() for line in lines[1:]]
            
            # Create a CSV reader from the processed lines
            reader = csv.DictReader([header] + data_lines)
            
            for row in reader:
                # Get email and skip if not present
                email = row.get("Email")
                if not email:  # Skip if no email
                    continue
                    
                # Get status and student name
                status = row.get("Status", '').strip()
                student_name = row.get("Full Name", "")
                email = email.lower()
                
                #print(f"Processing: {email}, Status: {status}")
                
                # Only process non-withdrawn students
                if status == 'Withdrawn':
                    #print(f"Skipping {email} - Withdrawn")
                    continue

                # If student is not in Canvas, check if they're dropped before adding to missing list
                if email not in canvas_emails:
                    certificate_status = row.get("CodePath Certificate Status", '').strip()
                    if certificate_status == 'Dropped':
                        #print(f"Skipping {email} - Certificate Status is Dropped")
                        continue
                    #print(f"Adding {email} to missing list - not in Canvas (Certificate Status: {certificate_status})")
                    emails_without_grades.append((email, student_name))
                    continue

                # Student is in Canvas, update their grades if not processed
                if email not in processed_emails:
                    for canvas_row in canvas_data:
                        if canvas_row[column_mapping["SIS Login ID"]].lower() == email:
                            updated_row = canvas_row.copy()
                            # Update grades using Assignments mapping
                            for canvas_col, codepath_col in column_mapping["Assignments"].items():
                                updated_row[canvas_col] = row.get(codepath_col, "")
                            updated_data.append(updated_row)
                            processed_emails.add(email)
                            break

        # Write the updated data to the output CSV file
        if updated_data:
            with open(output_csv_filename, "w", newline="") as output_file:
                fieldnames = canvas_data[0].keys()  # Use original Canvas CSV headers
                writer = csv.DictWriter(output_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(updated_data)
            print(f"Results written to {output_csv_filename}")

        # Always create the missing emails file with headers, even if empty
        with open(missing_emails_filename, "w", newline="") as missing_file:
            writer = csv.writer(missing_file)
            writer.writerow(["Email", "Student Name"])  # Add Student Name column
            if emails_without_grades:
                writer.writerows(emails_without_grades)  # Write both email and name
                print(
                    f"Missing students written to {missing_emails_filename}"
                )
            else:
                print(
                    f"No missing students written to {missing_emails_filename}"
                )

        # If we've reached this point without any exceptions, remove the temporary file
        # os.remove(temp_codepath_csv_filename)
        # print(f"Temporary file {temp_codepath_csv_filename} has been removed.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print(
            f"The temporary file {temp_codepath_csv_filename} has not been removed due to the error."
        )


if __name__ == "__main__":
    main()
