#!/usr/bin/env python3
"""
Compare students between COP4808 (new class) and COP4655 (previous class)
to identify returning students.
"""

import csv
import os

def read_students_from_csv(filepath):
    """
    Read student data from Canvas CSV file.
    Returns a dictionary with email as key and student info as value.
    """
    students = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip header rows (Points Possible, etc.)
            if row.get('Student') in ['Points Possible', '']:
                continue
            
            email = row.get('SIS Login ID', '').strip()
            name = row.get('Student', '').strip()
            section = row.get('Section', '').strip()
            current_score = row.get('Current Score', '').strip()
            unposted_current_grade = row.get('Unposted Current Grade', '').strip()
            
            if email and name:
                students[email] = {
                    'name': name,
                    'email': email,
                    'section': section,
                    'current_score': current_score,
                    'unposted_current_grade': unposted_current_grade
                }
    
    return students

def main():
    # File paths
    data_dir = '/Users/yoda26/Documents/FAU/Mobile-App-Fall-2025/Grades/data'
    next_semester_dir = '/Users/yoda26/Documents/FAU/Mobile-App-Fall-2025/Grades/next-semester'
    cop4808_file = os.path.join(next_semester_dir, '2025-11-18T2235_Canvas-COP4808_001_13815.csv')
    cop4655_file = os.path.join(data_dir, '2025-11-17T0922_Canvas-COP4655_001_13208.csv')
    
    # Read student data from both files
    print("Reading COP4808 (new class) students...")
    cop4808_students = read_students_from_csv(cop4808_file)
    print(f"Found {len(cop4808_students)} students in COP4808\n")
    
    print("Reading COP4655 (previous class) students...")
    cop4655_students = read_students_from_csv(cop4655_file)
    print(f"Found {len(cop4655_students)} students in COP4655\n")
    
    # Find returning students (students in both classes)
    returning_students = []
    
    for email, student_info in cop4808_students.items():
        if email in cop4655_students:
            # Add previous section info and current grade
            student_info['previous_section'] = cop4655_students[email]['section']
            student_info['previous_current_grade'] = cop4655_students[email]['unposted_current_grade']
            returning_students.append(student_info)
    
    # Print results in table format
    print("\n" + "=" * 115)
    print(f"RETURNING STUDENTS: {len(returning_students)} out of {len(cop4808_students)} total in COP4808")
    print("=" * 115)
    print()
    
    if returning_students:
        # Sort by name for easier reading
        returning_students.sort(key=lambda x: x['name'])
        
        # Print table header
        print(f"{'#':<4} {'Name':<30} {'Email':<35} {'Section':<25} {'COP4655 Grade':<15}")
        print("-" * 115)
        
        # Count by section and grade
        section_counts = {}
        grade_counts = {}
        
        for idx, student in enumerate(returning_students, 1):
            current_section = student['section']
            previous_grade = student.get('previous_current_grade', '')
            # Display N/A if grade is empty, otherwise show the grade
            display_grade = previous_grade if previous_grade else 'N/A'
            
            # Track section counts
            if current_section not in section_counts:
                section_counts[current_section] = 0
            section_counts[current_section] += 1
            
            # Track grade counts
            if display_grade not in grade_counts:
                grade_counts[display_grade] = 0
            grade_counts[display_grade] += 1
            
            print(f"{idx:<4} {student['name']:<30} {student['email']:<35} {current_section:<25} {display_grade:<15}")
        
        # Print section totals
        print("=" * 115)
        print("\nSECTION BREAKDOWN:")
        print("-" * 60)
        for section in sorted(section_counts.keys()):
            print(f"{section:<40} {section_counts[section]:>3} students")
        print("-" * 60)
        print(f"{'TOTAL RETURNING STUDENTS':<40} {len(returning_students):>3}")
        
        # Print grade distribution
        print("\n" + "=" * 115)
        print("\nGRADE DISTRIBUTION (COP4655 Current Grades):")
        print("-" * 60)
        
        # Sort grades in a logical order (A, A-, B+, B, B-, C+, C, etc.)
        grade_order = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'N/A']
        for grade in grade_order:
            if grade in grade_counts:
                print(f"Grade {grade:<10} {grade_counts[grade]:>3} students")
        
        # Print any grades not in the standard order
        for grade in sorted(grade_counts.keys()):
            if grade not in grade_order:
                print(f"Grade {grade:<10} {grade_counts[grade]:>3} students")
        
        print("-" * 60)
        print(f"{'TOTAL':<15} {len(returning_students):>3} students")
        print()
    else:
        print("No returning students found.")
    
    print()
    print(f"Summary: {len(returning_students)} out of {len(cop4808_students)} students in COP4808 ({len(returning_students)/len(cop4808_students)*100:.1f}%) are returning from COP4655")

if __name__ == '__main__':
    main()
