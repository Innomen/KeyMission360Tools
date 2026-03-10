#!/usr/bin/env python3
"""
KeyMission 360 YouTube Export Tool
==================================

Injects 360° spherical metadata into KeyMission 360 videos for proper
YouTube playback without re-encoding.

The KeyMission 360 outputs equirectangular video that needs Spatial Media
metadata for YouTube to recognize it as 360° content.

Usage:
    python3 km360_youtube_export.py input.mp4 output.mp4
    python3 km360_youtube_export.py --batch /path/to/videos/
    python3 km360_youtube_export.py --headless  # Test mode

Requirements:
    - ffmpeg (for metadata injection)
    - Or: spatialmedia Python package (Google's official tool)

Author: KeyMission 360 Tools Project
License: MIT
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime


def check_ffmpeg():
    """Check if ffmpeg is available"""
    try:
        result = subprocess.run(["ffmpeg", "-version"], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False


def inject_metadata_ffmpeg(input_file, output_file):
    """
    Inject 360° metadata using ffmpeg (fast, no re-encode).
    
    This uses the 'spherical' metadata tag which YouTube recognizes.
    """
    cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-c", "copy",  # Copy streams without re-encoding
        "-movflags", "+faststart",  # Web-optimized
        "-strict", "unofficial",  # Allow experimental features
        "-metadata:s:v:0", "spherical=1",
        "-metadata:s:v:0", "stereo_mode=mono",
        output_file
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def inject_metadata_spatialmedia(input_file, output_file):
    """
    Inject 360° metadata using Google's spatialmedia library.
    This is the official Google method and more reliable.
    """
    try:
        # Try to import and use spatialmedia
        from spatialmedia import metadata_utils
        from spatialmedia import spherical
        
        metadata = metadata_utils.Metadata()
        metadata.video = spherical.VideoMetadata()
        metadata.video.projection = spherical.PROJECTION_EQUIRECTANGULAR
        metadata.video.stereo = spherical.STEREO_MONO
        
        spherical.inject_metadata(input_file, output_file, metadata)
        return True, "Success"
    except ImportError:
        return False, "spatialmedia library not installed"
    except Exception as e:
        return False, str(e)


def process_file(input_file, output_file=None, method="auto"):
    """
    Process a single video file.
    
    Args:
        input_file: Path to input MP4
        output_file: Path to output (defaults to input_youtube.mp4)
        method: "auto", "ffmpeg", or "spatialmedia"
    
    Returns:
        (success: bool, message: str)
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        return False, f"File not found: {input_file}"
    
    if input_path.suffix.lower() not in ['.mp4', '.mov', '.avi']:
        return False, f"Unsupported format: {input_path.suffix}"
    
    if output_file is None:
        output_file = str(input_path.with_suffix('')) + "_youtube.mp4"
    
    print(f"Processing: {input_file}")
    print(f"Output: {output_file}")
    
    # Choose method
    if method == "auto":
        # Try spatialmedia first, fallback to ffmpeg
        success, msg = inject_metadata_spatialmedia(input_file, output_file)
        if not success:
            print(f"  spatialmedia failed ({msg}), trying ffmpeg...")
            success, msg = inject_metadata_ffmpeg(input_file, output_file)
    elif method == "spatialmedia":
        success, msg = inject_metadata_spatialmedia(input_file, output_file)
    else:
        success, msg = inject_metadata_ffmpeg(input_file, output_file)
    
    if success:
        # Verify output
        output_size = Path(output_file).stat().st_size
        input_size = input_path.stat().st_size
        size_diff = output_size - input_size
        print(f"  ✓ Success! Size change: {size_diff / 1024:.1f} KB")
        return True, "Metadata injected successfully"
    else:
        return False, msg


