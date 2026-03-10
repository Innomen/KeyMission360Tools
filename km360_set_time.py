#!/usr/bin/env python3
"""
Nikon KeyMission 360 Time Synchronization Tool
===============================================

Sets the camera's date and time to the current system time.

The KeyMission 360 has NO RTC battery - it loses date/time when the 
battery is removed or dies. This causes photos to have incorrect 
timestamps (usually showing 2016 or whatever the factory default was).

This tool automatically syncs the camera time to your computer's time.

Author: KeyMission 360 Tools Project
License: MIT
"""

import subprocess
import sys
import argparse
from datetime import datetime


def check_gphoto2():
    """Check if gphoto2 is installed"""
    try:
        result = subprocess.run(
            ["gphoto2", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
    except Exception:
        return False


def detect_camera():
    """Check if KeyMission 360 is connected"""
    try:
        result = subprocess.run(
            ["gphoto2", "--auto-detect"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return "KeyMission 360" in result.stdout
    except Exception as e:
        print(f"[!] Error detecting camera: {e}")
        return False


def get_camera_time():
    """Get current camera date/time"""
    try:
        result = subprocess.run(
            ["gphoto2", "--get-config=/main/settings/datetime"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Parse the output to find "Printable:" line
        for line in result.stdout.split('\n'):
            if 'Printable:' in line:
                return line.split(':', 1)[1].strip()
        
        return None
    except Exception as e:
        print(f"[!] Error reading camera time: {e}")
        return None


def set_camera_time():
    """Set camera time to current system time"""
    try:
        result = subprocess.run(
            ["gphoto2", "--set-config", "datetime=now"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        print(f"[!] Error setting camera time: {e}")
        return False


def run_headless_test():
    """Run basic tests without user interaction"""
    print("=" * 60)
    print("KeyMission 360 Time Sync - Headless Test Mode")
    print("=" * 60)
    print()
    
    # Test 1: Check gphoto2
    print("[TEST 1] Checking gphoto2 installation...")
    if check_gphoto2():
        print("  ✓ gphoto2 is installed")
    else:
        print("  ✗ gphoto2 not found")
        return
    
    # Test 2: Check for camera
    print("\n[TEST 2] Checking for KeyMission 360...")
    if detect_camera():
        print("  ✓ KeyMission 360 detected")
        
        # Test 3: Try to get time
        print("\n[TEST 3] Testing time read...")
        camera_time = get_camera_time()
        if camera_time:
            print(f"  ✓ Camera time: {camera_time}")
        else:
            print("  ⚠ Could not read camera time")
    else:
        print("  ⚠ KeyMission 360 not connected (expected if camera off)")
    
    # Test 4: Test datetime format
    print("\n[TEST 4] Testing datetime formatting...")
    now = datetime.now().strftime("%a %d %b %Y %I:%M:%S %p")
    print(f"  ✓ System time format: {now}")
    
    print("\n" + "=" * 60)
    print("Headless test complete")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Sync Nikon KeyMission 360 date/time to system time",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s              # Sync time and show result
  %(prog)s --check      # Only check current camera time
  %(prog)s --quiet      # Set time with minimal output
  %(prog)s --headless   # Run headless tests

Note:
  The KeyMission 360 has no RTC battery and loses time when
  the battery is removed. Run this tool after every battery change.
"""
    )
    
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Only check current camera time, don't change it"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output (errors only)"
    )
    parser.add_argument(
        "--headless", "--test", "-t",
        action="store_true",
        help="Run headless tests without changing time"
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 1.0"
    )
    
    args = parser.parse_args()
    
    # Headless test mode
    if args.headless:
        run_headless_test()
        sys.exit(0)
    
    if not args.quiet:
        print("=" * 60)
        print("Nikon KeyMission 360 Time Synchronization")
        print("=" * 60)
        print()
    
    # Check gphoto2 is installed
    if not check_gphoto2():
        print("[!] Error: gphoto2 is not installed!")
        print("    Install with: sudo apt-get install gphoto2")
        sys.exit(1)
    
    # Detect camera
    if not args.quiet:
        print("[*] Looking for KeyMission 360...")
    
    if not detect_camera():
        print("[!] Camera not found!")
        print("    Make sure the camera is:")
        print("    - Connected via USB")
        print("    - Powered on (press Photo or Video button)")
        sys.exit(1)
    
    if not args.quiet:
        print("[✓] KeyMission 360 detected")
        print()
    
    # Get current camera time
    if not args.quiet:
        print("[*] Reading current camera time...")
    
    camera_time = get_camera_time()
    
    if camera_time:
        if not args.quiet:
            print(f"[*] Camera time: {camera_time}")
    else:
        print("[!] Could not read camera time")
        camera_time = "Unknown"
    
    # If just checking, exit here
    if args.check:
        print(f"\nCurrent camera time: {camera_time}")
        sys.exit(0)
    
    # Get system time for comparison
    system_time = datetime.now().strftime("%a %d %b %Y %I:%M:%S %p")
    
    if not args.quiet:
        print(f"[*] System time:   {system_time}")
        print()
        print("[*] Setting camera time to system time...")
    
    # Set the time
    if set_camera_time():
        if not args.quiet:
            print("[✓] Time synchronized successfully!")
            print()
            print("[*] Verifying...")
        
        # Verify the change
        new_camera_time = get_camera_time()
        
        if new_camera_time:
            if not args.quiet:
                print(f"[✓] New camera time: {new_camera_time}")
                print()
                print("=" * 60)
                print("Time sync complete. Your photos will now have")
                print("the correct timestamp.")
                print("=" * 60)
            else:
                print(f"Camera time set to: {new_camera_time}")
        else:
            print("[!] Could not verify new time (but command succeeded)")
            
    else:
        print("[!] Failed to set camera time!")
        print("    Try running with sudo if permission denied.")
        sys.exit(1)


if __name__ == "__main__":
    main()
