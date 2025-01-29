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
    # print(f"Searching for headers: {headers} in file: {codepath_csv_filename}")
    with open(codepath_csv_filename, "r") as file:
        lines = file.readlines()
        # print(f"First few lines of the file:")
        # for i, line in enumerate(lines[:5]):
        #     print(f"Line {i + 1}: {line.strip()}")

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

        # Write to the temporary file
        with open(temp_filename, "w") as temp_file:
            temp_file.writelines(lines[header_index:])

        print(
            f"The file has been saved without the lines before the headers to: {temp_filename}"
        )
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

        updated_data = []
        emails_without_grades = []
        processed_emails = set()

        with open(temp_codepath_csv_filename, "r") as codepath_file:
            codepath_reader = csv.DictReader(codepath_file)
            for codepath_row in codepath_reader:
                email = codepath_row.get(column_mapping["Email"])
                if email:
                    canvas_row = next(
                        (
                            e
                            for e in canvas_data
                            if e[column_mapping["SIS Login ID"]].lower()
                            == email.lower()
                        ),
                        None,
                    )
                    if canvas_row and email not in processed_emails:
                        updated_row = canvas_row.copy()

                        # Update grades using Assignments mapping
                        for canvas_col, codepath_col in column_mapping[
                            "Assignments"
                        ].items():
                            updated_row[canvas_col] = codepath_row.get(codepath_col, "")

                        updated_data.append(updated_row)
                        processed_emails.add(email)
                    else:
                        emails_without_grades.append(email.lower())

        # Write the updated data to the output CSV file
        if updated_data:
            with open(output_csv_filename, "w", newline="") as output_file:
                fieldnames = canvas_data[0].keys()  # Use original Canvas CSV headers
                writer = csv.DictWriter(output_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(updated_data)
            print(f"Results written to {output_csv_filename}")

        # Write the list of email addresses without grades to a separate file
        if emails_without_grades:
            with open(missing_emails_filename, "w", newline="") as missing_file:
                writer = csv.writer(missing_file)
                writer.writerow(["Email"])
                writer.writerows([[email] for email in emails_without_grades])
            print(
                f"Emails that are not in the student roster written to {missing_emails_filename}"
            )

        # If we've reached this point without any exceptions, remove the temporary file
        os.remove(temp_codepath_csv_filename)
        print(f"Temporary file {temp_codepath_csv_filename} has been removed.")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print(
            f"The temporary file {temp_codepath_csv_filename} has not been removed due to the error."
        )


if __name__ == "__main__":
    main()
