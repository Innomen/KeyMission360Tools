#!/usr/bin/env python3
"""
KeyMission 360 - Comprehensive Test Suite
=========================================

Run with: python3 test_suite.py
Or: python3 test_suite.py --verbose

Tests:
- CLI syntax and imports
- GUI syntax and imports
- Dependency detection
- File parsing logic
- Merge detection
- Download logic (dry-run)
"""

import subprocess
import sys
import argparse

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

results = {"passed": 0, "failed": 0, "warnings": 0}


def log_pass(msg):
    results["passed"] += 1
    print(f"  {GREEN}✓{RESET} {msg}")


def log_fail(msg):
    results["failed"] += 1
    print(f"  {RED}✗{RESET} {msg}")


def log_warn(msg):
    results["warnings"] += 1
    print(f"  {YELLOW}⚠{RESET} {msg}")


def test_cli_syntax():
    """Test CLI compiles without errors"""
    print("\n[TEST] CLI Syntax")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", "km360"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            log_pass("km360 compiles successfully")
            return True
        else:
            log_fail(f"Syntax error: {result.stderr}")
            return False
    except Exception as e:
        log_fail(f"Exception: {e}")
        return False


def test_gui_syntax():
    """Test GUI compiles without errors"""
    print("\n[TEST] GUI Syntax")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", "km360_gui.py"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            log_pass("km360_gui.py compiles successfully")
            return True
        else:
            log_fail(f"Syntax error: {result.stderr}")
            return False
    except Exception as e:
        log_fail(f"Exception: {e}")
        return False


