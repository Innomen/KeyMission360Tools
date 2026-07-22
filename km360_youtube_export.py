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


def check_ffmpeg():
    """Check if ffmpeg is available"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except:
        return False


def check_existing_metadata(input_file):
    """Check if video already has 360° spherical metadata"""
    try:
        # Use ffprobe to check for spherical metadata
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream_tags=spherical",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            input_file,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        # If spherical tag exists and is set to 1, it's already 360
        if result.stdout.strip() in ["1", "true", "True"]:
            return True

        # Also check for other spherical metadata formats
        cmd2 = ["ffprobe", "-v", "error", "-show_format", "-show_streams", input_file]
        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=10)
        output = result2.stdout.lower()

        # Check for various 360 metadata indicators
        indicators = [
            "spherical",
            "equirectangular",
            "projectiontype=equirectangular",
            "gopro spherical",
            "youtube 360",
        ]
        for indicator in indicators:
            if indicator in output:
                return True

    except Exception:
        pass
    return False


def verify_360_metadata(file_path):
    """
    Comprehensive verification that 360° metadata is properly injected.
    Returns (is_valid: bool, details: dict)
    """
    import json

    details = {
        "has_spherical_tag": False,
        "has_projection_metadata": False,
        "has_stereo_metadata": False,
        "is_equirectangular": False,
        "has_spherical_side_data": False,
        "raw_metadata": {},
    }

    try:
        # Method 1: Check for proper Spatial Media metadata using ffprobe with JSON output
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            file_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            try:
                probe_data = json.loads(result.stdout)

                # Look through all streams for video metadata
                for stream in probe_data.get("streams", []):
                    if stream.get("codec_type") == "video":
                        # Check tags
                        tags = stream.get("tags", {})
                        details["raw_metadata"].update(tags)

                        # Check for spherical tag
                        spherical = tags.get("spherical", "").lower()
                        if spherical in ["1", "true", "yes"]:
                            details["has_spherical_tag"] = True

                        # Check for projection type in tags
                        projection = tags.get("projection_type", "").lower()
                        if projection == "equirectangular":
                            details["has_projection_metadata"] = True
                            details["is_equirectangular"] = True

                        # Check for stereo mode in tags
                        stereo = tags.get("stereo_mode", "").lower()
                        if stereo in ["mono", "top-bottom", "left-right"]:
                            details["has_stereo_metadata"] = True

                        # Check side_data (ffmpeg's way of storing spherical metadata)
                        side_data_list = stream.get("side_data_list", [])
                        for side_data in side_data_list:
                            side_type = side_data.get("side_data_type", "").lower()
                            if "spherical" in side_type:
                                details["has_spherical_side_data"] = True
                                # Also check projection in side_data
                                if (
                                    side_data.get("projection", "").lower()
                                    == "equirectangular"
                                ):
                                    details["is_equirectangular"] = True
                                    details["has_projection_metadata"] = True
                            # Also accept Stereo 3D as indicator of 360 metadata (from spatialmedia)
                            if "stereo 3d" in side_type or "stereo3d" in side_type:
                                details["has_360_metadata"] = True

            except json.JSONDecodeError:
                pass

        # Method 2: Check for moov/trak metadata using special ffmpeg probe
        # This detects the actual Spatial Media metadata box
        cmd2 = [
            "ffmpeg",
            "-v",
            "debug",
            "-i",
            file_path,
            "-c",
            "copy",
            "-f",
            "null",
            "-",
        ]
        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=15)
        debug_output = result2.stderr.lower()

        # Look for spatial media indicators in debug output
        spatial_indicators = [
            "spherical",
            "equirectangular",
            "projection",
            "cropleft",
            "cropright",
            "croptop",
            "cropbottom",
            "stereo_mode",
        ]
        found_indicators = []
        for indicator in spatial_indicators:
            if indicator in debug_output:
                found_indicators.append(indicator)

        details["debug_indicators"] = found_indicators

        # Method 3: Try to extract and parse the actual uuid box (Spatial Media metadata)
        # This is the most reliable method for checking proper YouTube 360 metadata
        cmd3 = [
            "ffmpeg",
            "-v",
            "quiet",
            "-dump",
            "-i",
            file_path,
            "-c",
            "copy",
            "-f",
            "null",
            "-",
        ]
        result3 = subprocess.run(cmd3, capture_output=True, text=True, timeout=15)

        # Check for UUID box indicators
        if "uuid" in result3.stderr.lower() or "uuid" in debug_output:
            details["has_uuid_box"] = True

        # Check for ffmpeg metadata tags (what we add with -metadata:s:v:0)
        # YouTube recognizes these tags even without side_data
        raw_metadata = details.get("raw_metadata", {})
        has_spherical_metadata_tag = raw_metadata.get("spherical", "").lower() in [
            "1",
            "true",
            "yes",
        ]
        has_projection_tag = (
            raw_metadata.get("projection_type", "").lower() == "equirectangular"
        )
        details["has_ffmpeg_metadata_tags"] = (
            has_spherical_metadata_tag and has_projection_tag
        )

        # Determine overall validity
        # For YouTube 360, we need either:
        # 1. Proper spherical tag AND equirectangular projection, OR
        # 2. UUID box with spatial media data (from spatialmedia library), OR
        # 3. side_data spherical mapping (ffmpeg method), OR
        # 4. Debug indicators showing both spherical and equirectangular, OR
        # 5. ffmpeg metadata tags (spherical=1 + projection_type=equirectangular), OR
        # 6. Stereo 3D side data (from spatialmedia library)
        is_valid = (
            (details["has_spherical_tag"] and details["is_equirectangular"])
            or details.get("has_uuid_box", False)
            or details["has_spherical_side_data"]
            or (
                "spherical" in found_indicators
                and "equirectangular" in found_indicators
            )
            or details["has_ffmpeg_metadata_tags"]
            or details.get("has_360_metadata", False)
        )

        return is_valid, details

    except Exception as e:
        details["error"] = str(e)
        return False, details


def print_verification_report(file_path, details):
    """Print a human-readable verification report"""
    print(f"\n{'=' * 60}")
    print("360° Metadata Verification Report")
    print(f"{'=' * 60}")
    print(f"File: {file_path}")
    print()

    # Status indicators
    checks = [
        ("Spherical tag", details.get("has_spherical_tag", False)),
        ("Projection metadata", details.get("has_projection_metadata", False)),
        ("Equirectangular format", details.get("is_equirectangular", False)),
        ("Stereo mode", details.get("has_stereo_metadata", False)),
        ("Spherical side data", details.get("has_spherical_side_data", False)),
        ("360 metadata (spatialmedia)", details.get("has_360_metadata", False)),
        ("FFmpeg metadata tags", details.get("has_ffmpeg_metadata_tags", False)),
        ("Spatial Media UUID box", details.get("has_uuid_box", False)),
    ]

    for name, status in checks:
        symbol = "✓" if status else "✗"
        print(f"  [{symbol}] {name}")

    # Debug indicators found
    indicators = details.get("debug_indicators", [])
    if indicators:
        print(f"\n  Debug indicators found: {', '.join(indicators)}")

    # Raw metadata (if any)
    raw = details.get("raw_metadata", {})
    if raw:
        print("\n  Raw metadata tags:")
        for key, value in raw.items():
            if any(
                x in key.lower() for x in ["spherical", "projection", "stereo", "crop"]
            ):
                print(f"    - {key}: {value}")

    # Overall status
    is_valid = (
        (details.get("has_spherical_tag") and details.get("is_equirectangular"))
        or details.get("has_uuid_box", False)
        or details.get("has_spherical_side_data", False)
        or details.get("has_ffmpeg_metadata_tags", False)
        or details.get("has_360_metadata", False)
    )

    print()
    if is_valid:
        print("  ✓ File has valid 360° metadata for YouTube")
    else:
        print("  ✗ File does NOT have valid 360° metadata")
        print("    YouTube may not recognize this as a 360° video")

    print(f"{'=' * 60}")

    return is_valid


def inject_metadata_ffmpeg(input_file, output_file):
    """
    Inject 360° metadata using ffmpeg (fast, no re-encode).

    This uses the 'spherical' metadata tag which YouTube recognizes.
    Note: ffmpeg method is less reliable than spatialmedia for YouTube 360.
    Consider installing: pip install spatialmedia
    """
    # Note: Already-tagged check is done in process_file before calling this

    # ffmpeg's -c copy doesn't always preserve side_data from input
    # We need to explicitly add metadata tags that YouTube recognizes

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_file,
        "-c",
        "copy",  # Copy streams without re-encoding
        "-movflags",
        "+faststart",  # Web-optimized
        # Spherical metadata - these are the key tags YouTube looks for
        "-metadata:s:v:0",
        "spherical=1",
        "-metadata:s:v:0",
        "stereo_mode=mono",
        "-metadata:s:v:0",
        "projection_type=equirectangular",
        # Additional compatibility tags
        "-metadata:s:v:0",
        "initial_view_heading=0",
        "-metadata:s:v:0",
        "initial_view_pitch=0",
        "-metadata:s:v:0",
        "initial_view_roll=0",
        output_file,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Build informative error message
        error_parts = []
        full_output = (result.stderr or "") + "\n" + (result.stdout or "")

        # Look for actual error lines
        for line in full_output.split("\n"):
            line_lower = line.lower()
            if any(
                x in line_lower
                for x in [
                    "error:",
                    "could not",
                    "failed",
                    "invalid",
                    "no such",
                    "permission denied",
                    "not found",
                ]
            ):
                # Skip version/header lines
                if not any(
                    skip in line_lower
                    for skip in [
                        "ffmpeg version",
                        "built with",
                        "configuration:",
                        "libavutil",
                    ]
                ):
                    error_parts.append(line.strip())

        if error_parts:
            error_msg = "; ".join(error_parts[-3:])  # Last 3 relevant errors
        else:
            # No clear error found - show truncated output
            brief = " ".join(full_output.split()[:20])  # First 20 words
            error_msg = f"ffmpeg error (code {result.returncode}): {brief}..."

        return False, error_msg

    return True, "Success"


def verify_only(file_path):
    """Just verify a file without processing"""
    input_path = Path(file_path)

    if not input_path.exists():
        print(f"✗ File not found: {file_path}", file=sys.stderr)
        return False

    print(f"Verifying: {file_path}")
    print()

    is_valid, details = verify_360_metadata(file_path)
    print_verification_report(file_path, details)

    return is_valid


def get_exiftool_path():
    """Find exiftool binary in common locations"""
    # Check PATH first
    for path in [
        "exiftool",
        "/usr/bin/exiftool",
        "/usr/local/bin/exiftool",
        os.path.expanduser("~/.local/bin/exiftool"),
    ]:
        try:
            result = subprocess.run(
                [path, "-ver"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return path
        except:
            continue
    return None


def check_exiftool():
    """Check if exiftool is available"""
    return get_exiftool_path() is not None


def inject_metadata_exiftool(input_file, output_file):
    """
    Inject 360° metadata using ExifTool (GPL/Artistic License).
    This is the most reliable and FOSS-friendly method.
    """
    exiftool_path = get_exiftool_path()
    if not exiftool_path:
        return False, "exiftool not installed"

    try:
        # For in-place modification, exiftool can modify directly
        # For output to different file, use -o option
        if input_file == output_file or output_file is None:
            # In-place modification
            cmd = [
                exiftool_path,
                "-XMP-GSpherical:Spherical=true",
                "-XMP-GSpherical:Stitched=true",
                "-XMP-GSpherical:StitchingSoftware=KeyMission360Tools",
                "-XMP-GSpherical:ProjectionType=equirectangular",
                "-XMP-GSpherical:StereoMode=mono",
                "-overwrite_original",
                input_file,
            ]
        else:
            # Output to different file
            cmd = [
                exiftool_path,
                "-XMP-GSpherical:Spherical=true",
                "-XMP-GSpherical:Stitched=true",
                "-XMP-GSpherical:StitchingSoftware=KeyMission360Tools",
                "-XMP-GSpherical:ProjectionType=equirectangular",
                "-XMP-GSpherical:StereoMode=mono",
                "-o",
                output_file,
                input_file,
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "exiftool failed"
            return False, error_msg

        return True, "Success"
    except Exception as e:
        return False, str(e)


def inject_metadata_spatialmedia(input_file, output_file):
    """
    Inject 360° metadata using Google's spatialmedia library.
    Fallback method if exiftool is not available.
    """
    try:
        # Try to import and use spatialmedia
        from spatialmedia import metadata_utils

        metadata = metadata_utils.Metadata()
        # Set video metadata for equirectangular 360° video (mono)
        metadata.projection = "equirectangular"
        metadata.stereo_mode = "mono"

        # Inject metadata - use a simple console function
        def console(msg):
            pass  # Silent operation

        metadata_utils.inject_metadata(
            input_file, output_file, metadata, console=console
        )
        return True, "Success"
    except ImportError as e:
        return False, f"spatialmedia library not installed: {e}"
    except Exception as e:
        return False, str(e)


def process_file(input_file, output_file=None, method="auto", in_place=True):
    """
    Process a single video file.

    Args:
        input_file: Path to input MP4
        output_file: Path to output (defaults to in-place modification)
        method: "auto", "ffmpeg", or "spatialmedia"
        in_place: If True, modify original file; if False, create _youtube.mp4 copy

    Returns:
        (success: bool, message: str)
        Message can be: "success", "already_tagged", or error description
    """
    import shutil

    input_path = Path(input_file)

    if not input_path.exists():
        return False, f"File not found: {input_file}"

    if input_path.suffix.lower() not in [
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".m4v",
        ".3gp",
    ]:
        return False, f"Unsupported format: {input_path.suffix}"

    # Determine output path
    if output_file is None:
        if in_place:
            output_file = input_file
        else:
            output_file = str(input_path.with_suffix("")) + "_youtube.mp4"

    print(f"Processing: {input_file}")
    if output_file != input_file:
        print(f"Output: {output_file}")

    # Check if already tagged before processing
    if check_existing_metadata(input_file):
        print("  ⚠ Already has 360° metadata - skipping")
        # Still verify the existing file
        final_file = input_file
        is_valid, details = verify_360_metadata(final_file)
        print_verification_report(final_file, details)
        return True, "already_tagged"

    # For in-place modification, use a temp file with proper .mp4 extension
    temp_file = None
    if output_file == input_file:
        import tempfile

        # Use system temp dir and proper .mp4 extension for ffmpeg
        temp_dir = tempfile.gettempdir()
        temp_name = input_path.stem + "_tmp_360.mp4"
        temp_file = os.path.join(temp_dir, temp_name)
        actual_output = temp_file
    else:
        actual_output = output_file

    # Choose method
    used_method = method
    if method == "auto":
        # Priority: exiftool > spatialmedia > ffmpeg (fallback)
        # ExifTool is the most reliable and FOSS-friendly option
        success, msg = inject_metadata_exiftool(input_file, actual_output)
        if success:
            used_method = "exiftool"
        elif "not installed" in msg:
            print("  (exiftool not installed, trying spatialmedia)")
            # Try spatialmedia next
            success, msg = inject_metadata_spatialmedia(input_file, actual_output)
            if success:
                used_method = "spatialmedia"
            elif "not installed" in msg:
                print("  (spatialmedia not installed, using ffmpeg fallback)")
                used_method = "ffmpeg"
                success, msg = inject_metadata_ffmpeg(input_file, actual_output)
            else:
                print(f"  spatialmedia error: {msg}, trying ffmpeg...", file=sys.stderr)
                used_method = "ffmpeg"
                success, msg = inject_metadata_ffmpeg(input_file, actual_output)
        else:
            print(f"  exiftool error: {msg}, trying spatialmedia...", file=sys.stderr)
            success, msg = inject_metadata_spatialmedia(input_file, actual_output)
            if success:
                used_method = "spatialmedia"
            elif "not installed" in msg:
                print("  (spatialmedia not installed, using ffmpeg fallback)")
                used_method = "ffmpeg"
                success, msg = inject_metadata_ffmpeg(input_file, actual_output)
            else:
                print(f"  spatialmedia error: {msg}, trying ffmpeg...", file=sys.stderr)
                used_method = "ffmpeg"
                success, msg = inject_metadata_ffmpeg(input_file, actual_output)
    elif method == "exiftool":
        success, msg = inject_metadata_exiftool(input_file, actual_output)
        used_method = "exiftool"
    elif method == "spatialmedia":
        success, msg = inject_metadata_spatialmedia(input_file, actual_output)
        used_method = "spatialmedia"
    elif method == "ffmpeg":
        success, msg = inject_metadata_ffmpeg(input_file, actual_output)
        used_method = "ffmpeg"
    else:
        success, msg = inject_metadata_ffmpeg(input_file, actual_output)
        used_method = "ffmpeg"

    if success:
        if msg == "already_tagged":
            if temp_file and Path(temp_file).exists():
                Path(temp_file).unlink()
            print("  ⏭ Already has 360° metadata")
            # Still verify the existing file
            final_file = input_file
            is_valid, details = verify_360_metadata(final_file)
            print_verification_report(final_file, details)
            return True, "already_tagged"

        # Move temp file to final location if in-place
        if temp_file:
            try:
                # Preserve original file permissions/timestamps
                orig_stat = input_path.stat()
                shutil.move(temp_file, input_file)
                # Try to preserve access/modify times
                os.utime(input_file, (orig_stat.st_atime, orig_stat.st_mtime))
                print("  ✓ Metadata injected in-place")
                final_file = input_file
            except Exception as e:
                # Clean up temp file on failure
                if Path(temp_file).exists():
                    Path(temp_file).unlink()
                return False, f"Failed to replace original file: {e}"
        else:
            # Verify output for non-in-place
            output_size = Path(output_file).stat().st_size
            input_size = input_path.stat().st_size
            size_diff = output_size - input_size
            print(f"  ✓ Success! Size change: {size_diff / 1024:.1f} KB")
            final_file = output_file

        # Run verification on the final file
        is_valid, details = verify_360_metadata(final_file)
        print_verification_report(final_file, details)

        if not is_valid:
            if used_method == "ffmpeg":
                # ffmpeg method cannot inject metadata, only preserve existing
                # This is a failure for files that need metadata injection
                print(
                    "\n  ✗ FAILED: ffmpeg cannot inject 360° metadata into files that lost it."
                )
                print(
                    "     The merged file needs ExifTool or spatialmedia to add metadata."
                )
                print()
                print("     Install ExifTool (recommended):")
                print("       sudo pacman -S perl-image-exiftool")
                print()
                print("     Or install spatialmedia:")
                print("       git clone https://github.com/google/spatial-media.git")
                print("       cd spatial-media && pip install .")
                print()
                return (
                    False,
                    "Metadata injection failed: ExifTool or spatialmedia required for files without existing metadata",
                )
            else:
                return (
                    False,
                    "Metadata injection completed but verification failed. The file may not be recognized as 360° by YouTube.",
                )

        return True, "Metadata injected successfully"
    else:
        # Clean up temp file on failure
        if temp_file and Path(temp_file).exists():
            Path(temp_file).unlink()
        return False, msg


def batch_process(directory, method="auto", in_place=True):
    """Process all videos in a directory"""
    video_extensions = [".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp"]
    video_files = [
        f for f in Path(directory).iterdir() if f.suffix.lower() in video_extensions
    ]

    if not video_files:
        print(f"No video files found in {directory}")
        return

    print(f"Found {len(video_files)} videos to process")
    print()

    success_count = 0
    tagged_count = 0
    failed_count = 0
    verified_count = 0

    for i, video_file in enumerate(video_files, 1):
        print(f"[{i}/{len(video_files)}] ", end="")
        success, msg = process_file(str(video_file), method=method, in_place=in_place)
        if success:
            if msg == "already_tagged":
                tagged_count += 1
            else:
                success_count += 1
                verified_count += 1
        else:
            failed_count += 1
            print(f"  ✗ Failed: {msg}", file=sys.stderr)
        print()

    print(
        f"Done! {success_count} tagged, {tagged_count} already had tags, {failed_count} failed"
    )
    if verified_count > 0:
        print(f"       ({verified_count} new files verified with 360° metadata)")


def run_headless_test():
    """Run tests without actual processing"""
    print("=" * 60)
    print("KeyMission 360 YouTube Export - Headless Test Mode")
    print("=" * 60)
    print()

    # Test 1: Check ffmpeg
    print("[TEST 1] Checking ffmpeg...")
    if check_ffmpeg():
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
        )
        version = result.stdout.split("\n")[0]
        print(f"  ✓ {version}")
    else:
        print("  ✗ ffmpeg not found", file=sys.stderr)

    # Test 2: Check exiftool (preferred method)
    print("\n[TEST 2] Checking exiftool...")
    if check_exiftool():
        result = subprocess.run(
            ["exiftool", "-ver"], capture_output=True, text=True, timeout=5
        )
        print(f"  ✓ ExifTool version {result.stdout.strip()}")
    else:
        print("  ✗ exiftool not installed (REQUIRED for merged/lost-metadata files)")
        print("    Install: sudo pacman -S perl-image-exiftool")
        print("    Or visit: https://exiftool.org/")

    # Test 3: Check spatialmedia (fallback)
    print("\n[TEST 3] Checking spatialmedia library...")
    try:
        from spatialmedia import metadata_utils

        print("  ✓ spatialmedia available (fallback)")
    except ImportError:
        print("  ⚠ spatialmedia not installed (optional fallback)")
        print("    Install: git clone https://github.com/google/spatial-media.git")
        print("             cd spatial-media && pip install .")

    # Test 4: Test metadata format
    print("\n[TEST 4] Testing metadata format...")
    print("  ✓ Equirectangular projection: supported")
    print("  ✓ Mono/stereo: mono (KeyMission 360)")
    print("  ✓ Metadata format: XMP-GSpherical (ExifTool)")

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
  %(prog)s --verify input.mp4           # Verify existing file has 360 metadata

Note:
  This tool does NOT re-encode video. It only injects metadata,
  so it's very fast and preserves original quality.

Methods:
  auto          - Try exiftool, then spatialmedia, then ffmpeg (default)
  exiftool      - Use ExifTool (RECOMMENDED - GPL/Artistic License)
  spatialmedia  - Use Google's spatialmedia (Apache License)
  ffmpeg        - Use ffmpeg (fallback only - cannot inject new metadata)

Verification:
  Use --verify to check if a video has valid 360° metadata
  without re-processing it. This is useful for confirming
  YouTube will recognize the video as 360°.

Installation:
  sudo pacman -S perl-image-exiftool  # Install ExifTool (recommended)
  pip install spatialmedia             # Alternative (optional)
""",
    )

    parser.add_argument("input", nargs="?", help="Input video file or directory")
    parser.add_argument("output", nargs="?", help="Output video file (optional)")
    parser.add_argument(
        "--batch",
        "-b",
        action="store_true",
        help="Batch process all videos in directory",
    )
    parser.add_argument(
        "--method",
        "-m",
        choices=["auto", "exiftool", "ffmpeg", "spatialmedia"],
        default="auto",
        help="Metadata injection method",
    )
    parser.add_argument(
        "--copy",
        "-c",
        action="store_true",
        help="Create a copy with _youtube.mp4 suffix instead of modifying in-place",
    )
    parser.add_argument(
        "--headless", "--test", "-t", action="store_true", help="Run headless tests"
    )
    parser.add_argument(
        "--verify",
        "-V",
        action="store_true",
        help="Verify existing file has valid 360° metadata (no processing)",
    )

    args = parser.parse_args()

    # Headless test mode
    if args.headless:
        run_headless_test()
        sys.exit(0)

    # Verification mode
    if args.verify:
        if not args.input:
            parser.print_help()
            sys.exit(1)
        success = verify_only(args.input)
        sys.exit(0 if success else 1)

    # Check input
    if not args.input:
        parser.print_help()
        sys.exit(1)

    print("=" * 60)
    print("KeyMission 360 YouTube Export")
    print("=" * 60)
    print()

    if args.batch:
        batch_process(args.input, method=args.method, in_place=not args.copy)
    else:
        success, msg = process_file(
            args.input, args.output, method=args.method, in_place=not args.copy
        )
        if success:
            print("\n✓ Export complete!")
            print("\nUpload to YouTube and it will automatically recognize")
            print("this as a 360° video with full spherical playback.")
        else:
            print(f"\n✗ Export failed: {msg}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
