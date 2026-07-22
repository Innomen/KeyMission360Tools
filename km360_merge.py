#!/usr/bin/env python3
"""
KeyMission 360 Video Merge Tool
===============================

Losslessly merge/concatenate video files while preserving 360° metadata.

This tool uses ffmpeg's concat demuxer to losslessly merge videos without
re-encoding. It also preserves or re-injects 360° spherical metadata so
YouTube will recognize the merged video as 360° content.

Auto-detection:
  When using --auto, the tool analyzes input files to detect if they appear
to be parts of a single recording session. Detection criteria:
  - Sequential file naming (e.g., DSCN0016.MP4, DSCN0017.MP4)
  - Similar creation timestamps (within gap-tolerance)
  - Matching video parameters (codec, resolution, frame rate)

Usage:
    python3 km360_merge.py -o output.mp4 input1.MP4 input2.MP4
    python3 km360_merge.py --auto -o output.mp4 DSCN*.MP4
    python3 km360_merge.py --detect-only DSCN*.MP4
    python3 km360_merge.py --headless  # Test mode

Requirements:
    - ffmpeg (for video concatenation)
    - exiftool (optional, for best 360° metadata injection)

Author: KeyMission 360 Tools Project
License: MIT
"""

import argparse
import subprocess
import sys
import os
import json
import tempfile
import glob
from pathlib import Path
from datetime import datetime


def format_size_bytes(size):
    """Format bytes to human readable string"""
    if size is None:
        return "Unknown"
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def get_video_info(filepath):
    """Get video metadata using ffprobe"""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            filepath,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        info = {
            "filepath": filepath,
            "duration": 0,
            "creation_time": None,
            "creation_time_ts": 0,
            "video_codec": None,
            "audio_codec": None,
            "width": 0,
            "height": 0,
            "fps": 0,
        }

        # Get format info
        format_info = data.get("format", {})
        info["duration"] = float(format_info.get("duration", 0))

        # Get stream info
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                info["video_codec"] = stream.get("codec_name")
                info["width"] = stream.get("width")
                info["height"] = stream.get("height")

                # Calculate FPS
                fps_str = stream.get("r_frame_rate", "0/1")
                if "/" in fps_str:
                    num, den = fps_str.split("/")
                    info["fps"] = float(num) / float(den) if float(den) != 0 else 0
                else:
                    info["fps"] = float(fps_str)

                # Get creation time from tags
                tags = stream.get("tags", {})
                creation = tags.get("creation_time")
                if creation:
                    info["creation_time"] = creation
                    try:
                        dt = datetime.fromisoformat(creation.replace("Z", "+00:00"))
                        info["creation_time_ts"] = dt.timestamp()
                    except:
                        pass

            elif stream.get("codec_type") == "audio":
                info["audio_codec"] = stream.get("codec_name")

        return info
    except Exception:
        return None


def check_video_compatibility(files):
    """Check if video files are compatible for concatenation"""
    if not files:
        return {"compatible": False, "issues": ["no files"]}

    issues = []
    base_info = get_video_info(files[0])

    if not base_info:
        return {"compatible": False, "issues": ["could not read first file"]}

    result = {
        "compatible": True,
        "video_codec": base_info.get("video_codec"),
        "audio_codec": base_info.get("audio_codec"),
        "resolution": f"{base_info.get('width')}x{base_info.get('height')}",
        "fps": base_info.get("fps"),
        "issues": [],
    }

    for f in files[1:]:
        info = get_video_info(f)
        if not info:
            issues.append(f"{Path(f).name}: could not read file")
            continue

        if info.get("video_codec") != base_info.get("video_codec"):
            issues.append(
                f"{Path(f).name}: video codec mismatch ({info.get('video_codec')} vs {base_info.get('video_codec')})"
            )

        if info.get("width") != base_info.get("width") or info.get(
            "height"
        ) != base_info.get("height"):
            issues.append(
                f"{Path(f).name}: resolution mismatch ({info.get('width')}x{info.get('height')} vs {base_info.get('width')}x{base_info.get('height')})"
            )

        if info.get("fps") and base_info.get("fps"):
            fps_diff = abs(info["fps"] - base_info["fps"])
            if fps_diff > 0.1:
                issues.append(
                    f"{Path(f).name}: frame rate mismatch ({info['fps']:.2f} vs {base_info['fps']:.2f})"
                )

    if issues:
        result["compatible"] = False
        result["issues"] = issues

    return result


