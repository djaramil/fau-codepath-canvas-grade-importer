#!/usr/bin/env python3
"""
Grade Processing Orchestrator
Runs all grade processing scripts in the correct order:
1. Update Canvas grades from Codepath data
2. Compare grades between Canvas files
3. Find unsubmitted assignments
"""

import sys
import os
from datetime import datetime

# Import the main functions from each script
try:
    import importlib.util
    
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Function to import a module from a file path
    def import_module_from_file(module_name, file_path):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    
    # Import each script as a module
    updater = import_module_from_file("updater", os.path.join(script_dir, "1-codepath-canvas-updater.py"))
    comparer = import_module_from_file("comparer", os.path.join(script_dir, "2-compare_grades.py"))
    finder = import_module_from_file("finder", os.path.join(script_dir, "3-find_unsubmitted_assignments.py"))
    
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure all three scripts are in the same directory:")
    print("  - 1-codepath-canvas-updater.py")
    print("  - 2-compare_grades.py")
    print("  - 3-find_unsubmitted_assignments.py")
    sys.exit(1)


def print_section_header(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70 + "\n")


def main():
    """Run all grade processing scripts in sequence"""
    start_time = datetime.now()
    print_section_header("GRADE PROCESSING PIPELINE STARTED")
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Step 1: Update Canvas grades from Codepath
    print_section_header("STEP 1: Updating Canvas Grades from Codepath Data")
    try:
        updater.main()
        print("\n✓ Step 1 completed successfully")
    except Exception as e:
        print(f"\n✗ Step 1 failed with error: {e}")
        print("Stopping pipeline due to error.")
        sys.exit(1)
    
    # Step 2: Compare grades between Canvas files
    print_section_header("STEP 2: Comparing Grades Between Canvas Files")
    try:
        comparer.main()
        print("\n✓ Step 2 completed successfully")
    except Exception as e:
        print(f"\n✗ Step 2 failed with error: {e}")
        print("Continuing to next step...")
    
    # Step 3: Find unsubmitted assignments
    print_section_header("STEP 3: Finding Unsubmitted Assignments")
    try:
        finder.main()
        print("\n✓ Step 3 completed successfully")
    except Exception as e:
        print(f"\n✗ Step 3 failed with error: {e}")
        print("Pipeline completed with errors.")
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    print_section_header("GRADE PROCESSING PIPELINE COMPLETED")
    print(f"Started at:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration:    {duration.total_seconds():.2f} seconds")
    print("\nAll processing complete! Check the data/ directory for output files.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
