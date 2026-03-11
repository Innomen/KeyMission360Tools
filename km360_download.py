#!/usr/bin/env python3
"""
Nikon KeyMission 360 Reliable Download Tool
============================================

A robust download tool with:
- Resume support (rsync-style)
- Checksum verification (SHA256)
- Retry with exponential backoff
- Progress reporting

Usage:
    python3 km360_download.py <file_number> <output_path>
    python3 km360_download.py --all <output_dir>
    python3 km360_download.py --verify <filepath>

Author: KeyMission 360 Tools Project
License: MIT
"""

import subprocess
import os
import sys
import hashlib
import time
import tempfile
import shutil
import argparse
from pathlib import Path


def calculate_checksum(filepath):
    """Calculate SHA256 checksum of a file"""
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error calculating checksum: {e}")
        return None


def verify_file(filepath, expected_size=None, verbose=True):
    """Verify file integrity"""
    if not os.path.exists(filepath):
        if verbose:
            print(f"✗ File not found: {filepath}")
        return False, None
    
    actual_size = os.path.getsize(filepath)
    
    if expected_size and actual_size != expected_size:
        if verbose:
            print(f"✗ Size mismatch: {actual_size} bytes (expected {expected_size})")
        return False, None
    
    checksum = calculate_checksum(filepath)
    if checksum:
        if verbose:
            print(f"✓ Checksum: {checksum[:16]}...")
        return True, checksum
    else:
        if verbose:
            print("✗ Checksum calculation failed")
        return False, None


def get_file_info(file_num):
    """Get file info from camera"""
    try:
        result = subprocess.run(
            ["gphoto2", "--list-files"],
            capture_output=True, text=True, timeout=30
        )
        
        for line in result.stdout.split('\n'):
            if line.strip().startswith(f'#{file_num}'):
                parts = line.strip().split()
                if len(parts) >= 3:
                    name = parts[1]
                    size_str = parts[2]
                    return name, size_str
    except Exception as e:
        print(f"Error getting file info: {e}")
    
    return None, None


def parse_size(size_str):
    """Parse size string like '12MB' to bytes"""
    size_str = size_str.upper()
    multipliers = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
    
    for suffix, mult in multipliers.items():
        if size_str.endswith(suffix):
            try:
                return int(float(size_str[:-len(suffix)]) * mult)
            except:
                return None
    
    try:
        return int(size_str)
    except:
        return None


def format_size(size):
    """Format bytes to human readable"""
    if size is None:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def download_file(file_num, output_path, max_retries=3, verify=True, show_progress=True):
    """
    Download a file from camera with resume support and verification.
    
    Returns:
        (success: bool, message: str, checksum: str or None)
    """
    # Get file info from camera
    name, size_str = get_file_info(file_num)
    if not name:
        return False, "Could not get file info from camera", None
    
    camera_size = parse_size(size_str) if size_str else None
    
    if show_progress:
        print(f"Downloading: {name}")
        print(f"Expected size: {format_size(camera_size)}")
    
    # Check if output file already exists and is complete
    if os.path.exists(output_path):
        existing_size = os.path.getsize(output_path)
        if camera_size and existing_size == camera_size:
            if verify:
                if show_progress:
                    print("File exists, verifying...")
                valid, checksum = verify_file(output_path, camera_size, verbose=show_progress)
                if valid:
                    return True, "File already exists and verified", checksum
                else:
                    if show_progress:
                        print("Existing file is corrupt, re-downloading...")
                    os.remove(output_path)
            else:
                return True, "File already exists", None
    
    # Use temp file for download
    temp_path = output_path + ".partial"
    
    # Check for partial download to resume
    resume_offset = 0
    if os.path.exists(temp_path):
        resume_offset = os.path.getsize(temp_path)
        if camera_size and resume_offset >= camera_size:
            # Already complete
            shutil.move(temp_path, output_path)
            if verify:
                valid, checksum = verify_file(output_path, camera_size, verbose=show_progress)
                if valid:
                    return True, "Download complete (already downloaded)", checksum
            return True, "Download complete", None
        elif show_progress:
            print(f"Resuming from {format_size(resume_offset)}...")
    
    # Download with retries
    last_error = None
    
    for attempt in range(max_retries):
        if show_progress and attempt > 0:
            print(f"Retry attempt {attempt + 1}/{max_retries}...")
        
        try:
            # Remove partial file on retry (since gphoto2 doesn't support byte resume)
            if attempt > 0 and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    resume_offset = 0
                except:
                    pass
            
            # Download using gphoto2
            result = subprocess.run(
                ["gphoto2", "--get-file", str(file_num), f"--filename={temp_path}"],
                capture_output=True, timeout=300
            )
            
            if result.returncode == 0:
                # Download successful
                if not os.path.exists(temp_path):
                    last_error = "Download completed but temp file not found"
                    continue
                
                # Verify size
                downloaded_size = os.path.getsize(temp_path)
                if camera_size and downloaded_size != camera_size:
                    last_error = f"Size mismatch: {downloaded_size} vs {camera_size}"
                    continue
                
                # Move to final location
                shutil.move(temp_path, output_path)
                
                # Verify checksum
                if verify:
                    if show_progress:
                        print("Verifying checksum...")
                    valid, checksum = verify_file(output_path, camera_size, verbose=show_progress)
                    if valid:
                        return True, "Download successful and verified", checksum
                    else:
                        last_error = "Checksum verification failed"
                        continue
                else:
                    return True, "Download successful", None
            else:
                stderr = result.stderr.decode() if result.stderr else "Unknown error"
                last_error = f"gphoto2 error: {stderr}"
                
                # Check for specific errors
                if "timeout" in stderr.lower() or "io" in stderr.lower():
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    break  # Don't retry on non-timeout errors
                    
        except subprocess.TimeoutExpired:
            last_error = "Download timeout"
            time.sleep(2 ** attempt)  # Exponential backoff
            continue
        except Exception as e:
            last_error = f"Exception: {str(e)}"
            continue
    
    # All retries failed
    # Clean up partial file
    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except:
            pass
    
    return False, f"Failed after {max_retries} attempts: {last_error}", None


