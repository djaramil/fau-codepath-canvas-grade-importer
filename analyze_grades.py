#!/usr/bin/env python3
"""
End-of-semester grade analysis.

Reads a Canvas finals export (Final Score + attendance columns) and prints
letter-grade distribution plus students within BORDERLINE_MARGIN of the next
cutoff up. Point at data/Final-Grades-*Canvas*.csv — see docs/end-of-semester.md.
"""

import csv
import glob
import os
from collections import defaultdict

BORDERLINE_MARGIN = 0.6  # percent below the next letter-grade cutoff

# Grading scale
GRADING_SCALE = [
    ('A', 95, 100),
    ('A-', 90, 94),
    ('B+', 86, 89),
    ('B', 82, 85),
    ('B-', 79, 81),
    ('C+', 75, 78),
    ('C', 70, 74),
    ('D', 60, 69),
    ('F', 0, 59),
]

def get_letter_grade(score):
    """Get letter grade based on percentage score."""
    if score >= 95:
        return 'A'
    elif score >= 90:
        return 'A-'
    elif score >= 86:
        return 'B+'
    elif score >= 82:
        return 'B'
    elif score >= 79:
        return 'B-'
    elif score >= 75:
        return 'C+'
    elif score >= 70:
        return 'C'
    elif score >= 60:
        return 'D'
    else:
        return 'F'

def is_borderline(score, letter_grade, margin=BORDERLINE_MARGIN):
    """Check if a score is borderline (within margin% of next grade UP)."""
    for grade, min_score, max_score in GRADING_SCALE:
        if letter_grade == grade:
            # Calculate distance to next grade's cutoff (minimum score)
            next_g = next_grade(grade)
            for ng, nmin, nmax in GRADING_SCALE:
                if ng == next_g:
                    distance = nmin - score
                    if 0 < distance <= margin:
                        return True, f"{distance:.2f}% from {next_g}"
            break
    return False, ""

def next_grade(current_grade):
    """Get the next higher grade."""
    for i, (grade, _, _) in enumerate(GRADING_SCALE):
        if grade == current_grade and i > 0:
            return GRADING_SCALE[i-1][0]
    return current_grade

def prev_grade(current_grade):
    """Get the next lower grade."""
    for i, (grade, _, _) in enumerate(GRADING_SCALE):
        if grade == current_grade and i < len(GRADING_SCALE) - 1:
            return GRADING_SCALE[i+1][0]
    return current_grade

def calculate_attendance(row, headers, points_possible_row):
    """Calculate attendance percentage from attendance columns."""
    attendance_earned = 0
    attendance_possible = 0
    
    for i, header in enumerate(headers):
        # Look for attendance columns
        if 'Attendance' in header:
            try:
                earned = float(row[i]) if i < len(row) and row[i].strip() != '' else 0
                possible = float(points_possible_row[i]) if i < len(points_possible_row) and points_possible_row[i].strip() != '' else 0
                attendance_earned += earned
                attendance_possible += possible
            except (ValueError, IndexError):
                continue
    
    if attendance_possible > 0:
        return (attendance_earned / attendance_possible) * 100
    return 0.0

def analyze_grades(csv_file):
    """Analyze grades from the CSV file."""
    results = []
    grade_distribution = defaultdict(list)
    borderline_students = []
    
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        headers = next(reader)
        manual_posting_row = next(reader)  # Skip manual posting row
        points_possible_row = next(reader)  # This is the points possible row
        
        # Find the Final Score column index
        final_score_idx = None
        for i, header in enumerate(headers):
            if header.strip() == 'Final Score':
                final_score_idx = i
                break
        
        if final_score_idx is None:
            print("Error: Could not find 'Final Score' column")
            return
        
        print(f"Using column {final_score_idx} for Final Score: {headers[final_score_idx]}")
        
        for row in reader:
            if len(row) <= final_score_idx:
                continue
            
            # Skip header rows (rows that don't have numeric scores)
            try:
                student_name = row[0]
                final_score = float(row[final_score_idx])
            except (ValueError, IndexError):
                continue
            
            letter_grade = get_letter_grade(final_score)
            attendance_pct = calculate_attendance(row, headers, points_possible_row)
            
            result = {
                'name': student_name,
                'score': final_score,
                'letter_grade': letter_grade,
                'attendance': attendance_pct
            }
            
            is_br, reason = is_borderline(final_score, letter_grade)
            if is_br:
                result['borderline'] = True
                result['reason'] = reason
                borderline_students.append(result)
            else:
                result['borderline'] = False
            
            grade_distribution[letter_grade].append(result)
            results.append(result)
    
    # Print results
    print("\n" + "="*80)
    print("GRADE DISTRIBUTION")
    print("="*80)
    for grade in ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'D', 'F']:
        students = grade_distribution[grade]
        if students:
            avg_score = sum(s['score'] for s in students) / len(students)
            print(f"\n{grade}: {len(students)} students")
            print(f"  Average: {avg_score:.2f}%")
            print(f"  Range: {min(s['score'] for s in students):.2f}% - {max(s['score'] for s in students):.2f}%")
    
    print("\n" + "="*80)
    print(f"BORDERLINE STUDENTS (within {BORDERLINE_MARGIN}% of next grade UP)")
    print("="*80)
    if borderline_students:
        for student in sorted(borderline_students, key=lambda x: x['score'], reverse=True):
            # Calculate distance to next grade cutoff
            for grade, min_score, max_score in GRADING_SCALE:
                if student['letter_grade'] == grade:
                    next_g = next_grade(grade)
                    for ng, nmin, nmax in GRADING_SCALE:
                        if ng == next_g:
                            cutoff = nmin
                            distance = cutoff - student['score']
                            print(f"{student['name']}: {student['score']:.2f}% ({student['letter_grade']}) - {distance:.2f}% from {next_g} (cutoff: {cutoff}%) | Attendance: {student['attendance']:.2f}%")
                            break
                    break
    else:
        print("No borderline students found.")
    
    print("\n" + "="*80)
    print("ALL STUDENTS BY GRADE")
    print("="*80)
    for grade in ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'D', 'F']:
        students = grade_distribution[grade]
        if students:
            print(f"\n{grade}:")
            for student in sorted(students, key=lambda x: x['score'], reverse=True):
                border = " [BORDERLINE]" if student['borderline'] else ""
                print(f"  {student['name']}: {student['score']:.2f}%{border}")


def find_final_grades_csv():
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    matches = glob.glob(os.path.join(data_dir, "Final-Grades-*Canvas*.csv"))
    if not matches:
        raise FileNotFoundError(
            "No data/Final-Grades-*Canvas*.csv found. Export Canvas finals and name it "
            "Final-Grades-YYYY-MM-DDTHHMM_Canvas-COP4655_001_18078.csv"
        )
    latest = max(matches)
    print(f"Using finals file: {latest}")
    return latest


if __name__ == '__main__':
    analyze_grades(find_final_grades_csv())
