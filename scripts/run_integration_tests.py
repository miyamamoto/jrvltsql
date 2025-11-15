#!/usr/bin/env python
"""Helper script to run integration tests with JV-Link service key.

This script helps you run integration tests by:
1. Prompting for your JV-Link service key (if not already set)
2. Running the integration tests
3. Displaying results

Usage:
    python run_integration_tests.py

Or set environment variable first:
    export JVLINK_SERVICE_KEY="YOUR_KEY"
    python run_integration_tests.py
"""

import os
import subprocess
import sys
from getpass import getpass


def main():
    """Run integration tests with service key."""
    print("=" * 70)
    print("JV-Link Integration Tests")
    print("=" * 70)
    print()

    # Check if service key is already set
    service_key = os.environ.get("JVLINK_SERVICE_KEY")

    if not service_key:
        print("JVLINK_SERVICE_KEY environment variable not set.")
        print()
        print("You need a valid JRA-VAN DataLab service key to run these tests.")
        print("The service key will only be used for this session.")
        print()

        choice = input("Do you want to enter your service key now? (y/n): ").strip().lower()

        if choice != 'y':
            print()
            print("Integration tests skipped.")
            print()
            print("To run tests later, set the environment variable:")
            print("  Windows CMD:        set JVLINK_SERVICE_KEY=YOUR_KEY")
            print("  Windows PowerShell: $env:JVLINK_SERVICE_KEY='YOUR_KEY'")
            print("  Git Bash/MSYS2:     export JVLINK_SERVICE_KEY='YOUR_KEY'")
            print()
            print("Then run: pytest tests/integration/ -v -s")
            return

        print()
        service_key = getpass("Enter your JV-Link service key: ").strip()

        if not service_key:
            print("Error: No service key provided.")
            sys.exit(1)

        # Set for this process
        os.environ["JVLINK_SERVICE_KEY"] = service_key
        print("✓ Service key set for this session")
        print()

    else:
        print(f"✓ Using service key from environment: {service_key[:4]}***")
        print()

    # Display test options
    print("=" * 70)
    print("Select tests to run:")
    print("=" * 70)
    print()
    print("1. Quick connection test (tests JV-Link initialization only)")
    print("2. Small data sample test (fetches ~100 records)")
    print("3. Full workflow test (complete: Fetch → Parse → Import → Verify)")
    print("4. Parser field coverage test (analyzes real data format)")
    print("5. Error handling tests")
    print("6. All integration tests")
    print("0. Exit")
    print()

    choice = input("Enter your choice (0-6): ").strip()

    # Map choices to pytest commands
    test_map = {
        "1": "tests/integration/test_jvlink_real.py::TestJVLinkRealDataFetching::test_jvlink_connection",
        "2": "tests/integration/test_jvlink_real.py::TestJVLinkRealDataFetching::test_fetch_small_data_sample",
        "3": "tests/integration/test_jvlink_real.py::TestJVLinkRealDataFetching::test_full_workflow_with_real_data",
        "4": "tests/integration/test_jvlink_real.py::TestJVLinkRealDataFetching::test_parser_with_real_data_formats",
        "5": "tests/integration/test_jvlink_real.py::TestJVLinkErrorHandling",
        "6": "tests/integration/test_jvlink_real.py",
    }

    if choice == "0":
        print("Exiting.")
        return

    if choice not in test_map:
        print(f"Error: Invalid choice '{choice}'")
        sys.exit(1)

    test_path = test_map[choice]

    print()
    print("=" * 70)
    print("Running tests...")
    print("=" * 70)
    print()

    # Run pytest
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        test_path,
        "-v",
        "-s",
        "--tb=short",
    ]

    try:
        result = subprocess.run(cmd, env=os.environ.copy())
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print()
        print("Tests interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