def extract_360_metadata(filepath):
    """Extract 360° spherical metadata from video file"""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            filepath,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                # Check side_data_list for spherical mapping
                side_data = stream.get("side_data_list", [])
                for sd in side_data:
                    if "spherical" in sd.get("side_data_type", "").lower():
                        return {
                            "projection": sd.get("projection", "equirectangular"),
                            "yaw": sd.get("yaw", 0),
                            "pitch": sd.get("pitch", 0),
                            "roll": sd.get("roll", 0),
                        }

                # Check tags
                tags = stream.get("tags", {})
                if tags.get("spherical") or tags.get("projection_type"):
                    return {
                        "projection": tags.get("projection_type", "equirectangular"),
                        "spherical": tags.get("spherical"),
                        "stereo_mode": tags.get("stereo_mode", "mono"),
                    }

        return None
    except Exception:
        return None


def detect_recording_sessions(files, gap_tolerance=3.0):
    """
    Auto-detect which files are parts of a single recording session.

    Detection criteria:
    1. Sequential file naming (e.g., DSCN0016.MP4, DSCN0017.MP4)
    2. Similar creation timestamps (within gap_tolerance seconds)
    3. Matching video parameters (codec, resolution, frame rate)

    Returns: List of files that belong to the same session
    """
    print("Analyzing files for recording session detection...")

    # Get metadata for all files
    file_info = []
    for f in files:
        info = get_video_info(f)
        if info:
            file_info.append((f, info))

    if len(file_info) < 2:
        return files

    # Sort by filename (which usually correlates with recording order)
    file_info.sort(key=lambda x: x[0])

    # Group files by session
    sessions = []
    current_session = [file_info[0]]

    for i in range(1, len(file_info)):
        prev_file, prev_info = current_session[-1]
        curr_file, curr_info = file_info[i]

        is_continuous = True
        issues = []

        # Check 1: Sequential naming
        prev_name = Path(prev_file).stem
        curr_name = Path(curr_file).stem

        # Try to extract numbers from filenames
        prev_nums = "".join(c if c.isdigit() else " " for c in prev_name).split()
        curr_nums = "".join(c if c.isdigit() else " " for c in curr_name).split()

        if prev_nums and curr_nums:
            try:
                prev_num = int(prev_nums[-1])
                curr_num = int(curr_nums[-1])
                if curr_num != prev_num + 1:
                    is_continuous = False
                    issues.append(
                        f"non-sequential numbering ({prev_num} -> {curr_num})"
                    )
            except ValueError:
                pass

        # Check 2: Timestamp gap
        if prev_info.get("duration") and curr_info.get("creation_time"):
            prev_end = prev_info.get("creation_time_ts", 0) + prev_info.get(
                "duration", 0
            )
            curr_start = curr_info.get("creation_time_ts", 0)
            gap = curr_start - prev_end

            if gap > gap_tolerance:
                is_continuous = False
                issues.append(f"time gap too large ({gap:.1f}s > {gap_tolerance}s)")

        # Check 3: Video parameters match
        if prev_info.get("video_codec") != curr_info.get("video_codec"):
            is_continuous = False
            issues.append("different video codec")

        if prev_info.get("width") != curr_info.get("width") or prev_info.get(
            "height"
        ) != curr_info.get("height"):
            is_continuous = False
            issues.append("different resolution")

        if prev_info.get("fps") and curr_info.get("fps"):
            fps_diff = abs(prev_info["fps"] - curr_info["fps"])
            if fps_diff > 0.1:
                is_continuous = False
                issues.append("different frame rate")

        if is_continuous:
            current_session.append((curr_file, curr_info))
        else:
            sessions.append(current_session)
            current_session = [(curr_file, curr_info)]

            print(f"  Break after {Path(prev_file).name} -> {Path(curr_file).name}:")
            for issue in issues:
                print(f"    - {issue}")

    sessions.append(current_session)

    print()
    print(f"Detected {len(sessions)} recording session(s):")
    for i, session in enumerate(sessions, 1):
        print(f"  Session {i}: {len(session)} file(s)")
        for f, _ in session[:3]:
            print(f"    - {Path(f).name}")
        if len(session) > 3:
            print(f"    ... and {len(session) - 3} more")
    print()

    # Return the largest session
    if sessions:
        largest = max(sessions, key=len)
        if len(largest) > 1:
            return [f for f, _ in largest]

    return files


