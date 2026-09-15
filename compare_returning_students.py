#!/usr/bin/env python3
"""
Compare students between COP4655 Fall 2026 (new class) and COP4808 Spring 2026
(previous Codepath course) to identify returning students.
"""

import csv

def letter_from_score(score):
    if score is None:
        return 'N/A'
    if score >= 95:
        return 'A'
    if score >= 90:
        return 'A-'
    if score >= 86:
        return 'B+'
    if score >= 82:
        return 'B'
    if score >= 79:
        return 'B-'
    if score >= 75:
        return 'C+'
    if score >= 70:
        return 'C'
    if score >= 60:
        return 'D'
    return 'F'


def parse_score(value):
    value = (value or '').strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def read_students_from_csv(filepath):
    """
    Read student data from Canvas CSV file.
    Returns a dictionary with email as key and student info as value.
    """
    students = {}

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get('Student') or '').strip()
            if not name or name.lower() in {'points possible', 'student, test'}:
                continue

            email = (row.get('SIS Login ID') or '').strip()
            section = (row.get('Section') or '').strip()
            current_score = (row.get('Current Score') or '').strip()
            unposted_current_grade = (row.get('Unposted Current Grade') or '').strip()
            final_score = parse_score(
                row.get('Unposted Final Score') or row.get('Final Score') or row.get('Unposted Current Score')
            )
            if not unposted_current_grade and final_score is not None:
                unposted_current_grade = letter_from_score(final_score)

            if email and name:
                students[email.lower()] = {
                    'name': name,
                    'email': email,
                    'section': section,
                    'current_score': current_score,
                    'final_score': final_score,
                    'unposted_current_grade': unposted_current_grade
                }

    return students

def main():
    new_file = '/Users/yoda26/Documents/FAU/Mobile-App-Fall-2026/roster/2026-09-10T1539_Roster-COP4655_001_18078-Canvas.csv'
    prev_file = '/Users/yoda26/Documents/FAU/FullStackWeb-Spring-2026/Grades/data/Final-Grades-2026-05-08T1322_Canvas-COP4808_001_13815.csv'

    print("Reading COP4655 Fall 2026 (new class) students...")
    new_students = read_students_from_csv(new_file)
    print(f"Found {len(new_students)} students in Fall 2026\n")

    print("Reading COP4808 Spring 2026 (previous class) students...")
    prev_students = read_students_from_csv(prev_file)
    print(f"Found {len(prev_students)} students in Spring 2026\n")

    returning_students = []

    for email, student_info in new_students.items():
        if email in prev_students:
            student_info['previous_section'] = prev_students[email]['section']
            student_info['previous_current_grade'] = prev_students[email]['unposted_current_grade']
            student_info['previous_final_score'] = prev_students[email]['final_score']
            returning_students.append(student_info)

    print("\n" + "=" * 125)
    print(f"RETURNING STUDENTS: {len(returning_students)} out of {len(new_students)} total in Fall 2026")
    print("=" * 125)
    print()

    if returning_students:
        returning_students.sort(key=lambda x: x['name'])

        print(f"{'#':<4} {'Name':<30} {'Email':<35} {'Section':<25} {'S26 Grade':<10} {'S26 Score':<10}")
        print("-" * 125)

        section_counts = {}
        grade_counts = {}

        for idx, student in enumerate(returning_students, 1):
            current_section = student['section']
            previous_grade = student.get('previous_current_grade', '')
            display_grade = previous_grade if previous_grade else 'N/A'
            prev_score = student.get('previous_final_score')
            display_score = f"{prev_score:.2f}%" if prev_score is not None else 'N/A'

            if current_section not in section_counts:
                section_counts[current_section] = 0
            section_counts[current_section] += 1

            if display_grade not in grade_counts:
                grade_counts[display_grade] = 0
            grade_counts[display_grade] += 1

            print(f"{idx:<4} {student['name']:<30} {student['email']:<35} {current_section:<25} {display_grade:<10} {display_score:<10}")

        print("=" * 125)
        print("\nSECTION BREAKDOWN:")
        print("-" * 60)
        for section in sorted(section_counts.keys()):
            print(f"{section:<40} {section_counts[section]:>3} students")
        print("-" * 60)
        print(f"{'TOTAL RETURNING STUDENTS':<40} {len(returning_students):>3}")

        print("\n" + "=" * 125)
        print("\nGRADE DISTRIBUTION (Spring 2026 COP4808):")
        print("-" * 60)

        grade_order = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D+', 'D', 'D-', 'F', 'N/A']
        for grade in grade_order:
            if grade in grade_counts:
                print(f"Grade {grade:<10} {grade_counts[grade]:>3} students")

        for grade in sorted(grade_counts.keys()):
            if grade not in grade_order:
                print(f"Grade {grade:<10} {grade_counts[grade]:>3} students")

        print("-" * 60)
        print(f"{'TOTAL':<15} {len(returning_students):>3} students")
        print()
    else:
        print("No returning students found.")

    print()
    pct = (len(returning_students) / len(new_students) * 100) if new_students else 0
    print(f"Summary: {len(returning_students)} out of {len(new_students)} students in Fall 2026 ({pct:.1f}%) are returning from Spring 2026 COP4808")
    print("Overlap with Fall 2025 COP4655 (same-course retakes): 0")

if __name__ == '__main__':
    main()