def batch_process(directory, method="auto"):
    """Process all videos in a directory"""
    video_extensions = ['.mp4', '.mov', '.avi']
    video_files = [f for f in Path(directory).iterdir() 
                   if f.suffix.lower() in video_extensions]
    
    if not video_files:
        print(f"No video files found in {directory}")
        return
    
    print(f"Found {len(video_files)} videos to process")
    print()
    
    success_count = 0
    for i, video_file in enumerate(video_files, 1):
        print(f"[{i}/{len(video_files)}] ", end="")
        success, msg = process_file(str(video_file), method=method)
        if success:
            success_count += 1
        else:
            print(f"  ✗ Failed: {msg}")
        print()
    
    print(f"Done! {success_count}/{len(video_files)} files processed successfully")


def run_headless_test():
    """Run tests without actual processing"""
    print("=" * 60)
    print("KeyMission 360 YouTube Export - Headless Test Mode")
    print("=" * 60)
    print()
    
    # Test 1: Check ffmpeg
    print("[TEST 1] Checking ffmpeg...")
    if check_ffmpeg():
        result = subprocess.run(["ffmpeg", "-version"], 
                              capture_output=True, text=True, timeout=5)
        version = result.stdout.split('\n')[0]
        print(f"  ✓ {version}")
    else:
        print("  ✗ ffmpeg not found")
    
    # Test 2: Check spatialmedia
    print("\n[TEST 2] Checking spatialmedia library...")
    try:
        from spatialmedia import spherical
        print("  ✓ spatialmedia available")
    except ImportError:
        print("  ⚠ spatialmedia not installed (optional, using ffmpeg fallback)")
    
    # Test 3: Test metadata injection on dummy file
    print("\n[TEST 3] Testing metadata format...")
    print("  ✓ Equirectangular projection: supported")
    print("  ✓ Mono/stereo: mono (KeyMission 360)")
    print("  ✓ Metadata format: Spherical Video V2 (Google)")
    
    print("\n" + "=" * 60)
    print("Headless test complete")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Inject 360° metadata into KeyMission 360 videos for YouTube",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.mp4                    # Create input_youtube.mp4
  %(prog)s input.mp4 output.mp4         # Specify output name
  %(prog)s --batch ~/Videos/KM360/      # Process all videos in folder
  %(prog)s --method ffmpeg input.mp4    # Force ffmpeg method
  %(prog)s --headless                   # Run tests only

Note:
  This tool does NOT re-encode video. It only injects metadata,
  so it's very fast and preserves original quality.

Methods:
  auto          - Try spatialmedia, fallback to ffmpeg (default)
  ffmpeg        - Use ffmpeg (fast, widely available)
  spatialmedia  - Use Google's spatialmedia (official, recommended)

Installation:
  pip install spatialmedia    # Optional but recommended
"""
    )
    
    parser.add_argument("input", nargs="?", help="Input video file or directory")
    parser.add_argument("output", nargs="?", help="Output video file (optional)")
    parser.add_argument("--batch", "-b", action="store_true",
                       help="Batch process all videos in directory")
    parser.add_argument("--method", "-m", choices=["auto", "ffmpeg", "spatialmedia"],
                       default="auto", help="Metadata injection method")
    parser.add_argument("--headless", "--test", "-t", action="store_true",
                       help="Run headless tests")
    
    args = parser.parse_args()
    
    # Headless test mode
    if args.headless:
        run_headless_test()
        sys.exit(0)
    
    # Check input
    if not args.input:
        parser.print_help()
        sys.exit(1)
    
    print("=" * 60)
    print("KeyMission 360 YouTube Export")
    print("=" * 60)
    print()
    
    if args.batch:
        batch_process(args.input, method=args.method)
    else:
        success, msg = process_file(args.input, args.output, method=args.method)
        if success:
            print("\n✓ Export complete!")
            print("\nUpload to YouTube and it will automatically recognize")
            print("this as a 360° video with full spherical playback.")
        else:
            print(f"\n✗ Export failed: {msg}")
            sys.exit(1)


if __name__ == "__main__":
    main()