def merge_videos_ffmpeg(input_files, output_file, metadata=None):
    """
    Merge videos using ffmpeg concat demuxer (lossless, no re-encoding).

    Args:
        input_files: List of input video file paths
        output_file: Path for output merged video
        metadata: Dict with 360° metadata to inject (optional)

    Returns:
        True if successful, False otherwise
    """
    # Create concat list file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        concat_file = f.name
        for input_file in input_files:
            # Get absolute path and escape single quotes
            abs_path = os.path.abspath(input_file)
            escaped = abs_path.replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")

    try:
        # Build ffmpeg command
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_file,
            "-c",
            "copy",
            "-movflags",
            "+faststart",
        ]

        # Add metadata if available
        if metadata:
            projection = metadata.get("projection", "equirectangular")
            cmd.extend(
                [
                    "-metadata:s:v:0",
                    "spherical=1",
                    "-metadata:s:v:0",
                    f"projection_type={projection}",
                    "-metadata:s:v:0",
                    "stereo_mode=mono",
                ]
            )

            # Add initial view if available
            if "yaw" in metadata:
                cmd.extend(
                    ["-metadata:s:v:0", f"initial_view_heading={metadata['yaw']}"]
                )
            if "pitch" in metadata:
                cmd.extend(
                    ["-metadata:s:v:0", f"initial_view_pitch={metadata['pitch']}"]
                )
            if "roll" in metadata:
                cmd.extend(["-metadata:s:v:0", f"initial_view_roll={metadata['roll']}"])

        cmd.append(output_file)

        # Run ffmpeg
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

        if result.returncode != 0:
            print(f"[!] ffmpeg error: {result.stderr[-500:]}")
            return False

        # Verify output file was created
        if not Path(output_file).exists():
            print("[!] Output file was not created")
            return False

        # If we had 360 metadata, verify or re-inject with exiftool if available
        if metadata:
            reinject_360_metadata(output_file, metadata)

        return True

    finally:
        # Clean up concat file
        try:
            os.unlink(concat_file)
        except:
            pass


