#!/usr/bin/env python3
"""
Samsung Frame TV Art Mode Verification Script

Tests connectivity and art mode functionality with the Samsung Frame TV.
"""

import json
import os
import sys
from datetime import datetime

# Configuration
TV_IP = os.environ.get("TV_IP", "192.168.0.105")
TIMEOUT = 10


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(name: str, success: bool, data=None, error=None) -> None:
    """Print a test result with PASS/FAIL status."""
    status = "\033[92mPASS\033[0m" if success else "\033[91mFAIL\033[0m"
    print(f"\n[{status}] {name}")

    if data is not None:
        print("  Result:")
        if isinstance(data, (dict, list)):
            print(f"  {json.dumps(data, indent=4, default=str)}")
        else:
            print(f"  {data}")

    if error is not None:
        print(f"  Error: {error}")


def main() -> int:
    """Run TV verification tests."""
    print_header("Samsung Frame TV Art Mode Verification")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Target TV: {TV_IP}")

    # Track results
    results = {"passed": 0, "failed": 0}

    # Import library
    print_header("1. Library Import")
    try:
        from samsungtvws import SamsungTVWS
        print_result("Import samsungtvws", True)
        results["passed"] += 1
    except ImportError as e:
        print_result("Import samsungtvws", False, error=str(e))
        results["failed"] += 1
        print("\n\033[91mCannot proceed without library. Exiting.\033[0m")
        return 1

    # Connect to TV
    print_header("2. TV Connection")
    tv = None
    try:
        tv = SamsungTVWS(TV_IP, timeout=TIMEOUT)
        print_result("Create TV connection", True, data=f"Connected to {TV_IP}")
        results["passed"] += 1
    except Exception as e:
        print_result("Create TV connection", False, error=str(e))
        results["failed"] += 1
        print("\n\033[91mCannot proceed without connection. Exiting.\033[0m")
        return 1

    # Check art mode support
    print_header("3. Art Mode Support")
    art_supported = False
    try:
        art_supported = tv.art().supported()
        print_result("art().supported()", True, data=art_supported)
        results["passed"] += 1
    except Exception as e:
        print_result("art().supported()", False, error=str(e))
        results["failed"] += 1

    if not art_supported:
        print("\n\033[93mWarning: Art mode not supported or TV may be off.\033[0m")
        print("Make sure:")
        print("  - TV is powered on")
        print("  - TV is in Art Mode (not regular TV mode)")
        print("  - TV is a Samsung Frame model")

    # Get available artwork
    print_header("4. Available Artwork")
    try:
        available = tv.art().available()
        count = len(available) if isinstance(available, list) else "unknown"
        print_result("art().available()", True, data=f"Found {count} artwork(s)")
        if available and isinstance(available, list) and len(available) > 0:
            print("  First 3 items:")
            for item in available[:3]:
                print(f"    - {json.dumps(item, default=str)}")
        results["passed"] += 1
    except Exception as e:
        print_result("art().available()", False, error=str(e))
        results["failed"] += 1

    # Get current artwork
    print_header("5. Current Artwork")
    try:
        current = tv.art().get_current()
        print_result("art().get_current()", True, data=current)
        results["passed"] += 1
    except Exception as e:
        print_result("art().get_current()", False, error=str(e))
        results["failed"] += 1

    # Summary
    print_header("Summary")
    total = results["passed"] + results["failed"]
    print(f"  Passed: {results['passed']}/{total}")
    print(f"  Failed: {results['failed']}/{total}")

    if results["failed"] == 0:
        print("\n\033[92mAll tests passed! TV art mode communication verified.\033[0m")
        return 0
    else:
        print("\n\033[93mSome tests failed. Check errors above.\033[0m")
        return 1


if __name__ == "__main__":
    sys.exit(main())