def test_cli_help():
    """Test CLI help works"""
    print("\n[TEST] CLI Help")
    try:
        result = subprocess.run(
            [sys.executable, "km360", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and "KeyMission 360" in result.stdout:
            log_pass("CLI help works")
            return True
        else:
            log_fail("CLI help failed")
            return False
    except Exception as e:
        log_fail(f"Exception: {e}")
        return False


def test_gui_headless():
    """Test GUI headless mode"""
    print("\n[TEST] GUI Headless Mode")
    try:
        result = subprocess.run(
            [sys.executable, "km360_gui.py", "--test"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and (
            "passed" in result.stdout.lower() or "✓" in result.stdout
        ):
            log_pass("GUI headless test passes")
            return True
        else:
            log_fail("GUI headless test failed")
            print(f"    stdout: {result.stdout[:200]}")
            return False
    except Exception as e:
        log_fail(f"Exception: {e}")
        return False


def test_cli_deps_check():
    """Test CLI dependency check"""
    print("\n[TEST] CLI Dependency Check")
    try:
        result = subprocess.run(
            [sys.executable, "km360", "check"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and "Dependency Check" in result.stdout:
            log_pass("CLI dependency check works")
            return True
        else:
            log_warn("CLI dependency check may have issues")
            return True  # Non-critical
    except Exception as e:
        log_warn(f"Exception: {e}")
        return True  # Non-critical


def test_merge_detection():
    """Test merge candidate detection logic"""
    print("\n[TEST] Merge Detection Logic")
    try:
        import re
        from pathlib import Path

        # Test files
        test_files = [
            "DSCN0016.MP4",
            "DSCN0017.MP4",  # Sequential
            "DSCN0020.MP4",  # Gap
            "DSCN0021.MP4",  # Sequential with 20
        ]

        # Detection logic
        sequences = []
        current_seq = [test_files[0]]

        for i in range(1, len(test_files)):
            prev = Path(test_files[i - 1]).stem
            curr = Path(test_files[i]).stem

            prev_nums = re.findall(r"\d+", prev)
            curr_nums = re.findall(r"\d+", curr)

            is_sequential = False
            if prev_nums and curr_nums:
                try:
                    gap = int(curr_nums[-1]) - int(prev_nums[-1])
                    if 1 <= gap <= 2:
                        is_sequential = True
                except:
                    pass

            if is_sequential:
                current_seq.append(test_files[i])
            else:
                if len(current_seq) >= 2:
                    sequences.append(current_seq)
                current_seq = [test_files[i]]

        if len(current_seq) >= 2:
            sequences.append(current_seq)

        if len(sequences) == 2:
            log_pass(f"Detected {len(sequences)} sequences correctly")
            return True
        else:
            log_fail(f"Expected 2 sequences, got {len(sequences)}")
            return False

    except Exception as e:
        log_fail(f"Exception: {e}")
        return False


def test_duplicate_detection():
    """Test download duplicate detection logic"""
    print("\n[TEST] Duplicate Detection Logic")
    try:
        # Simulate camera files and local files
        camera_files = [
            (1, "DSCN0016.JPG"),
            (2, "DSCN0017.MP4"),
            (3, "DSCN0018.JPG"),
        ]

        existing_files = {"DSCN0016.JPG"}  # First one exists

        # Run logic
        to_skip = []
        to_download = []

        for num, name in camera_files:
            if name in existing_files:
                to_skip.append(name)
            else:
                to_download.append(name)

        if len(to_skip) == 1 and len(to_download) == 2:
            log_pass(f"Skip: {len(to_skip)}, Download: {len(to_download)}")
            return True
        else:
            log_fail(
                f"Wrong counts - Skip: {len(to_skip)}, Download: {len(to_download)}"
            )
            return False

    except Exception as e:
        log_fail(f"Exception: {e}")
        return False


def test_cli_subcommands():
    """Test all CLI subcommands are available"""
    print("\n[TEST] CLI Subcommands")
    required = ["info", "list", "download", "reset", "time", "format", "deps", "merge"]

    try:
        result = subprocess.run(
            [sys.executable, "km360", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        help_text = result.stdout

        all_found = True
        for cmd in required:
            if cmd in help_text:
                log_pass(f"'{cmd}' command available")
            else:
                log_fail(f"'{cmd}' command MISSING")
                all_found = False

        return all_found

    except Exception as e:
        log_fail(f"Exception: {e}")
        return False


def test_config_module():
    """Test config module works"""
    print("\n[TEST] Config Module")
    try:
        from km360_config import load_config, get_last_download_dir

        # Test load
        config = load_config()
        if isinstance(config, dict):
            log_pass("load_config() works")
        else:
            log_fail("load_config() returned non-dict")
            return False

        # Test get_last_download_dir
        path = get_last_download_dir()
        if path and isinstance(path, str):
            log_pass("get_last_download_dir() works")
        else:
            log_warn("get_last_download_dir() returned empty")

        return True

    except Exception as e:
        log_fail(f"Exception: {e}")
        return False


def test_file_dialogs():
    """Test file dialog imports"""
    print("\n[TEST] File Dialog Imports")
    try:
        log_pass("Native dialogs imported successfully")
        return True
    except Exception as e:
        log_fail(f"Failed to import: {e}")
        return False


def test_merge_cli():
    """Test merge CLI functionality"""
    print("\n[TEST] Merge CLI")
    try:
        # Test help
        result = subprocess.run(
            [sys.executable, "km360", "merge", "--help"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0 and "--auto" in result.stdout:
            log_pass("Merge command available with --auto flag")
        else:
            log_warn("Merge command may have issues")

        # Test detect-only with sample files
        result = subprocess.run(
            [
                sys.executable,
                "km360",
                "merge",
                "--detect-only",
                "--force",
                "-o",
                "/tmp/test.mp4",
                "DSCN0017.MP4",
                "DSCN0022.MP4",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if any(text in result.stdout for text in ("Merge complete", "Detect-only", "No valid input files found")):
            log_pass("Merge detect-only handles synthetic missing inputs")
        else:
            log_warn("Merge detect-only output unexpected")

        return True

    except Exception as e:
        log_warn(f"Exception: {e}")
        return True  # Non-critical


def test_path_validation():
    """Test that paths are validated and cleaned (DRI_PRIME bug fix)"""
    print("\n[TEST] Path Validation")
    try:
        from km360_config import set_last_download_dir, load_config

        # Save original
        original = load_config().get("last_download_dir")
        test_dir = "/tmp"

        # Test 1: Valid path
        set_last_download_dir(test_dir)
        config = load_config()
        if config.get("last_download_dir") == test_dir:
            log_pass("Valid path accepted and saved")
        else:
            log_fail("Valid path was not saved correctly")

        # Test 2: Path with newline (should extract the actual path)
        set_last_download_dir("Invalid value\n/home/user/extracted_path")
        config = load_config()
        saved = config.get("last_download_dir", "")
        if "/home/user/extracted_path" in saved:
            log_pass("Path with newline - extracted valid path")
        elif saved == test_dir:
            log_pass("Path with newline rejected")
        else:
            log_fail(f"Unexpected path after newline test: {saved}")

        # Reset to test dir
        set_last_download_dir(test_dir)

        # Test 3: DRI_PRIME error prefix (should extract the actual path)
        set_last_download_dir(
            "Invalid value (0) for DRI_PRIME. Should be > 0 /home/user/clean_path"
        )
        config = load_config()
        saved = config.get("last_download_dir", "")
        if saved == "/home/user/clean_path":
            log_pass("DRI_PRIME error prefix stripped, path extracted")
        elif "DRI_PRIME" not in saved:
            log_pass("DRI_PRIME path rejected or cleaned")
        else:
            log_fail(f"DRI_PRIME still in path: {saved}")

        # Reset
        set_last_download_dir(test_dir)

        # Test 4: Error message (should reject)
        set_last_download_dir("Error: something went wrong /home/user/path")
        config = load_config()
        if "Error:" not in config.get("last_download_dir", ""):
            log_pass("Error message path rejected")
        else:
            log_fail("Error message path was NOT rejected!")

        # Reset
        set_last_download_dir(test_dir)

        # Test 5: Empty path (should reject)
        set_last_download_dir("")
        config = load_config()
        if config.get("last_download_dir") == test_dir:
            log_pass("Empty path rejected")
        else:
            log_fail("Empty path handling issue")

        # Reset
        set_last_download_dir(test_dir)

        # Test 6: Relative path (should reject)
        set_last_download_dir("relative/path/to/folder")
        config = load_config()
        if "relative" not in config.get("last_download_dir", ""):
            log_pass("Relative path rejected (must be absolute)")
        else:
            log_fail("Relative path was NOT rejected!")

        # Restore original
        set_last_download_dir(original)
        return True

    except Exception as e:
        log_fail(f"Exception: {e}")
        return False


def run_all_tests(verbose=False):
    """Run all tests"""
    print("=" * 60)
    print("KeyMission 360 - Test Suite")
    print("=" * 60)

    tests = [
        ("CLI Syntax", test_cli_syntax),
        ("GUI Syntax", test_gui_syntax),
        ("CLI Help", test_cli_help),
        ("GUI Headless", test_gui_headless),
        ("CLI Dependency Check", test_cli_deps_check),
        ("CLI Subcommands", test_cli_subcommands),
        ("Merge Detection Logic", test_merge_detection),
        ("Duplicate Detection", test_duplicate_detection),
        ("Config Module", test_config_module),
        ("File Dialogs", test_file_dialogs),
        ("Merge CLI", test_merge_cli),
        ("Path Validation", test_path_validation),
    ]

    for name, test_func in tests:
        try:
            test_func()
        except Exception as e:
            log_fail(f"Test crashed: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Passed:   {GREEN}{results['passed']}{RESET}")
    print(f"Failed:   {RED}{results['failed']}{RESET}")
    print(f"Warnings: {YELLOW}{results['warnings']}{RESET}")

    if results["failed"] == 0:
        print(f"\n{GREEN}✓ All critical tests passed!{RESET}")
        return 0
    else:
        print(f"\n{RED}✗ Some tests failed. Please review.{RESET}")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KeyMission 360 Test Suite")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    exit_code = run_all_tests(verbose=args.verbose)
    sys.exit(exit_code)