def reinject_360_metadata(output_file, metadata):
    """
    Re-inject 360° metadata using exiftool if available.
    This ensures YouTube properly recognizes the merged video.
    """
    # Check for exiftool
    exiftool_path = None
    for path in ["exiftool", "/usr/bin/exiftool", "/usr/local/bin/exiftool"]:
        try:
            result = subprocess.run([path, "-ver"], capture_output=True, timeout=5)
            if result.returncode == 0:
                exiftool_path = path
                break
        except:
            continue

    if not exiftool_path:
        print("  Note: exiftool not found. Metadata preserved via ffmpeg.")
        print(
            "  For best YouTube compatibility, install: sudo pacman -S perl-image-exiftool"
        )
        return

    try:
        cmd = [
            exiftool_path,
            "-XMP-GSpherical:Spherical=true",
            "-XMP-GSpherical:Stitched=true",
            "-XMP-GSpherical:StitchingSoftware=KeyMission360Tools",
            "-XMP-GSpherical:ProjectionType=equirectangular",
            "-XMP-GSpherical:StereoMode=mono",
            "-overwrite_original",
            output_file,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print("  ✓ 360° metadata re-injected with exiftool")
        else:
            print(f"  Note: exiftool metadata injection returned: {result.stderr}")

    except Exception as e:
        print(f"  Note: Could not re-inject metadata with exiftool: {e}")


def run_headless_test():
    """Run tests without actual processing"""
    print("=" * 60)
    print("KeyMission 360 Merge Tool - Headless Test Mode")
    print("=" * 60)
    print()

    # Test 1: Check ffmpeg
    print("[TEST 1] Checking ffmpeg...")
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.split("\n")[0]
            print(f"  ✓ {version}")
        else:
            print("  ✗ ffmpeg not working properly")
    except Exception as e:
        print(f"  ✗ ffmpeg not found: {e}")

    # Test 2: Check exiftool
    print("\n[TEST 2] Checking exiftool...")
    try:
        result = subprocess.run(
            ["exiftool", "-ver"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print(f"  ✓ ExifTool version {result.stdout.strip()}")
        else:
            print("  ⚠ exiftool not available (optional but recommended)")
    except:
        print("  ⚠ exiftool not installed (optional but recommended)")

    # Test 3: Check ffprobe
    print("\n[TEST 3] Checking ffprobe...")
    try:
        result = subprocess.run(
            ["ffprobe", "-version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.split("\n")[0]
            print(f"  ✓ {version}")
        else:
            print("  ✗ ffprobe not working properly")
    except:
        print("  ✗ ffprobe not found")

    print("\n" + "=" * 60)
    print("Headless test complete")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Losslessly merge KeyMission 360 videos while preserving 360° metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -o merged.mp4 part1.MP4 part2.MP4 part3.MP4
  %(prog)s --auto -o merged.mp4 DSCN*.MP4
  %(prog)s --detect-only DSCN*.MP4
  %(prog)s --headless

Auto-detection:
  Use --auto to automatically detect which files are part of the same
  recording session based on filename patterns and timestamps.

Metadata:
  360° spherical metadata is extracted from the first file and preserved
  in the merged output. The metadata is re-injected using exiftool if
  available for best YouTube compatibility.

Compatibility:
  Videos must have the same codec, resolution, and frame rate to be
  merged losslessly.
        """,
    )

    parser.add_argument(
        "inputs", nargs="*", help="Input video files to merge (in order)"
    )
    parser.add_argument("--output", "-o", help="Output merged video file")
    parser.add_argument(
        "--auto",
        "-a",
        action="store_true",
        help="Auto-detect split files by filename pattern",
    )
    parser.add_argument(
        "--detect-only",
        "-d",
        action="store_true",
        help="Only detect and show which files would be merged",
    )
    parser.add_argument(
        "--gap-tolerance",
        "-g",
        type=float,
        default=3.0,
        help="Max seconds gap between files (default: 3)",
    )
    parser.add_argument(
        "--headless", "--test", "-t", action="store_true", help="Run tests only"
    )

    args = parser.parse_args()

    # Headless test mode
    if args.headless:
        run_headless_test()
        sys.exit(0)

    if not args.inputs:
        parser.print_help()
        sys.exit(1)

    if not args.output and not args.detect_only:
        print("[!] Please specify an output file with --output")
        sys.exit(1)

    # Expand any glob patterns and validate files
    input_files = []
    for pattern in args.inputs:
        expanded = glob.glob(pattern)
        if expanded:
            input_files.extend(expanded)
        elif os.path.exists(pattern):
            input_files.append(pattern)

    if not input_files:
        print("[!] No valid input files found")
        sys.exit(1)

    # Sort and deduplicate
    input_files = sorted(set(input_files))

    # Auto-detect mode
    if args.auto:
        input_files = detect_recording_sessions(input_files, args.gap_tolerance)
        if not input_files:
            print("[!] No files found that match the auto-detection criteria")
            sys.exit(1)

    # Validate all input files
    valid_files = []
    for f in input_files:
        path = Path(f)
        if not path.exists():
            print(f"[!] File not found: {f}")
            continue
        if path.suffix.lower() not in [".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp"]:
            print(f"[!] Skipping non-video file: {f}")
            continue
        valid_files.append(f)

    if len(valid_files) < 2:
        print("[!] Need at least 2 video files to merge")
        sys.exit(1)

    input_files = valid_files

    print("=" * 60)
    print("KeyMission 360 - Video Merge Tool")
    print("=" * 60)
    print()

    print(f"Files to merge ({len(input_files)}):")
    total_size = 0
    for i, f in enumerate(input_files, 1):
        size = Path(f).stat().st_size
        total_size += size
        print(f"  {i}. {Path(f).name} ({format_size_bytes(size)})")
    print(f"\nTotal input size: {format_size_bytes(total_size)}")
    if args.output:
        print(f"Output: {args.output}")
    print()

    # Detect-only mode
    if args.detect_only:
        print("[Detect-only mode] The following files would be merged:")
        for f in input_files:
            print(f"  - {f}")
        sys.exit(0)

    # Check output file doesn't exist
    output_path = Path(args.output)
    if output_path.exists():
        response = input(
            f"[!] Output file exists: {args.output}\n    Overwrite? (y/N): "
        )
        if response.lower() != "y":
            print("Cancelled.")
            sys.exit(0)

    # Check ffmpeg
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        if result.returncode != 0:
            print("[!] ffmpeg not found. Please install ffmpeg.")
            sys.exit(1)
    except:
        print("[!] ffmpeg not found. Please install ffmpeg.")
        sys.exit(1)

    # Check compatibility
    print("Checking video compatibility...")
    compat = check_video_compatibility(input_files)
    if not compat["compatible"]:
        print("[!] Video files are not compatible for merging:")
        for issue in compat["issues"]:
            print(f"    - {issue}")
        print("\nVideos must have the same codec, resolution, and frame rate.")
        sys.exit(1)

    print(
        f"  ✓ All videos compatible ({compat['video_codec']}, {compat['resolution']}, {compat['fps']:.2f} fps)"
    )
    print()

    # Extract 360° metadata
    print("Extracting 360° metadata...")
    metadata = extract_360_metadata(input_files[0])
    if metadata:
        print(
            f"  ✓ Found 360° metadata: {metadata.get('projection', 'unknown')} projection"
        )
    else:
        print("  ⚠ No 360° metadata found in first file")
    print()

    # Perform the merge
    print("Merging videos (lossless, no re-encoding)...")
    print("  This may take a while depending on file sizes.")
    print()

    success = merge_videos_ffmpeg(input_files, args.output, metadata)

    if success:
        output_size = Path(args.output).stat().st_size
        print()
        print("=" * 60)
        print("✓ Merge complete!")
        print(f"  Output: {args.output}")
        print(f"  Size: {format_size_bytes(output_size)}")
        if metadata:
            print("  360° metadata: Preserved")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("[!] Merge failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