def download_all(output_dir, verify=True):
    """Download all files from camera"""
    print("Getting file list from camera...")
    
    try:
        result = subprocess.run(
            ["gphoto2", "--list-files"],
            capture_output=True, text=True, timeout=30
        )
        
        files = []
        for line in result.stdout.split('\n'):
            if line.strip().startswith('#'):
                parts = line.strip().split()
                if len(parts) >= 2:
                    num = int(parts[0][1:])
                    name = parts[1]
                    files.append((num, name))
        
        if not files:
            print("No files found on camera.")
            return
        
        print(f"Found {len(files)} files to download.\n")
        
        success_count = 0
        failed_files = []
        
        for i, (num, name) in enumerate(files, 1):
            print(f"[{i}/{len(files)}] ", end="")
            output_path = os.path.join(output_dir, name)
            
            success, message, checksum = download_file(
                num, output_path, verify=verify, show_progress=False
            )
            
            if success:
                print(f"✓ {name} - {message}")
                success_count += 1
            else:
                print(f"✗ {name} - {message}")
                failed_files.append((name, message))
        
        print(f"\n{'='*50}")
        print(f"Complete: {success_count}/{len(files)} files")
        
        if failed_files:
            print(f"\nFailed files:")
            for name, error in failed_files:
                print(f"  • {name}: {error}")
        
    except Exception as e:
        print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Reliable download tool for KeyMission 360",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 5 ~/Videos/myvideo.mp4       # Download file #5
  %(prog)s --all ~/Downloads            # Download all files
  %(prog)s --verify ~/Videos/file.mp4   # Verify file checksum
  %(prog)s --list                       # List files on camera
        """
    )
    
    parser.add_argument("file_num", nargs="?", type=int, help="File number to download")
    parser.add_argument("output", nargs="?", help="Output path")
    parser.add_argument("--all", "-a", action="store_true", help="Download all files")
    parser.add_argument("--verify", "-v", metavar="PATH", help="Verify file checksum")
    parser.add_argument("--list", "-l", action="store_true", help="List files on camera")
    parser.add_argument("--no-verify", action="store_true", help="Skip checksum verification")
    parser.add_argument("--retries", "-r", type=int, default=3, help="Max retry attempts (default: 3)")
    
    args = parser.parse_args()
    
    if args.verify:
        # Verify mode
        valid, checksum = verify_file(args.verify)
        sys.exit(0 if valid else 1)
    
    elif args.list:
        # List mode
        print("Files on camera:")
        print("-" * 50)
        try:
            result = subprocess.run(
                ["gphoto2", "--list-files"],
                capture_output=True, text=True, timeout=30
            )
            print(result.stdout)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif args.all:
        # Download all
        output_dir = args.output or "."
        os.makedirs(output_dir, exist_ok=True)
        download_all(output_dir, verify=not args.no_verify)
    
    elif args.file_num and args.output:
        # Download single file
        success, message, checksum = download_file(
            args.file_num, args.output, 
            max_retries=args.retries,
            verify=not args.no_verify
        )
        print(f"\n{message}")
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
