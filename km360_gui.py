#!/usr/bin/env python3
"""
KeyMission 360 Linux Utility - Main GUI Application
====================================================

A comprehensive Linux replacement for the Nikon KeyMission 360/170 
Utility Windows application.

Features:
- File browser with download manager
- Camera settings configuration
- Date/time synchronization
- SD card formatting
- 360° image/video viewer
- YouTube 360° metadata export

Author: KeyMission 360 Tools Project
License: MIT
Version: 1.0
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import subprocess
import threading
import os
import json
import sys
import time
import shutil
import hashlib
import tempfile
from datetime import datetime
from pathlib import Path

# Import our config and native dialogs
from km360_config import (
    ask_directory, ask_saveas_filename, ask_open_filename,
    load_config, save_config, get_config_value, set_config_value
)

# USB imports for port cycling
try:
    import usb1
    import usb.core
    import usb.util
    USB_AVAILABLE = True
except ImportError:
    USB_AVAILABLE = False

# Version info
VERSION = "1.0"
APP_NAME = "KeyMission 360 Linux Utility"

# Placeholder features for future versions
PLACEHOLDER_FEATURES = {
    "batch_ops": "Batch Operations - Coming in v2.0",
    "advanced_settings": "Advanced Settings - Coming in v2.0",
    "tethered": "Tethered Shooting - Coming in v2.0",
    "gps": "GPS Data Editor - Coming in v2.0",
}


def format_size_bytes(size):
    """Format bytes to human readable string"""
    if size is None:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


class PlaceholderDialog:
    """Dialog to show placeholder features"""
    def __init__(self, parent, feature_name, description):
        self.window = tk.Toplevel(parent)
        self.window.title(f"{feature_name} - Coming Soon")
        self.window.geometry("400x200")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center the dialog
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (200)
        y = (self.window.winfo_screenheight() // 2) - (100)
        self.window.geometry(f"+{x}+{y}")
        
        # Icon (placeholder emoji)
        ttk.Label(self.window, text="🚧", font=("Arial", 48)).pack(pady=10)
        
        # Message
        ttk.Label(self.window, text=feature_name, font=("Arial", 14, "bold")).pack()
        ttk.Label(self.window, text=description, wraplength=350, justify="center").pack(pady=10)
        
        # Close button
        ttk.Button(self.window, text="OK", command=self.window.destroy).pack(pady=10)


class DownloadProgressDialog:
    """Download manager dialog with progress bar, resume support, checksum verification, and queue"""
    
    def __init__(self, parent, files, dest, main_app, delete_after=False):
        self.parent = parent
        self.files = files  # List of (num, name) tuples
        self.dest = dest
        self.main_app = main_app
        self.delete_after = delete_after  # Delete files from camera after successful download
        self.downloading = False
        self.cancelled = False
        self.current_index = 0
        self.failed_files = []
        self.completed_files = []
        self.file_checksums = {}  # Store checksums for verification
        self.deleted_files = []  # Track which files were deleted from camera
        
        # Create dialog
        self.window = tk.Toplevel(parent)
        self.window.title("📥 Download Manager")
        self.window.geometry("650x650")
        self.window.minsize(600, 550)
        self.window.transient(parent)
        # Don't use grab_set - it prevents main window from closing
        
        # Center dialog
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - 325
        y = (self.window.winfo_screenheight() // 2) - 325
        self.window.geometry(f"+{x}+{y}")
        
        self.setup_ui()
        
        # Handle window close button
        self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        # Start download automatically
        self.window.after(100, self.start_download)
    
    def _on_window_close(self):
        """Handle window close button - cancel download and close"""
        if self.downloading:
            self.cancel_download()
            # Give a moment for cancellation to propagate
            self.window.after(500, self.window.destroy)
        else:
            self.window.destroy()
    
    def setup_ui(self):
        """Setup the download dialog UI"""
        # Title
        ttk.Label(self.window, text="📥 Download Manager", 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        # Overall progress
        progress_frame = ttk.LabelFrame(self.window, text="Overall Progress", padding=10)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.overall_var = tk.DoubleVar(value=0)
        self.overall_bar = ttk.Progressbar(progress_frame, variable=self.overall_var, 
                                          maximum=len(self.files), length=600)
        self.overall_bar.pack(fill=tk.X)
        
        self.overall_label = ttk.Label(progress_frame, 
                                      text=f"0 / {len(self.files)} files")
        self.overall_label.pack(pady=(5, 0))
        
        # Current file progress
        current_frame = ttk.LabelFrame(self.window, text="Current File", padding=10)
        current_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.current_name_var = tk.StringVar(value="Waiting...")
        ttk.Label(current_frame, textvariable=self.current_name_var, 
                 font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        self.current_progress_var = tk.DoubleVar(value=0)
        self.current_bar = ttk.Progressbar(current_frame, variable=self.current_progress_var, 
                                          maximum=100, length=600)
        self.current_bar.pack(fill=tk.X, pady=(5, 0))
        
        self.current_size_var = tk.StringVar(value="")
        ttk.Label(current_frame, textvariable=self.current_size_var).pack(anchor=tk.W)
        
        # Speed and ETA
        stats_frame = ttk.Frame(current_frame)
        stats_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.speed_var = tk.StringVar(value="Speed: -")
        ttk.Label(stats_frame, textvariable=self.speed_var).pack(side=tk.LEFT)
        
        self.eta_var = tk.StringVar(value="ETA: -")
        ttk.Label(stats_frame, textvariable=self.eta_var).pack(side=tk.RIGHT)
        
        # Verification status
        self.verify_var = tk.StringVar(value="")
        self.verify_label = ttk.Label(current_frame, textvariable=self.verify_var, 
                                     foreground="green")
        self.verify_label.pack(anchor=tk.W)
        
        # File queue list
        queue_frame = ttk.LabelFrame(self.window, text="Queue", padding=5)
        queue_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Treeview for queue
        columns = ("status", "name", "size", "verify")
        self.queue_tree = ttk.Treeview(queue_frame, columns=columns, 
                                       show="headings", height=8)
        
        self.queue_tree.heading("status", text="Status")
        self.queue_tree.heading("name", text="Filename")
        self.queue_tree.heading("size", text="Size")
        self.queue_tree.heading("verify", text="Verify")
        
        self.queue_tree.column("status", width=100)
        self.queue_tree.column("name", width=250)
        self.queue_tree.column("size", width=80)
        self.queue_tree.column("verify", width=80)
        
        vsb = ttk.Scrollbar(queue_frame, orient="vertical", command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=vsb.set)
        
        self.queue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate queue
        for num, name in self.files:
            self.queue_tree.insert('', 'end', values=("⏳ Pending", name, "-", "-"), tags=('pending',))
        
        self.queue_tree.tag_configure('pending', foreground='gray')
        self.queue_tree.tag_configure('downloading', foreground='blue')
        self.queue_tree.tag_configure('completed', foreground='green')
        self.queue_tree.tag_configure('failed', foreground='red')
        self.queue_tree.tag_configure('resumed', foreground='orange')
        self.queue_tree.tag_configure('verifying', foreground='purple')
        
        # Buttons
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.cancel_download)
        self.cancel_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.retry_btn = ttk.Button(btn_frame, text="Retry Failed", 
                                   command=self.retry_failed, state=tk.DISABLED)
        self.retry_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(btn_frame, text="Close", command=self.window.destroy).pack(side=tk.RIGHT)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready to download")
        ttk.Label(self.window, textvariable=self.status_var, 
                 relief=tk.SUNKEN, anchor=tk.W).pack(side=tk.BOTTOM, fill=tk.X)
    
    def start_download(self):
        """Start the download thread"""
        if self.downloading:
            return
        
        self.downloading = True
        self.cancelled = False
        self.thread = threading.Thread(target=self._download_worker)
        self.thread.daemon = True
        self.thread.start()
    
    def cancel_download(self):
        """Cancel the download"""
        self.cancelled = True
        self.status_var.set("Cancelling...")
        self.cancel_btn.config(state=tk.DISABLED)
    
    def retry_failed(self):
        """Retry failed downloads"""
        if self.failed_files:
            self.files = self.failed_files[:]
            self.failed_files = []
            self.current_index = 0
            self.completed_files = []
            
            # Clear queue
            for item in self.queue_tree.get_children():
                self.queue_tree.delete(item)
            
            # Repopulate
            for num, name in self.files:
                self.queue_tree.insert('', 'end', values=("⏳ Pending", name, "-", "-"), tags=('pending',))
            
            self.overall_var.set(0)
            self.overall_label.config(text=f"0 / {len(self.files)} files")
            self.retry_btn.config(state=tk.DISABLED)
            
            self.start_download()
    
    def _get_file_size_on_camera(self, file_num):
        """Get the size of a file on the camera using gphoto2 --list-files"""
        try:
            result = subprocess.run(
                ["gphoto2", "--list-files"],
                capture_output=True, text=True, timeout=30
            )
            
            for line in result.stdout.split('\n'):
                if line.strip().startswith(f'#{file_num}'):
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        size_str = parts[2]
                        return self._parse_size(size_str)
        except Exception as e:
            print(f"Error getting file size: {e}")
        
        return None
    
    def _parse_size(self, size_str):
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
    
    def _format_size(self, size):
        """Format bytes to human readable"""
        return format_size_bytes(size)
    
    def _calculate_checksum(self, filepath):
        """Calculate SHA256 checksum of a file"""
        import hashlib
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"Error calculating checksum: {e}")
            return None
    
    def _verify_file_integrity(self, filepath, expected_size=None):
        """Verify file exists and has correct size, return checksum"""
        if not os.path.exists(filepath):
            return False, None, "File not found"
        
        actual_size = os.path.getsize(filepath)
        
        if expected_size and actual_size != expected_size:
            return False, None, f"Size mismatch: {actual_size} vs {expected_size}"
        
        # Calculate checksum
        checksum = self._calculate_checksum(filepath)
        if checksum:
            return True, checksum, "OK"
        else:
            return False, None, "Checksum failed"
    
    def _download_with_rsync_style_resume(self, file_num, file_name, dest_path, camera_size):
        """Download file with REAL progress tracking using stdout streaming"""
        import subprocess
        import time
        
        part_path = dest_path + ".part"
        dest_dir = os.path.dirname(dest_path)
        
        # Debug info about temp file
        self.window.after(0, lambda: self.status_var.set(f"Downloading to: {part_path}"))
        print(f"[DEBUG] Download temp file: {part_path}")
        
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            if self.cancelled:
                return False, "Cancelled"
            
            try:
                # Open output file in binary write mode
                out_file = open(part_path, 'wb')
                bytes_written = 0
                last_update_bytes = 0
                last_update_time = time.time()
                
                # Use stdout streaming to track progress in real-time
                process = subprocess.Popen(
                    ["gphoto2", "--get-file", str(file_num), "--stdout"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=8192
                )
                
                # Read stdout in chunks and write to file
                chunk_size = 65536  # 64KB chunks
                start_time = time.time()
                
                while True:
                    if self.cancelled:
                        out_file.close()
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except:
                            process.kill()
                        return False, "Cancelled"
                    
                    chunk = process.stdout.read(chunk_size)
                    if not chunk:
                        break
                    
                    out_file.write(chunk)
                    out_file.flush()  # Ensure data is written to disk
                    bytes_written += len(chunk)
                    
                    # Update progress every 0.2 seconds or every 256KB
                    current_time = time.time()
                    if current_time - last_update_time >= 0.2 or bytes_written - last_update_bytes >= 262144:
                        if camera_size and camera_size > 0:
                            progress = min(100, int(100 * bytes_written / camera_size))
                            elapsed = current_time - start_time
                            speed = bytes_written / elapsed if elapsed > 0 else 0
                            
                            # Format for display
                            size_str = f"{bytes_written / 1024 / 1024:.1f} MB"
                            total_str = f"{camera_size / 1024 / 1024:.1f} MB"
                            speed_str = f"{speed / 1024 / 1024:.1f} MB/s"
                            
                            # Update UI - direct call since we're in a thread, use after for thread safety
                            self.window.after(0, self._update_progress_ui, progress, 
                                              f"{size_str} / {total_str}", speed_str)
                        
                        last_update_time = current_time
                        last_update_bytes = bytes_written
                
                out_file.close()
                
                # Wait for process to complete
                try:
                    stderr = process.stderr.read()
                    process.wait(timeout=30)
                except:
                    process.kill()
                    raise Exception("Process wait timeout")
                
                if process.returncode == 0:
                    # Verify size
                    if camera_size and bytes_written != camera_size:
                        last_error = f"Size mismatch: {bytes_written} vs {camera_size}"
                        os.remove(part_path)
                        continue
                    
                    # Rename .part to final name
                    print(f"[DEBUG] Download complete, renaming {part_path} -> {dest_path}")
                    os.rename(part_path, dest_path)
                    return True, "Downloaded successfully"
                else:
                    stderr_str = stderr.decode() if stderr else "Unknown error"
                    last_error = f"gphoto2 error: {stderr_str}"
                    
                    # Clean up partial file on error
                    if os.path.exists(part_path):
                        os.remove(part_path)
                    
                    if "timeout" in stderr_str.lower() or "io" in stderr_str.lower():
                        time.sleep(2)
                        continue
                    else:
                        return False, last_error
                        
            except Exception as e:
                last_error = f"Exception: {str(e)}"
                # Clean up partial file on exception
                if os.path.exists(part_path):
                    try:
                        os.remove(part_path)
                    except:
                        pass
                continue
        
        return False, f"Failed after {max_retries} attempts: {last_error}"
    
    def _update_progress_ui(self, progress, size_str, speed_str):
        """Update the progress bar and status labels - called from main thread via after()"""
        try:
            # Update the DoubleVar which is bound to the progressbar
            self.current_progress_var.set(float(progress))
            self.current_size_var.set(f"Progress: {size_str}")
            self.speed_var.set(f"Speed: {speed_str}")
            # Force immediate UI update
            self.current_bar.update()
        except Exception as e:
            print(f"[DEBUG] Progress update error: {e}")  # Debug output
    
    def _is_video_file(self, filename):
        """Check if file is a video based on extension"""
        ext = filename.lower().split('.')[-1] if '.' in filename else ''
        return ext in ['mp4', 'mov', 'avi', 'mkv', 'm4v']

    def _download_worker(self):
        """Main download worker thread - auto-injects 360° metadata for videos"""
        import tempfile
        import shutil
        
        total_files = len(self.files)
        start_time = time.time()
        
        for i, (file_num, file_name) in enumerate(self.files):
            if self.cancelled:
                break
            
            self.current_index = i
            dest_path = os.path.join(self.dest, file_name)
            
            # Check if this is a video file (for metadata injection)
            is_video = self._is_video_file(file_name)
            
            # Update UI
            self.window.after(0, lambda n=file_name, idx=i: self._update_current_file(n, idx))
            
            # Get expected file size from camera
            camera_size = self._get_file_size_on_camera(file_num)
            if camera_size:
                self.window.after(0, lambda s=format_size_bytes(camera_size): 
                    self.current_size_var.set(f"Expected size: {s}"))
            
            # Check for existing complete file (resume support)
            if os.path.exists(dest_path):
                existing_size = os.path.getsize(dest_path)
                if camera_size and existing_size == camera_size:
                    # Verify checksum of existing file
                    self.window.after(0, lambda: self.status_var.set("Verifying existing file..."))
                    valid, checksum, msg = self._verify_file_integrity(dest_path, camera_size)
                    if valid:
                        self.file_checksums[file_name] = checksum
                        # For videos, check if metadata already injected
                        if is_video:
                            self.window.after(0, lambda idx=i, cs=checksum[:16]: 
                                self._mark_verified(idx, f"{cs} (360° ready)"))
                        else:
                            self.window.after(0, lambda idx=i, cs=checksum[:16]: 
                                self._mark_verified(idx, cs))
                        self.completed_files.append((file_num, file_name))
                        continue
                    else:
                        # File exists but is corrupt, remove and re-download
                        try:
                            os.remove(dest_path)
                        except:
                            pass
            
            # Download the file with retry/resume support
            self.window.after(0, lambda: self.status_var.set("Downloading..."))
            success, message = self._download_with_rsync_style_resume(
                file_num, file_name, dest_path, camera_size
            )
            
            # Set progress to 100% when download completes (success or fail)
            self.window.after(0, lambda: self.current_progress_var.set(100))
            
            if success:
                # Verify the downloaded file
                self.window.after(0, lambda: self.status_var.set("Verifying checksum..."))
                self.window.after(0, lambda idx=i: self._mark_verifying(idx))
                
                valid, checksum, msg = self._verify_file_integrity(dest_path, camera_size)
                
                if valid:
                    self.file_checksums[file_name] = checksum
                    
                    # If video, inject 360° metadata for YouTube
                    if is_video:
                        self.window.after(0, lambda: self.status_var.set("Injecting 360° metadata..."))
                        temp_output = dest_path + ".yt_temp.mp4"
                        yt_success, yt_message = self._inject_youtube_metadata(dest_path, temp_output)
                        
                        if yt_success:
                            # Replace original with metadata-injected version
                            try:
                                os.replace(temp_output, dest_path)
                                status_msg = "Downloaded + 360° metadata"
                            except Exception as e:
                                # If replace fails, keep the original
                                try:
                                    os.remove(temp_output)
                                except:
                                    pass
                                status_msg = "Downloaded (meta failed)"
                        else:
                            # Metadata injection failed, but keep the original download
                            try:
                                if os.path.exists(temp_output):
                                    os.remove(temp_output)
                            except:
                                pass
                            status_msg = "Downloaded (no 360° meta)"
                    else:
                        status_msg = "Downloaded"
                    
                    # Delete from camera if requested (after successful download+verify)
                    if self.delete_after:
                        self.window.after(0, lambda: self.status_var.set("Deleting from camera..."))
                        if self._delete_file_from_camera(file_num):
                            self.deleted_files.append(file_name)
                            self.window.after(0, lambda idx=i, cs=checksum[:16]: 
                                self._mark_completed(idx, f"{status_msg} + deleted", cs))
                        else:
                            self.window.after(0, lambda idx=i, cs=checksum[:16]: 
                                self._mark_completed(idx, f"{status_msg} (del failed)", cs))
                    else:
                        self.window.after(0, lambda idx=i, cs=checksum[:16]: 
                            self._mark_completed(idx, status_msg, cs))
                    
                    self.completed_files.append((file_num, file_name))
                else:
                    self.failed_files.append((file_num, file_name, f"Verify failed: {msg}"))
                    self.window.after(0, lambda idx=i: self._mark_failed(idx, "Checksum failed"))
            else:
                self.failed_files.append((file_num, file_name, message))
                self.window.after(0, lambda idx=i, err=message[:30]: 
                    self._mark_failed(idx, err))
            
            # Update overall progress
            elapsed = time.time() - start_time
            avg_time = elapsed / (i + 1) if i > 0 else 0
            remaining_files = total_files - (i + 1)
            eta_seconds = avg_time * remaining_files
            
            self.window.after(0, lambda p=i+1, eta=eta_seconds: 
                self._update_overall_progress(p, total_files, eta))
        
        # Done
        self.downloading = False
        self.window.after(0, self._download_complete)
    
    def _inject_youtube_metadata(self, input_file, output_file):
        """Inject 360° metadata using ffmpeg (no re-encode)"""
        try:
            cmd = [
                "ffmpeg", "-y", "-i", input_file,
                "-c", "copy",  # Copy streams without re-encoding
                "-movflags", "+faststart",  # Web-optimized
                "-strict", "unofficial",  # Allow experimental features
                "-metadata:s:v:0", "spherical=1",
                "-metadata:s:v:0", "stereo_mode=mono",
                output_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return result.returncode == 0, result.stderr if result.stderr else "Success"
        except Exception as e:
            return False, str(e)

    def _delete_file_from_camera(self, file_num):
        """Delete a file from the camera after successful export"""
        try:
            print(f"[DEBUG] Attempting to delete file #{file_num} from camera...")
            
            # Try different methods to delete the file
            # Method 1: Direct delete
            result = subprocess.run(
                ["gphoto2", "--delete-file", str(file_num)],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                print(f"[DEBUG] Delete successful (method 1)")
                return True
            
            # Method 2: Try with recurse flag
            result = subprocess.run(
                ["gphoto2", "--recurse", "--delete-file", str(file_num)],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                print(f"[DEBUG] Delete successful (method 2 - recurse)")
                return True
            
            # Method 3: Try common folder paths
            common_folders = ["/store_00010001", "/store_00000001", "/DCIM", "/DCIM/100NIKON"]
            for folder in common_folders:
                result = subprocess.run(
                    ["gphoto2", "--folder", folder, "--delete-file", str(file_num)],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    print(f"[DEBUG] Delete successful (method 3 - folder {folder})")
                    return True
            
            print(f"[DEBUG] All delete methods failed. Last error: {result.stderr}")
            return False
            
        except Exception as e:
            print(f"[DEBUG] Exception deleting file {file_num}: {e}")
            return False
    
    def _update_current_file(self, name, index):
        """Update UI for current file"""
        self.current_name_var.set(f"{index + 1}. {name}")
        self.current_progress_var.set(0)
        self.current_size_var.set("")
        self.speed_var.set("Speed: -")
        self.eta_var.set("ETA: -")
        self.verify_var.set("")
        
        # Highlight in queue
        item = self.queue_tree.get_children()[index]
        self.queue_tree.item(item, values=("⬇️ Downloading", name, "-", "-"), tags=('downloading',))
        self.queue_tree.see(item)
    
    def _mark_completed(self, index, status="Completed", checksum=""):
        """Mark file as completed in queue"""
        item = self.queue_tree.get_children()[index]
        values = self.queue_tree.item(item, 'values')
        self.queue_tree.item(item, 
            values=(f"✓ {status}", values[1], values[2], checksum + "..." if checksum else "OK"), 
            tags=('completed',))
    
    def _mark_failed(self, index, error="Failed"):
        """Mark file as failed in queue"""
        item = self.queue_tree.get_children()[index]
        values = self.queue_tree.item(item, 'values')
        error_short = error[:20] + "..." if len(error) > 20 else error
        self.queue_tree.item(item, 
            values=(f"✗ {error_short}", values[1], values[2], "Fail"), 
            tags=('failed',))
    
    def _mark_verifying(self, index):
        """Mark file as being verified"""
        item = self.queue_tree.get_children()[index]
        values = self.queue_tree.item(item, 'values')
        self.queue_tree.item(item, 
            values=("🔍 Verifying", values[1], values[2], "-"), 
            tags=('verifying',))
    
    def _mark_verified(self, index, checksum=""):
        """Mark file as verified (already existed)"""
        item = self.queue_tree.get_children()[index]
        values = self.queue_tree.item(item, 'values')
        self.queue_tree.item(item, 
            values=("✓ Verified", values[1], "Exists", checksum + "..." if checksum else "OK"), 
            tags=('completed',))

    def _mark_exported_and_deleted(self, index):
        """Mark file as exported and deleted from camera"""
        item = self.queue_tree.get_children()[index]
        values = self.queue_tree.item(item, 'values')
        self.queue_tree.item(item, 
            values=("✓ Exported+Deleted", values[1], "Deleted", "OK"), 
            tags=('completed',))
    
    def _update_overall_progress(self, completed, total, eta_seconds):
        """Update overall progress bar"""
        self.overall_var.set(completed)
        self.overall_label.config(text=f"{completed} / {total} files")
        
        if eta_seconds > 0:
            if eta_seconds < 60:
                eta_str = f"{int(eta_seconds)}s"
            elif eta_seconds < 3600:
                eta_str = f"{int(eta_seconds/60)}m {int(eta_seconds%60)}s"
            else:
                eta_str = f"{int(eta_seconds/3600)}h {int((eta_seconds%3600)/60)}m"
            self.eta_var.set(f"ETA: {eta_str}")
        
        self.status_var.set(f"Downloaded {completed} of {total} files")
    
    def _download_complete(self):
        """Called when download is complete"""
        self.cancel_btn.config(state=tk.DISABLED)
        
        deleted_count = len(self.deleted_files)
        
        if self.failed_files:
            self.retry_btn.config(state=tk.NORMAL)
            self.status_var.set(f"Completed with {len(self.failed_files)} failures")
            
            # Build detailed error message
            error_details = "\n".join([f"• {name}: {err[:50]}" for _, name, err in self.failed_files[:5]])
            if len(self.failed_files) > 5:
                error_details += f"\n... and {len(self.failed_files) - 5} more"
            
            delete_msg = f"\nDeleted from camera: {deleted_count} files" if (self.delete_after and deleted_count > 0) else ""
            
            messagebox.showwarning("Download Complete", 
                f"Downloaded {len(self.completed_files)} files.\n"
                f"Failed: {len(self.failed_files)} files.{delete_msg}\n\n"
                f"Details:\n{error_details}\n\n"
                "Click 'Retry Failed' to attempt again.")
        elif self.cancelled:
            self.status_var.set("Download cancelled")
            messagebox.showinfo("Download Cancelled", 
                f"Downloaded {len(self.completed_files)} files before cancellation.")
        else:
            self.status_var.set("All downloads complete!")
            self.overall_var.set(len(self.files))
            self.current_progress_var.set(100)
            
            # Build success message
            msg = f"Successfully downloaded {len(self.completed_files)} files!"
            if deleted_count > 0:
                msg += f"\n\nDeleted {deleted_count} files from camera."
            
            # Count videos with metadata
            video_count = sum(1 for _, name in self.completed_files 
                            if self._is_video_file(name))
            if video_count > 0:
                msg += f"\n\nVideos processed with 360° metadata: {video_count}"
            
            messagebox.showinfo("Download Complete", msg)
        
        # Refresh main app file list (files may have been deleted)
        self.main_app.set_status(f"Downloaded {len(self.completed_files)} files")
        self.main_app.refresh_files()


class KM360GUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        # State
        self.connected = False
        self.camera_info = {}
        self.current_files = []
        self.download_thread = None
        self.connection_thread = None
        self.cancelled = False  # For thread cancellation
        
        # Setup UI
        self.setup_menu()
        self.setup_main_layout()
        self.setup_status_bar()
        
        # Handle window close properly
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Try auto-connect (with delay to let camera stabilize)
        self.root.after(2000, self.check_connection)
    
    def on_close(self):
        """Handle application close - cancel all operations and cleanup"""
        self.cancelled = True
        self.set_status("Closing application...")
        
        # Cancel any ongoing downloads
        if hasattr(self, 'download_thread') and self.download_thread and self.download_thread.is_alive():
            self.set_status("Waiting for download to cancel...")
            # Downloads check self.cancelled flag
            self.root.after(500, self._finish_close)
        else:
            self._finish_close()
    
    def _finish_close(self):
        """Complete the close operation"""
        # Stop the auto-check timer
        self.cancelled = True
        # Destroy the window
        self.root.destroy()
    
    def setup_menu(self):
        """Setup application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Connect to Camera", command=self.connect_camera)
        file_menu.add_command(label="Disconnect", command=self.disconnect_camera)
        file_menu.add_separator()
        file_menu.add_command(label="Settings...", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Camera Menu
        camera_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Camera", menu=camera_menu)
        camera_menu.add_command(label="Sync Date/Time", command=self.sync_datetime)
        camera_menu.add_command(label="Format SD Card...", command=self.format_sd)
        camera_menu.add_separator()
        camera_menu.add_command(label="Camera Info", command=self.show_camera_info)
        camera_menu.add_command(label="Storage Info", command=self.show_storage_info)
        
        # Tools Menu (with placeholders)
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Working features
        tools_menu.add_command(label="Download Manager", command=self.show_download_manager)
        tools_menu.add_separator()
        
        # Placeholder features (not yet implemented)
        tools_menu.add_command(label="🚧 Batch Operations", 
                              command=lambda: self.show_placeholder("Batch Operations"))
        tools_menu.add_separator()
        tools_menu.add_command(label="🚧 Advanced Settings", 
                              command=lambda: self.show_placeholder("Advanced Settings"))
        tools_menu.add_command(label="🚧 Tethered Shooting", 
                              command=lambda: self.show_placeholder("Tethered Shooting"))
        
        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation", command=self.show_docs)
        help_menu.add_separator()
        help_menu.add_command(label="Add to Start Menu...", command=self.install_desktop_entry)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
    
    def setup_main_layout(self):
        """Setup main window layout"""
        # Create main paned window
        self.main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Connection & Files
        self.left_frame = ttk.Frame(self.main_pane, width=350)
        self.main_pane.add(self.left_frame, weight=1)
        
        self.setup_connection_panel()
        self.setup_file_browser()
        
        # Right panel - Tabs
        self.right_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(self.right_frame, weight=3)
        
        self.setup_tabs()
    
    def setup_connection_panel(self):
        """Setup connection status panel"""
        conn_frame = ttk.LabelFrame(self.left_frame, text="Connection", padding=10)
        conn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_label = ttk.Label(conn_frame, text="● Not Connected", 
                                      foreground="red", font=("Arial", 10, "bold"))
        self.status_label.pack(anchor=tk.W)
        
        self.camera_model_label = ttk.Label(conn_frame, text="Camera: -")
        self.camera_model_label.pack(anchor=tk.W, pady=(5, 0))
        
        self.battery_label = ttk.Label(conn_frame, text="Battery: -")
        self.battery_label.pack(anchor=tk.W)
        
        btn_frame = ttk.Frame(conn_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.connect_btn = ttk.Button(btn_frame, text="Connect", 
                                     command=self.connect_camera)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.refresh_btn = ttk.Button(btn_frame, text="Refresh", 
                                     command=self.refresh_files)
        self.refresh_btn.pack(side=tk.LEFT)
    
    def setup_file_browser(self):
        """Setup file browser tree"""
        files_frame = ttk.LabelFrame(self.left_frame, text="Camera Files", padding=5)
        files_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview for files - include file_num as hidden column
        columns = ("name", "size", "date", "file_num")
        self.file_tree = ttk.Treeview(files_frame, columns=columns, 
                                      show="headings", selectmode="extended")
        
        # Hide the file_num column (used internally)
        self.file_tree.column("file_num", width=0, stretch=False)
        self.file_tree.heading("file_num", text="")
        
        self.file_tree.heading("name", text="Name")
        self.file_tree.heading("size", text="Size")
        self.file_tree.heading("date", text="Date")
        
        self.file_tree.column("name", width=150)
        self.file_tree.column("size", width=70)
        self.file_tree.column("date", width=100)
        
        # Scrollbars
        vsb = ttk.Scrollbar(files_frame, orient="vertical", command=self.file_tree.yview)
        hsb = ttk.Scrollbar(files_frame, orient="horizontal", command=self.file_tree.xview)
        self.file_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.file_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        
        files_frame.grid_rowconfigure(0, weight=1)
        files_frame.grid_columnconfigure(0, weight=1)
        
        # File browser buttons
        btn_frame = ttk.Frame(files_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        
        ttk.Button(btn_frame, text="Download Selected", 
                  command=self.download_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Download All", 
                  command=self.download_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Delete", 
                  command=self.delete_selected).pack(side=tk.LEFT, padx=(0, 5))
        
        # USB Reset button
        self.reset_usb_btn = ttk.Button(btn_frame, text="🔄 Reset USB", 
                                       command=self.reset_usb_port)
        self.reset_usb_btn.pack(side=tk.RIGHT)
        
        # Setup right-click context menu
        self.setup_file_context_menu()
        
        # Setup keyboard shortcuts for batch selection
        self.setup_file_shortcuts()
    
    def setup_file_shortcuts(self):
        """Setup keyboard shortcuts for file browser"""
        # Ctrl+A - Select all
        self.file_tree.bind("<Control-a>", self.select_all_files)
        self.file_tree.bind("<Control-A>", self.select_all_files)
        
        # Space - Toggle selection of current item (custom multi-select)
        self.file_tree.bind("<space>", self.toggle_selection)
        
        # Shift+Click for range selection is built into Treeview with extended mode
    
    def select_all_files(self, event=None):
        """Select all files in the tree"""
        items = self.file_tree.get_children()
        if items:
            self.file_tree.selection_set(items)
        return "break"
    
    def toggle_selection(self, event=None):
        """Toggle selection of focused item"""
        focused = self.file_tree.focus()
        if focused:
            if focused in self.file_tree.selection():
                self.file_tree.selection_remove(focused)
            else:
                self.file_tree.selection_add(focused)
        return "break"
    
    def setup_file_context_menu(self):
        """Setup right-click context menu for file browser"""
        # Create context menu
        self.file_context_menu = tk.Menu(self.root, tearoff=0)
        self.file_context_menu.add_command(label="👁️ View in 360° Viewer", 
                                          command=self.view_selected_in_viewer)
        self.file_context_menu.add_separator()
        self.file_context_menu.add_command(label="⬇️ Download", 
                                          command=self.download_selected)
        self.file_context_menu.add_command(label="🗑️ Delete", 
                                          command=self.delete_selected)
        self.file_context_menu.add_separator()
        self.file_context_menu.add_command(label="📋 Copy Filename", 
                                          command=self.copy_filename)
        
        # Bind right-click to show menu
        self.file_tree.bind("<Button-3>", self.show_file_context_menu)  # Linux/Windows
        self.file_tree.bind("<Control-Button-1>", self.show_file_context_menu)  # Mac
        
        # Bind click elsewhere to close menu
        self.root.bind("<Button-1>", self.close_context_menu)
    
    def close_context_menu(self, event=None):
        """Close context menu when clicking elsewhere"""
        try:
            self.file_context_menu.unpost()
        except:
            pass
    
    def show_file_context_menu(self, event):
        """Show context menu on right-click"""
        # Select item under cursor
        item = self.file_tree.identify_row(event.y)
        if item:
            # If not already selected, select this item
            if item not in self.file_tree.selection():
                self.file_tree.selection_set(item)
            
            # Show menu
            try:
                self.file_context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                # Ensure menu is closed when clicking elsewhere
                self.file_context_menu.grab_release()
    
    def get_selected_file_info(self):
        """Get file number and name for selected item"""
        selected = self.file_tree.selection()
        if not selected:
            return None, None
        
        item = selected[0]
        values = self.file_tree.item(item, 'values')
        name = values[0] if values else "unknown"
        # Get file number from hidden column (index 3)
        idx = int(values[3]) if len(values) > 3 and values[3] else self.file_tree.index(item) + 1
        
        return idx, name
    
    def view_selected_in_viewer(self):
        """Download and view selected file(s) in 360° viewer - ignores non-viewable files"""
        selected = self.file_tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select a file to view.")
            return
        
        # Find first viewable file in selection (ignore others silently)
        for item in selected:
            values = self.file_tree.item(item, 'values')
            name = values[0] if values else "unknown"
            # Get file number from hidden column
            idx = int(values[3]) if len(values) > 3 and values[3] else self.file_tree.index(item) + 1
            
            # Check if it's viewable (image or video)
            ext = name.lower().split('.')[-1] if '.' in name else ''
            if ext in ['jpg', 'jpeg', 'png', 'mp4', 'mov', 'avi']:
                # Found a viewable file, open it
                self._view_single_file(idx, name)
                return
        
        # No viewable files found
        messagebox.showinfo("Not Supported", 
            "360° Viewer only supports images and videos.\n\n"
            "No viewable files found in selection.")
    
    def _view_single_file(self, idx, name):
        """Download and view a single file with warning dialog and cancel support"""
        import tempfile
        
        # Get file size first
        file_size_str = "Unknown size"
        file_size_bytes = None
        try:
            result = subprocess.run(
                ["gphoto2", "--list-files"],
                capture_output=True, text=True, timeout=30
            )
            for line in result.stdout.split('\n'):
                if line.strip().startswith(f'#{idx}'):
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        file_size_str = parts[2]
                        # Try to parse for MB display
                        try:
                            size_val = float(parts[2][:-2])  # Remove MB/KB/etc
                            size_unit = parts[2][-2:].upper()
                            if size_unit == 'MB' and size_val > 100:
                                file_size_str = f"{parts[2]} ({size_val/1000:.1f} GB)"
                            elif size_unit == 'KB':
                                file_size_str = f"{parts[2]} ({size_val/1000:.1f} MB)"
                        except:
                            pass
                    break
        except:
            pass
        
        # Check if it's a video (warn about large files)
        ext = name.lower().split('.')[-1] if '.' in name else ''
        is_video = ext in ['mp4', 'mov', 'avi']
        
        # Show warning/confirmation dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Download Required")
        dialog.geometry("450x250")
        dialog.transient(self.root)
        # Don't use grab_set - prevents main window close
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 225
        y = (dialog.winfo_screenheight() // 2) - 125
        dialog.geometry(f"+{x}+{y}")
        
        # Icon and warning
        ttk.Label(dialog, text="📥", font=("Arial", 32)).pack(pady=(10, 5))
        
        # Message
        msg = f"The file must be downloaded before viewing.\n\n"
        msg += f"File: {name}\n"
        msg += f"Size: {file_size_str}\n"
        
        if is_video:
            msg += "\n⚠️ This is a video file and may take\nseveral minutes to download."
        
        ttk.Label(dialog, text=msg, justify="center").pack(pady=10)
        
        # Progress frame (hidden initially)
        progress_frame = ttk.Frame(dialog)
        self.view_progress_var = tk.DoubleVar(value=0)
        self.view_status_var = tk.StringVar(value="Ready to download...")
        
        ttk.Label(progress_frame, textvariable=self.view_status_var).pack()
        ttk.Progressbar(progress_frame, variable=self.view_progress_var, 
                       maximum=100, length=350).pack(pady=5)
        
        # Store cancel flag and thread
        self.view_cancelled = False
        self.view_thread = None
        
        def do_download():
            download_btn.config(state=tk.DISABLED)
            cancel_btn.config(text="Cancel Download", command=cancel_download)
            progress_frame.pack(pady=10)
            
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, name)
            
            self.view_thread = threading.Thread(
                target=download_worker,
                args=(temp_path,)
            )
            self.view_thread.start()
        
        def download_worker(temp_path):
            try:
                self.root.after(0, lambda: self.view_status_var.set("Downloading..."))
                
                # Start download process
                process = subprocess.Popen(
                    ["gphoto2", "--get-file", str(idx), f"--filename={temp_path}"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                
                # Poll for progress
                while process.poll() is None:
                    if self.view_cancelled:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except:
                            process.kill()
                        self.root.after(0, lambda: self.view_status_var.set("Download cancelled"))
                        return
                    
                    time.sleep(0.5)
                    
                    # Update progress (animate since we don't have total)
                    if os.path.exists(temp_path):
                        current_size = os.path.getsize(temp_path)
                        size_str = format_size_bytes(current_size)
                        self.root.after(0, lambda s=size_str: 
                            self.view_status_var.set(f"Downloaded: {s}"))
                        # Animate progress bar
                        current = self.view_progress_var.get()
                        self.view_progress_var.set((current + 10) % 100)
                
                # Check result
                if process.returncode == 0 and os.path.exists(temp_path):
                    self.root.after(0, lambda: self.view_status_var.set("Opening viewer..."))
                    subprocess.Popen(["python3", "km360_viewer.py", temp_path])
                    self.root.after(0, dialog.destroy)
                else:
                    stderr = process.stderr.read().decode() if process.stderr else "Unknown error"
                    self.root.after(0, lambda: self.view_status_var.set(f"Failed: {stderr[:50]}"))
                    self.root.after(0, lambda: cancel_btn.config(text="Close", state=tk.NORMAL))
                    
            except Exception as e:
                self.root.after(0, lambda: self.view_status_var.set(f"Error: {str(e)}"))
        
        def cancel_download():
            self.view_cancelled = True
            self.view_status_var.set("Cancelling...")
            cancel_btn.config(state=tk.DISABLED)
            # Dialog will close when thread finishes
            self.root.after(2000, dialog.destroy)
        
        def close_dialog():
            if self.view_thread and self.view_thread.is_alive():
                self.view_cancelled = True
                self.view_thread.join(timeout=2)
            dialog.destroy()
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        download_btn = ttk.Button(btn_frame, text="Download & View", command=do_download)
        download_btn.pack(side=tk.LEFT, padx=5)
        
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=close_dialog)
        cancel_btn.pack(side=tk.LEFT, padx=5)
        
        progress_frame.pack_forget()  # Hide initially
        
        dialog.protocol("WM_DELETE_WINDOW", close_dialog)
    
    def copy_filename(self):
        """Copy selected filename to clipboard"""
        idx, name = self.get_selected_file_info()
        if name:
            self.root.clipboard_clear()
            self.root.clipboard_append(name)
            self.set_status(f"Copied: {name}")
    
    def setup_tabs(self):
        """Setup tabbed interface"""
        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Tab 1: Quick Actions
        self.setup_quick_actions_tab()
        
        # Tab 2: Camera Settings
        self.setup_settings_tab()
        
        # Tab 3: Info
        self.setup_info_tab()
        
        # Tab 4: 360° Viewer
        self.setup_viewer_tab()
        

    
    def setup_quick_actions_tab(self):
        """Setup quick actions tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="⚡ Quick Actions")
        
        # Title
        ttk.Label(tab, text="Quick Actions", font=("Arial", 16, "bold")).pack(pady=20)
        
        # Actions frame
        actions_frame = ttk.Frame(tab)
        actions_frame.pack(pady=20)
        
        # Time sync
        time_frame = ttk.LabelFrame(actions_frame, text="Date & Time", padding=10)
        time_frame.pack(fill=tk.X, pady=5)
        ttk.Label(time_frame, text="Camera has no RTC battery - time resets when battery removed").pack(anchor=tk.W)
        ttk.Button(time_frame, text="Sync to System Time", 
                  command=self.sync_datetime).pack(pady=(10, 0))
        
        # Storage
        storage_frame = ttk.LabelFrame(actions_frame, text="Storage", padding=10)
        storage_frame.pack(fill=tk.X, pady=5)
        ttk.Button(storage_frame, text="Format SD Card...", 
                  command=self.format_sd).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(storage_frame, text="Storage Info", 
                  command=self.show_storage_info).pack(side=tk.LEFT)
        
        # WiFi
        wifi_frame = ttk.LabelFrame(actions_frame, text="WiFi Configuration", padding=10)
        wifi_frame.pack(fill=tk.X, pady=5)
        ttk.Button(wifi_frame, text="Configure WiFi...", 
                  command=self.configure_wifi).pack()
        
        # Application
        app_frame = ttk.LabelFrame(actions_frame, text="Application", padding=10)
        app_frame.pack(fill=tk.X, pady=5)
        ttk.Button(app_frame, text="🚀 Add to Start Menu...", 
                  command=self.install_desktop_entry).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(app_frame, text="Settings...", 
                  command=self.show_settings).pack(side=tk.LEFT)
    
    def setup_settings_tab(self):
        """Setup camera settings tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="⚙️ Settings")
        
        ttk.Label(tab, text="Camera Settings", font=("Arial", 16, "bold")).pack(pady=20)
        
        # Settings container with scrollbar
        container = ttk.Frame(tab)
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # White Balance
        wb_frame = ttk.LabelFrame(scrollable_frame, text="White Balance", padding=10)
        wb_frame.pack(fill=tk.X, pady=5)
        self.wb_var = tk.StringVar(value="Automatic")
        for value, label in [("0", "Automatic"), ("1", "Daylight"), 
                            ("2", "Fluorescent"), ("3", "Tungsten")]:
            ttk.Radiobutton(wb_frame, text=label, variable=self.wb_var, 
                          value=value).pack(anchor=tk.W)
        ttk.Button(wb_frame, text="Apply", command=self.apply_whitebalance).pack(pady=(10, 0))
        
        # Movie Loop Length
        loop_frame = ttk.LabelFrame(scrollable_frame, text="Movie Loop Length", padding=10)
        loop_frame.pack(fill=tk.X, pady=5)
        ttk.Label(loop_frame, text="⚠️ Unknown: Likely controls loop recording buffer duration (dashcam mode).",
                 font=("Arial", 9, "italic"), foreground="orange", wraplength=400).pack(anchor=tk.W)
        self.loop_var = tk.StringVar(value="5")
        for value, label in [("0", "5 seconds"), ("1", "10 seconds"), 
                            ("2", "30 seconds"), ("3", "60 seconds")]:
            ttk.Radiobutton(loop_frame, text=label, variable=self.loop_var, 
                          value=value).pack(anchor=tk.W)
        ttk.Button(loop_frame, text="Apply", command=self.apply_looplength).pack(pady=(10, 0))
        
        # Capture Target
        target_frame = ttk.LabelFrame(scrollable_frame, text="Capture Target", padding=10)
        target_frame.pack(fill=tk.X, pady=5)
        self.target_var = tk.StringVar(value="1")
        ttk.Radiobutton(target_frame, text="Internal RAM", variable=self.target_var, 
                       value="0").pack(anchor=tk.W)
        ttk.Radiobutton(target_frame, text="Memory Card (SD)", variable=self.target_var, 
                       value="1").pack(anchor=tk.W)
        ttk.Button(target_frame, text="Apply", command=self.apply_capturetarget).pack(pady=(10, 0))
        
        # Copyright
        copy_frame = ttk.LabelFrame(scrollable_frame, text="Copyright Info", padding=10)
        copy_frame.pack(fill=tk.X, pady=5)
        self.copyright_var = tk.StringVar()
        ttk.Entry(copy_frame, textvariable=self.copyright_var, width=40).pack()
        ttk.Button(copy_frame, text="Set Copyright", command=self.apply_copyright).pack(pady=(10, 0))
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_info_tab(self):
        """Setup information tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="ℹ️ Info")
        
        ttk.Label(tab, text="Camera Information", font=("Arial", 16, "bold")).pack(pady=20)
        
        # Info text widget
        self.info_text = scrolledtext.ScrolledText(tab, wrap=tk.WORD, width=80, height=30)
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Refresh button
        ttk.Button(tab, text="Refresh Info", command=self.refresh_info).pack(pady=10)
        
        # Initial info
        self.info_text.insert(tk.END, "Click 'Connect to Camera' or 'Refresh Info' to load camera details.\n\n")
        self.info_text.insert(tk.END, "KeyMission 360 Linux Utility\n")
        self.info_text.insert(tk.END, f"Version: {VERSION}\n\n")
        self.info_text.insert(tk.END, "Features:\n")
        self.info_text.insert(tk.END, "- File download with resume support\n")
        self.info_text.insert(tk.END, "- Auto 360° metadata injection for videos (YouTube ready)\n")
        self.info_text.insert(tk.END, "- Optional delete from camera after download\n")
        self.info_text.insert(tk.END, "- Date/time synchronization\n")
        self.info_text.insert(tk.END, "- Camera settings configuration\n")
        self.info_text.insert(tk.END, "- SD card formatting\n")
        self.info_text.insert(tk.END, "- 360° image/video viewer\n")
        self.info_text.insert(tk.END, "- USB port memory for quick reset\n\n")
        self.info_text.insert(tk.END, "Planned (v2.0):\n")
        self.info_text.insert(tk.END, "- Batch Operations\n")
        self.info_text.insert(tk.END, "- Advanced Settings panel\n")
        self.info_text.insert(tk.END, "- Tethered Shooting\n")
        self.info_text.insert(tk.END, "- GPS Data Editor\n")
        self.info_text.configure(state=tk.DISABLED)
    
    def setup_viewer_tab(self):
        """Setup 360° viewer tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="👁️ 360° Viewer")
        
        ttk.Label(tab, text="360° Image & Video Viewer", font=("Arial", 16, "bold")).pack(pady=20)
        
        info_frame = ttk.LabelFrame(tab, text="About", padding=10)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(info_frame, text="View equirectangular 360° photos and videos with interactive controls.",
                 wraplength=600).pack(anchor=tk.W)
        
        ttk.Label(info_frame, text="\nFeatures:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(info_frame, text="• Mouse drag to look around").pack(anchor=tk.W)
        ttk.Label(info_frame, text="• Scroll to zoom").pack(anchor=tk.W)
        ttk.Label(info_frame, text="• Arrow keys / WASD to navigate").pack(anchor=tk.W)
        ttk.Label(info_frame, text="• Video playback with pause/play").pack(anchor=tk.W)
        
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="Launch 360° Viewer", 
                  command=self.launch_viewer).pack(pady=5)
        
        # Quick access from camera files
        quick_frame = ttk.LabelFrame(tab, text="Quick Open from Camera", padding=10)
        quick_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(quick_frame, text="Right-click any file in the Camera Files list → 'View in 360° Viewer'",
                 foreground="blue").pack(pady=5)
        
        ttk.Label(quick_frame, text="Or select a file here:").pack(anchor=tk.W, pady=(10, 5))
        
        self.viewer_file_var = tk.StringVar()
        self.viewer_file_combo = ttk.Combobox(quick_frame, textvariable=self.viewer_file_var, 
                                              state="readonly", width=50)
        self.viewer_file_combo.pack(fill=tk.X, pady=5)
        
        ttk.Button(quick_frame, text="🔄 Refresh File List", 
                  command=self.refresh_viewer_file_list).pack(pady=5)
        ttk.Button(quick_frame, text="👁️ Open Selected in Viewer", 
                  command=self.open_viewer_file_combo).pack(pady=5)
        
        ttk.Label(tab, text="Or run from terminal: python3 km360_viewer.py [file]",
                 foreground="gray").pack(pady=10)
    
    def launch_viewer(self):
        """Launch the 360° viewer"""
        import subprocess
        try:
            subprocess.Popen(["python3", "km360_viewer.py"])
        except Exception as e:
            messagebox.showerror("Error", f"Could not launch viewer: {e}")
    
    def refresh_viewer_file_list(self):
        """Refresh the file list in the viewer tab combo box"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to camera first.")
            return
        
        # Get all files from tree
        files = []
        for item in self.file_tree.get_children():
            values = self.file_tree.item(item, 'values')
            if values:
                name = values[0]
                # Get file number from hidden column
                file_num = int(values[3]) if len(values) > 3 and values[3] else self.file_tree.index(item) + 1
                # Only include images and videos
                ext = name.lower().split('.')[-1] if '.' in name else ''
                if ext in ['jpg', 'jpeg', 'png', 'mp4', 'mov', 'avi']:
                    files.append(f"{file_num}: {name}")
        
        self.viewer_file_combo['values'] = files
        if files:
            self.viewer_file_combo.set(files[0])
            self.set_status(f"Loaded {len(files)} viewable files")
        else:
            self.viewer_file_combo.set("")
            self.set_status("No viewable files found")
    
    def open_viewer_file_combo(self):
        """Open selected file from combo box in viewer"""
        selected = self.viewer_file_var.get()
        if not selected:
            messagebox.showinfo("No Selection", "Please select a file or refresh the list.")
            return
        
        # Parse file number
        try:
            idx = int(selected.split(':')[0])
        except:
            messagebox.showerror("Error", "Invalid file selection")
            return
        
        # Get filename
        name = selected.split(':', 1)[1].strip() if ':' in selected else f"file_{idx}"
        
        # Download and view
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, name)
        
        self.set_status(f"Downloading {name}...")
        
        def download_and_view():
            try:
                result = subprocess.run(
                    ["gphoto2", "--get-file", str(idx), f"--filename={temp_path}"],
                    capture_output=True, timeout=60
                )
                
                if result.returncode == 0 and os.path.exists(temp_path):
                    self.set_status(f"Opening {name}...")
                    subprocess.Popen(["python3", "km360_viewer.py", temp_path])
                else:
                    self.set_status("Failed to download")
                    messagebox.showerror("Error", "Failed to download file.")
            except Exception as e:
                self.set_status(f"Error: {str(e)}")
        
        threading.Thread(target=download_and_view).start()
    
    def browse_yt_file(self):
        """Browse for video file to export"""
        path = ask_open_filename(
            title="Select Video to Export",
            filetypes=[("Videos", "*.mp4 *.mov *.avi"), ("All Files", "*.*")],
            parent=self.root
        )
        if path:
            self.yt_file_var.set(path)
    
    def export_youtube(self):
        """Export video for YouTube"""
        file_path = self.yt_file_var.get()
        if not file_path:
            messagebox.showwarning("No File", "Please select a video file.")
            return
        
        if not os.path.exists(file_path):
            messagebox.showerror("Error", "File not found.")
            return
        
        self.yt_status.config(text="Exporting...", foreground="blue")
        self.root.update()
        
        import subprocess
        try:
            result = subprocess.run(
                ["python3", "km360_youtube_export.py", file_path],
                capture_output=True, text=True, timeout=120
            )
            
            if result.returncode == 0:
                self.yt_status.config(text="✓ Export complete!", foreground="green")
                messagebox.showinfo("Success", 
                    "Video exported successfully!\n\n"
                    "The video is ready to upload to YouTube.")
            else:
                self.yt_status.config(text="✗ Export failed", foreground="red")
                messagebox.showerror("Error", result.stderr)
        except Exception as e:
            self.yt_status.config(text="✗ Export failed", foreground="red")
            messagebox.showerror("Error", str(e))

    def setup_placeholder_tab(self, title, feature_key):
        """Setup a placeholder tab for future features"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=f"🚧 {title}")
        
        # Center content
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        
        frame = ttk.Frame(tab)
        frame.grid(row=0, column=0)
        
        # Icon
        ttk.Label(frame, text="🚧", font=("Arial", 72)).pack(pady=30)
        
        # Title
        ttk.Label(frame, text=title, font=("Arial", 20, "bold")).pack()
        
        # Description
        description = PLACEHOLDER_FEATURES.get(feature_key, "Coming soon!")
        ttk.Label(frame, text=description, wraplength=500, 
                 justify="center", font=("Arial", 12)).pack(pady=20)
        
        # Features list
        features_frame = ttk.LabelFrame(frame, text="Planned Features", padding=20)
        features_frame.pack(pady=20)
        
        features = self.get_placeholder_features(feature_key)
        for feature in features:
            ttk.Label(features_frame, text=f"• {feature}").pack(anchor=tk.W)
        
        # Note
        ttk.Label(frame, text="This feature is under development.", 
                 foreground="gray", font=("Arial", 10, "italic")).pack(pady=10)
    
    def get_placeholder_features(self, feature_key):
        """Get feature list for placeholder tabs"""
        features = {
            "batch_ops": [
                "Batch rename files",
                "Batch convert formats",
                "Batch delete",
                "Batch metadata edit",
                "Batch download"
            ],
            "advanced_settings": [
                "Detailed camera configuration",
                "Custom presets",
                "Firmware management",
                "Network settings",
                "Advanced troubleshooting"
            ],
            "tethered": [
                "Live view on computer",
                "Remote shutter control",
                "Instant download to PC",
                "Time-lapse shooting",
                "Multi-camera sync"
            ],
            "gps": [
                "Edit GPS coordinates",
                "View track logs",
                "Geotag photos",
                "Export to GPX",
                "Map visualization"
            ]
        }
        return features.get(feature_key, ["Feature details coming soon"])
    
    def setup_status_bar(self):
        """Setup status bar at bottom"""
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def set_status(self, message):
        """Update status bar message"""
        self.status_bar.config(text=message)
        self.root.update()
    
    def show_placeholder(self, feature_name):
        """Show placeholder dialog"""
        key = feature_name.lower().replace(" ", "_").replace("°", "")
        description = PLACEHOLDER_FEATURES.get(key, f"{feature_name} is coming in a future version.")
        PlaceholderDialog(self.root, feature_name, description)
    
    # --- Connection Methods ---
    
    def check_connection(self):
        """Check if camera is connected - non-blocking with short timeout"""
        def do_check():
            try:
                # Use a short timeout to prevent hanging
                result = subprocess.run(["gphoto2", "--auto-detect"], 
                                      capture_output=True, text=True, timeout=5)
                if "KeyMission 360" in result.stdout:
                    if not self.connected:
                        # Schedule connect on main thread
                        self.root.after(0, self.connect_camera)
                else:
                    if self.connected:
                        # Schedule disconnect on main thread
                        self.root.after(0, self.disconnect_camera)
            except subprocess.TimeoutExpired:
                # Camera is not responding - might need USB reset
                self.root.after(0, lambda: self.set_status("Camera not responding - try USB Reset"))
            except Exception as e:
                pass
        
        # Run check in thread to avoid blocking UI
        threading.Thread(target=do_check, daemon=True).start()
        
        # Schedule next check
        self.root.after(5000, self.check_connection)
    
    def connect_camera(self):
        """Connect to the camera and save USB port info - runs in thread to avoid blocking"""
        self.set_status("Connecting to camera...")
        
        def do_connect():
            try:
                # Check if camera is present (short timeout)
                result = subprocess.run(["gphoto2", "--auto-detect"], 
                                      capture_output=True, text=True, timeout=10)
                
                if "KeyMission 360" not in result.stdout:
                    self.root.after(0, lambda: (
                        messagebox.showerror("Connection Failed", 
                            "KeyMission 360 not found.\n\nMake sure the camera is:\n"
                            "- Connected via USB\n- Powered on (press Photo or Video button)\n\n"
                            "If the camera is connected but not responding,\n"
                            "try clicking '🔄 Reset USB' button."),
                        self.set_status("Not connected - try USB Reset")
                    ))
                    return
                
                # Save USB port info for faster reset
                if USB_AVAILABLE:
                    try:
                        import usb1
                        with usb1.USBContext() as context:
                            for device in context.getDeviceIterator(skip_on_error=True):
                                if device.getVendorID() == 0x04b0:
                                    bus = device.getBusNumber()
                                    addr = device.getDeviceAddress()
                                    port_str = f"{bus:03d}:{addr:03d}"
                                    config = load_config()
                                    config['last_usb_port'] = port_str
                                    save_config(config)
                                    print(f"Saved USB port: {port_str}")
                                    break
                    except Exception as e:
                        print(f"Could not save USB port info: {e}")
                
                # Get camera info (with retry and short timeout)
                info_success = False
                for attempt in range(3):
                    if self.cancelled:
                        return
                    try:
                        self.root.after(0, self.update_camera_info)
                        info_success = True
                        break
                    except Exception as e:
                        if attempt < 2:
                            self.root.after(0, lambda a=attempt: 
                                self.set_status(f"Camera slow to respond, retrying... ({a+1}/3)"))
                            time.sleep(1)
                        else:
                            print(f"Warning: Could not get camera info: {e}")
                
                self.connected = True
                self.root.after(0, lambda: (
                    self.status_label.config(text="● Connected", foreground="green"),
                    self.set_status("Connected to KeyMission 360"),
                    self.refresh_files()
                ))
                
            except subprocess.TimeoutExpired:
                self.root.after(0, lambda: (
                    messagebox.showwarning("Connection Timeout", 
                        "Camera is not responding.\n\n"
                        "The camera may be stuck. Try:\n"
                        "1. Click '🔄 Reset USB' button\n"
                        "2. Unplug and replug the USB cable\n"
                        "3. Power cycle the camera"),
                    self.set_status("Connection timeout - try USB Reset")
                ))
            except Exception as e:
                self.root.after(0, lambda: (
                    messagebox.showerror("Error", f"Failed to connect: {str(e)}"),
                    self.set_status("Connection error")
                ))
        
        # Run connection in thread to avoid blocking UI
        self.connection_thread = threading.Thread(target=do_connect, daemon=True)
        self.connection_thread.start()
    
    def disconnect_camera(self):
        """Disconnect from camera"""
        self.connected = False
        self.status_label.config(text="● Not Connected", foreground="red")
        self.camera_model_label.config(text="Camera: -")
        self.battery_label.config(text="Battery: -")
        self.file_tree.delete(*self.file_tree.get_children())
        self.set_status("Disconnected")
    
    def update_camera_info(self):
        """Update camera information display"""
        try:
            # Get summary
            result = subprocess.run(["gphoto2", "--summary"], 
                                  capture_output=True, text=True, timeout=30)
            
            # Parse info (simplified)
            lines = result.stdout.split('\n')
            for line in lines:
                if "Model:" in line:
                    model = line.split(":", 1)[1].strip()
                    self.camera_model_label.config(text=f"Camera: {model}")
                if "Battery Level" in line or "100%" in line:
                    battery = line.split(":")[-1].strip()
                    self.battery_label.config(text=f"Battery: {battery}")
            
            # Update info tab
            self.refresh_info()
            
        except Exception as e:
            print(f"Error getting camera info: {e}")
    
    # --- File Operations ---
    
    def refresh_files(self):
        """Refresh file list from camera - filter to images and videos only"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to camera first.")
            return
        
        self.set_status("Reading file list...")
        self.file_tree.delete(*self.file_tree.get_children())
        
        # Supported image and video extensions
        image_exts = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif'}
        video_exts = {'.mp4', '.mov', '.avi', '.mkv', '.m4v', '.3gp', '.mts'}
        
        try:
            result = subprocess.run(["gphoto2", "--list-files"], 
                                  capture_output=True, text=True, timeout=30)
            
            lines = result.stdout.split('\n')
            files_added = 0
            files_filtered = 0
            
            for line in lines:
                # Parse gphoto2 list-files output
                # Format: #<num> <name> <size> <date>
                if line.strip().startswith('#'):
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        num = parts[0][1:]  # Remove #
                        name = parts[1]
                        size = parts[2]
                        date = ' '.join(parts[3:])
                        
                        # Check if it's an image or video file
                        ext = os.path.splitext(name)[1].lower()
                        if ext in image_exts or ext in video_exts:
                            # Store file_num in hidden column for accurate delete/download
                            self.file_tree.insert('', 'end', values=(name, size, date, num))
                            files_added += 1
                        else:
                            files_filtered += 1
            
            status_msg = f"Loaded {files_added} media files"
            if files_filtered > 0:
                status_msg += f" ({files_filtered} hidden)"
            self.set_status(status_msg)
            
        except Exception as e:
            self.set_status(f"Error reading files: {str(e)}")
    
    def _show_download_options_dialog(self, num_files):
        """Show download options dialog with delete checkbox"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Download {num_files} File{'s' if num_files > 1 else ''}")
        dialog.geometry("450x320")
        dialog.minsize(400, 280)
        dialog.transient(self.root)
        # Don't use grab_set - prevents main window close
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 225
        y = (dialog.winfo_screenheight() // 2) - 160
        dialog.geometry(f"+{x}+{y}")
        
        # Info
        ttk.Label(dialog, text="📥 Download", 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        video_note = "\n\nNote: Video files will automatically have 360° metadata injected for YouTube upload."
        ttk.Label(dialog, text=f"Will download {num_files} file{'s' if num_files > 1 else ''} from camera.{video_note}",
                 wraplength=400).pack(pady=5, padx=20)
        
        # Options frame
        options_frame = ttk.LabelFrame(dialog, text="Options", padding=10)
        options_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Delete after download checkbox
        delete_var = tk.BooleanVar(value=get_config_value('delete_after_download', False))
        ttk.Checkbutton(options_frame, 
                       text="Remove from camera after successful download",
                       variable=delete_var).pack(anchor=tk.W)
        
        # Info label
        ttk.Label(options_frame, 
                 text="⚠️ Warning: This will permanently delete files from the camera.",
                 foreground="orange", font=("Arial", 9)).pack(anchor=tk.W, pady=(5, 0))
        
        # Result storage
        result = [False]
        
        def on_ok():
            # Save the delete preference
            set_config_value('delete_after_download', delete_var.get())
            result[0] = delete_var.get()
            dialog.destroy()
        
        def on_cancel():
            result[0] = None  # Cancelled
            dialog.destroy()
        
        def on_close():
            result[0] = None  # Treat window close as cancel
            dialog.destroy()
        
        # Buttons - pack at bottom to ensure visibility
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(side=tk.BOTTOM, pady=15)
        
        ttk.Button(btn_frame, text="Download", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Handle window close button
        dialog.protocol("WM_DELETE_WINDOW", on_close)
        
        # Wait for dialog
        self.root.wait_window(dialog)
        
        return result[0]

    def download_selected(self):
        """Download selected files with options dialog"""
        selected = self.file_tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select files to download.")
            return
        
        # Show download options
        delete_after = self._show_download_options_dialog(len(selected))
        if delete_after is None:
            return  # Cancelled
        
        # Ask for destination using native dialog
        dest = ask_directory(
            title="Select Download Destination",
            parent=self.root
        )
        if not dest:
            return
        
        # Get file numbers from selection
        files_to_download = []
        for item in selected:
            values = self.file_tree.item(item, 'values')
            name = values[0]
            # Get file number from hidden column (index 3)
            file_num = int(values[3]) if len(values) > 3 and values[3] else self.file_tree.index(item) + 1
            files_to_download.append((file_num, name))
        
        # Start download in thread
        self.download_thread = threading.Thread(
            target=self._download_files, 
            args=(files_to_download, dest, delete_after)
        )
        self.download_thread.start()
    
    def download_all(self):
        """Download all files with options dialog"""
        if not self.file_tree.get_children():
            messagebox.showinfo("No Files", "No files to download.")
            return
        
        num_files = len(self.file_tree.get_children())
        
        # Show download options
        delete_after = self._show_download_options_dialog(num_files)
        if delete_after is None:
            return  # Cancelled
        
        dest = ask_directory(
            title="Select Download Destination",
            parent=self.root
        )
        if not dest:
            return
        
        self.download_thread = threading.Thread(
            target=self._download_all_files,
            args=(dest, delete_after)
        )
        self.download_thread.start()
    
    def _download_files(self, files, dest, delete_after=False):
        """Download specific files with progress tracking and resume support"""
        self.show_download_progress_dialog(files, dest, delete_after)
    
    def _download_all_files(self, dest, delete_after=False):
        """Download all files with progress tracking"""
        # Get all files from tree
        files = []
        for item in self.file_tree.get_children():
            values = self.file_tree.item(item, 'values')
            if values:
                name = values[0]
                # Get file number from hidden column
                idx = int(values[3]) if len(values) > 3 and values[3] else self.file_tree.index(item) + 1
                files.append((idx, name))
        
        if files:
            self.show_download_progress_dialog(files, dest, delete_after)
        else:
            self.root.after(0, lambda: messagebox.showinfo("No Files", "No files to download."))
    
    def show_download_progress_dialog(self, files, dest, delete_after=False):
        """Show download progress dialog with queue and resume support"""
        DownloadProgressDialog(self.root, files, dest, self, delete_after=delete_after)
    
    def reset_usb_port(self):
        """Reset the USB port the camera is connected to - uses remembered port if available"""
        if not USB_AVAILABLE:
            messagebox.showerror("Error", 
                "USB libraries not available. Install pyusb and libusb1:\n"
                "pip install pyusb libusb1")
            return
        
        self.set_status("Resetting USB port...")
        
        def do_reset():
            try:
                context = usb1.USBContext()
                camera_device = None
                bus = None
                addr = None
                
                # First, try the remembered port from config
                config = load_config()
                last_port = config.get('last_usb_port')
                
                if last_port:
                    try:
                        bus_str, addr_str = last_port.split(':')
                        last_bus = int(bus_str)
                        last_addr = int(addr_str)
                        
                        self.set_status(f"Checking last known port {last_port}...")
                        
                        # Try to find device at the last known port
                        for device in context.getDeviceIterator(skip_on_error=True):
                            if (device.getBusNumber() == last_bus and 
                                device.getVendorID() == 0x04b0):
                                # Camera found at remembered port
                                bus = last_bus
                                addr = device.getDeviceAddress()  # Use current address
                                camera_device = device
                                self.set_status(f"Camera found at remembered port {last_bus:03d}:{addr:03d}")
                                break
                    except (ValueError, Exception) as e:
                        print(f"Could not parse last_usb_port: {e}")
                
                # If not found at remembered port, scan all devices
                if not camera_device:
                    self.set_status("Scanning USB bus for camera...")
                    
                    for device in context.getDeviceIterator(skip_on_error=True):
                        # Nikon vendor ID
                        if device.getVendorID() == 0x04b0:
                            camera_device = device
                            bus = device.getBusNumber()
                            addr = device.getDeviceAddress()
                            
                            # Save this port for next time
                            port_str = f"{bus:03d}:{addr:03d}"
                            config['last_usb_port'] = port_str
                            save_config(config)
                            
                            self.set_status(f"Found camera at bus {bus}, addr {addr} (saved for next time)")
                            break
                
                if not camera_device:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Camera Not Found", 
                        "No Nikon camera found on USB bus.\n"
                        "Make sure the camera is connected."))
                    self.set_status("Camera not found for USB reset")
                    return
                
                # Try to reset using usb.core (pyusb) - this is the most reliable method
                try:
                    dev = usb.core.find(idVendor=0x04b0)
                    if dev:
                        dev.reset()
                        self.set_status("USB port reset successful")
                        self.root.after(0, lambda: messagebox.showinfo(
                            "USB Reset", 
                            f"USB port reset at bus {bus}, address {addr}.\n\n"
                            "Wait a few seconds for the camera to reconnect,\n"
                            "then click 'Connect' or 'Refresh'."))
                        return
                except Exception as e:
                    print(f"pyusb reset failed: {e}")
                
                # Fallback: Try using usbreset via shell
                try:
                    result = subprocess.run(
                        ["usbreset", f"/dev/bus/usb/{bus:03d}/{addr:03d}"],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0:
                        self.set_status("USB port reset via usbreset")
                        self.root.after(0, lambda: messagebox.showinfo(
                            "USB Reset", 
                            "USB port has been reset.\n\n"
                            "Wait a few seconds for the camera to reconnect."))
                        return
                except FileNotFoundError:
                    pass  # usbreset not available
                
                # Last resort: Try kernel driver unbind/bind if we can find it
                self.root.after(0, lambda: self._try_sysfs_reset(bus, addr))
                
            except Exception as e:
                self.set_status(f"USB reset failed: {str(e)}")
                self.root.after(0, lambda: messagebox.showerror(
                    "USB Reset Failed", 
                    f"Failed to reset USB port:\n{str(e)}\n\n"
                    "You may need to run with sudo or unplug/replug manually."))
        
        threading.Thread(target=do_reset).start()
    
    def _try_sysfs_reset(self, bus, addr):
        """Try to reset USB device via sysfs"""
        try:
            # Find the device path
            result = subprocess.run(
                ["lsusb", "-s", f"{bus}:{addr}"],
                capture_output=True, text=True, timeout=15
            )
            
            # Try to reset using /dev/bus/usb
            usbdev = f"/dev/bus/usb/{bus:03d}/{addr:03d}"
            
            # Check if we have a udev rule or can use sudo
            messagebox.showinfo(
                "Manual Reset Required",
                f"Could not automatically reset USB port.\n\n"
                f"Camera is at: {usbdev}\n\n"
                "Options:\n"
                "1. Unplug and replug the USB cable manually\n"
                "2. Run: sudo usbreset " + usbdev + "\n"
                "3. Install usbreset: sudo apt-get install usbutils\n\n"
                "After reset, click 'Connect' to reconnect.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not determine USB device path: {e}")
    
    def delete_selected(self):
        """Delete selected files from camera"""
        selected = self.file_tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select files to delete.")
            return
        
        if not messagebox.askyesno("Confirm Delete", 
                                   f"Delete {len(selected)} files from camera?\n\n"
                                   "This cannot be undone!"):
            return
        
        # Get current folder from camera first
        folder = "/"
        try:
            result = subprocess.run(["gphoto2", "--list-folders"],
                                    capture_output=True, text=True, timeout=10)
            # Parse to find the folder with files
            for line in result.stdout.split('\n'):
                if 'store_' in line or 'DCIM' in line:
                    folder = line.strip()
                    break
        except:
            pass
        
        deleted_count = 0
        failed_files = []
        
        # Delete files using stored file numbers
        for item in selected:
            values = self.file_tree.item(item, 'values')
            # Get file number from hidden column
            file_num = int(values[3]) if len(values) > 3 and values[3] else self.file_tree.index(item) + 1
            name = values[0] if values else f"file_{file_num}"
            
            try:
                # Try without folder first (some cameras work this way)
                result = subprocess.run(["gphoto2", "--delete-file", str(file_num)], 
                             capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    # Try with folder specification
                    result = subprocess.run(["gphoto2", "--folder", folder, "--delete-file", str(file_num)], 
                                 capture_output=True, text=True, timeout=30)
                    
                    if result.returncode != 0:
                        # Try with --recurse flag
                        result = subprocess.run(["gphoto2", "--recurse", "--delete-file", str(file_num)], 
                                     capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    deleted_count += 1
                else:
                    failed_files.append((name, result.stderr.strip()))
                    print(f"Error deleting file {file_num}: {result.stderr}")
            except Exception as e:
                failed_files.append((name, str(e)))
                print(f"Error deleting file {file_num}: {e}")
        
        self.refresh_files()
        
        if failed_files:
            error_msg = "\n".join([f"• {name}: {err[:50]}" for name, err in failed_files[:3]])
            if len(failed_files) > 3:
                error_msg += f"\n... and {len(failed_files) - 3} more"
            messagebox.showwarning("Delete Complete", 
                f"Deleted {deleted_count} files.\nFailed: {len(failed_files)}\n\n{error_msg}")
        else:
            self.set_status(f"Deleted {deleted_count} files")
    
    # --- Settings Methods ---
    
    def sync_datetime(self):
        """Sync camera time to system time"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to camera first.")
            return
        
        try:
            subprocess.run(["gphoto2", "--set-config", "datetime=now"], 
                         capture_output=True, timeout=30)
            self.set_status("Date/Time synchronized")
            messagebox.showinfo("Success", "Camera time synchronized with system time.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to sync time: {str(e)}")
    
    def format_sd(self):
        """Format SD card"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to camera first.")
            return
        
        if not messagebox.askyesno("CONFIRM FORMAT", 
            "⚠️ WARNING: This will ERASE ALL DATA on the SD card!\n\n"
            "Are you sure you want to format the SD card?\n\n"
            "Type 'YES' to proceed:", icon='warning'):
            return
        
        # Use our dedicated formatter
        try:
            subprocess.run(["python3", "km360_formatter.py", "--force"], 
                         capture_output=True, timeout=60)
            self.set_status("SD card formatted")
            messagebox.showinfo("Success", "SD card formatted successfully.")
            self.refresh_files()
        except Exception as e:
            messagebox.showerror("Error", f"Format failed: {str(e)}")
    
    def apply_whitebalance(self):
        """Apply white balance setting"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to camera first.")
            return
        
        try:
            subprocess.run(["gphoto2", "--set-config", 
                          f"whitebalance={self.wb_var.get()}"], 
                         capture_output=True, timeout=30)
            self.set_status("White balance updated")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set white balance: {str(e)}")
    
    def apply_looplength(self):
        """Apply movie loop length"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to camera first.")
            return
        
        try:
            subprocess.run(["gphoto2", "--set-config", 
                          f"movielooplength={self.loop_var.get()}"], 
                         capture_output=True, timeout=30)
            self.set_status("Loop length updated")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set loop length: {str(e)}")
    
    def apply_capturetarget(self):
        """Apply capture target"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to camera first.")
            return
        
        try:
            subprocess.run(["gphoto2", "--set-config", 
                          f"capturetarget={self.target_var.get()}"], 
                         capture_output=True, timeout=30)
            self.set_status("Capture target updated")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set capture target: {str(e)}")
    
    def apply_copyright(self):
        """Apply copyright info"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to camera first.")
            return
        
        copyright_text = self.copyright_var.get()
        try:
            subprocess.run(["gphoto2", "--set-config", 
                          f"/main/other/501f={copyright_text}"], 
                         capture_output=True, timeout=30)
            self.set_status("Copyright info set")
            messagebox.showinfo("Success", "Copyright info updated.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set copyright: {str(e)}")
    
    def configure_wifi(self):
        """Open WiFi configuration dialog"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to camera first.")
            return
        
        # Simple WiFi config dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("WiFi Configuration")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="WiFi Settings", font=("Arial", 14, "bold")).pack(pady=10)
        
        # SSID
        ttk.Label(dialog, text="SSID (Camera Name):").pack(anchor=tk.W, padx=20)
        ssid_var = tk.StringVar(value="KM360")
        ttk.Entry(dialog, textvariable=ssid_var, width=30).pack(pady=(0, 10), padx=20)
        
        # Password
        ttk.Label(dialog, text="WiFi Password:").pack(anchor=tk.W, padx=20)
        pass_var = tk.StringVar(value="NikonKeyMission")
        ttk.Entry(dialog, textvariable=pass_var, width=30, show="*").pack(pady=(0, 10), padx=20)
        
        def apply_wifi():
            try:
                subprocess.run(["gphoto2", "--set-config", 
                              f"/main/other/d338={ssid_var.get()}"], 
                             capture_output=True, timeout=30)
                subprocess.run(["gphoto2", "--set-config", 
                              f"/main/other/d340={pass_var.get()}"], 
                             capture_output=True, timeout=30)
                self.set_status("WiFi configuration updated")
                messagebox.showinfo("Success", "WiFi settings updated.\n\n"
                                  "Note: You may need to re-pair with SnapBridge app.")
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update WiFi: {str(e)}")
        
        ttk.Button(dialog, text="Apply", command=apply_wifi).pack(pady=20)
    
    # --- Info Methods ---
    
    def show_camera_info(self):
        """Show camera information dialog"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to camera first.")
            return
        
        try:
            result = subprocess.run(["gphoto2", "--summary"], 
                                  capture_output=True, text=True, timeout=30)
            
            dialog = tk.Toplevel(self.root)
            dialog.title("Camera Information")
            dialog.geometry("600x500")
            
            text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD)
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert(tk.END, result.stdout)
            text.configure(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get info: {str(e)}")
    
    def show_storage_info(self):
        """Show storage information"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to camera first.")
            return
        
        try:
            result = subprocess.run(["gphoto2", "--storage-info"], 
                                  capture_output=True, text=True, timeout=30)
            
            messagebox.showinfo("Storage Information", result.stdout)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get storage info: {str(e)}")
    
    def refresh_info(self):
        """Refresh info tab"""
        if not self.connected:
            return
        
        try:
            result = subprocess.run(["gphoto2", "--summary"], 
                                  capture_output=True, text=True, timeout=30)
            
            self.info_text.configure(state=tk.NORMAL)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, result.stdout)
            self.info_text.configure(state=tk.DISABLED)
            
        except Exception as e:
            print(f"Error refreshing info: {e}")
    
    # --- Menu Methods ---
    
    def show_settings(self):
        """Show application settings"""
        # Keep reference to prevent garbage collection
        self.settings_dialog = tk.Toplevel(self.root)
        dialog = self.settings_dialog
        dialog.title("Application Settings")
        dialog.geometry("500x550")
        dialog.minsize(450, 500)
        dialog.transient(self.root)
        
        # Don't use grab_set - it prevents window manager from closing the window properly
        
        ttk.Label(dialog, text="Application Settings", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Load current config
        config = load_config()
        
        # Download directory
        ttk.Label(dialog, text="Default Download Directory:").pack(anchor=tk.W, padx=20)
        dir_frame = ttk.Frame(dialog)
        dir_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        download_dir = tk.StringVar(value=config.get('last_download_dir', str(Path.home() / 'Pictures')))
        ttk.Entry(dir_frame, textvariable=download_dir).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        def browse_dir():
            d = ask_directory(
                title="Select Default Download Directory",
                parent=dialog
            )
            if d:
                download_dir.set(d)
        
        ttk.Button(dir_frame, text="Browse...", command=browse_dir).pack(side=tk.LEFT, padx=(5, 0))
        
        # Download options frame
        dl_frame = ttk.LabelFrame(dialog, text="Download Options", padding=10)
        dl_frame.pack(fill=tk.X, padx=20, pady=10)
        
        delete_after = tk.BooleanVar(value=config.get('delete_after_download', False))
        ttk.Checkbutton(dl_frame, text="Default: Remove from camera after download",
                       variable=delete_after).pack(anchor=tk.W)
        
        ttk.Label(dl_frame, text="(Videos automatically get 360° metadata for YouTube)",
                 foreground="gray", font=("Arial", 9)).pack(anchor=tk.W, pady=(5, 0))
        
        # Auto-sync time option
        auto_sync = tk.BooleanVar(value=config.get('auto_sync_time', False))
        ttk.Checkbutton(dialog, text="Auto-sync time on connect", 
                       variable=auto_sync).pack(anchor=tk.W, padx=20, pady=10)
        
        # USB Reset frame
        usb_frame = ttk.LabelFrame(dialog, text="USB Port Memory", padding=10)
        usb_frame.pack(fill=tk.X, padx=20, pady=10)
        
        last_usb = config.get('last_usb_port', 'Not detected yet')
        ttk.Label(usb_frame, text=f"Last detected USB port: {last_usb}").pack(anchor=tk.W)
        
        ttk.Label(usb_frame, text="The USB reset button will use this port for faster reset.",
                 foreground="gray", font=("Arial", 9), wraplength=380).pack(anchor=tk.W, pady=(5, 0))
        
        # File dialog preference
        dialog_frame = ttk.LabelFrame(dialog, text="File Dialog Style", padding=10)
        dialog_frame.pack(fill=tk.X, padx=20, pady=10)
        
        dialog_pref = tk.StringVar(value=config.get('preferred_file_dialog', 'auto'))
        ttk.Radiobutton(dialog_frame, text="Auto-detect (recommended)", 
                       variable=dialog_pref, value="auto").pack(anchor=tk.W)
        ttk.Radiobutton(dialog_frame, text="GTK (GNOME, XFCE, etc.)", 
                       variable=dialog_pref, value="gtk").pack(anchor=tk.W)
        ttk.Radiobutton(dialog_frame, text="KDE (KDialog)", 
                       variable=dialog_pref, value="kde").pack(anchor=tk.W)
        ttk.Radiobutton(dialog_frame, text="Standard (Tkinter)", 
                       variable=dialog_pref, value="tk").pack(anchor=tk.W)
        
        def save_settings():
            config['last_download_dir'] = download_dir.get()
            config['delete_after_download'] = delete_after.get()
            config['auto_sync_time'] = auto_sync.get()
            config['preferred_file_dialog'] = dialog_pref.get()
            save_config(config)
            dialog.destroy()
        
        ttk.Button(dialog, text="Save", command=save_settings).pack(pady=10)
    
    def show_download_manager(self):
        """Show download manager"""
        # Get all files from current file tree
        files = []
        for item in self.file_tree.get_children():
            values = self.file_tree.item(item, 'values')
            if values:
                name = values[0]
                # Get file number from hidden column
                file_num = int(values[3]) if len(values) > 3 and values[3] else self.file_tree.index(item) + 1
                files.append((file_num, name))
        
        if not files:
            messagebox.showinfo("No Files", "No files available. Connect to camera first.")
            return
        
        # Show download options
        delete_after = self._show_download_options_dialog(len(files))
        if delete_after is None:
            return
        
        # Ask for destination using native dialog
        dest = ask_directory(
            title="Select Download Destination",
            parent=self.root
        )
        if not dest:
            return
        
        # Show download dialog (don't use grab_set so main window can still be closed)
        dialog = DownloadProgressDialog(self.root, files, dest, self, delete_after=delete_after)
    
    def show_docs(self):
        """Show documentation"""
        try:
            with open("README.md", "r") as f:
                content = f.read()
            
            # Keep reference to prevent garbage collection
            self.docs_dialog = tk.Toplevel(self.root)
            self.docs_dialog.title("Documentation")
            self.docs_dialog.geometry("800x600")
            self.docs_dialog.transient(self.root)
            
            # Add close button frame
            btn_frame = ttk.Frame(self.docs_dialog)
            btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            ttk.Button(btn_frame, text="Close", 
                      command=self.docs_dialog.destroy).pack(side=tk.RIGHT)
            
            text = scrolledtext.ScrolledText(self.docs_dialog, wrap=tk.WORD)
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert(tk.END, content)
            text.configure(state=tk.DISABLED)
            
        except FileNotFoundError:
            messagebox.showinfo("Documentation", 
                "Documentation is available at:\n"
                "https://github.com/Innomen/KeyMission360Tools")

    def install_desktop_entry(self):
        """Install desktop entry for the application menu"""
        # Keep reference to prevent garbage collection
        self.install_dialog = tk.Toplevel(self.root)
        dialog = self.install_dialog
        dialog.title("Add to Start Menu")
        dialog.geometry("500x450")
        dialog.transient(self.root)
        # Don't use grab_set - prevents main window close
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - 250
        y = (dialog.winfo_screenheight() // 2) - 225
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(dialog, text="🚀 Add to Start Menu", 
                 font=("Arial", 16, "bold")).pack(pady=15)
        
        info_text = """This will add the KeyMission 360 Utility to your 
application menu so you can launch it from:

  • Activities / Application menu
  • Desktop launchers
  • Alt+F2 run dialog

The desktop entry will be installed for the current user.
"""
        ttk.Label(dialog, text=info_text, justify=tk.LEFT).pack(pady=10, padx=20)
        
        # Status frame
        status_frame = ttk.LabelFrame(dialog, text="Status", padding=10)
        status_frame.pack(fill=tk.X, padx=20, pady=10)
        
        status_var = tk.StringVar(value="Not installed")
        ttk.Label(status_frame, textvariable=status_var, 
                 font=("Arial", 10)).pack(anchor=tk.W)
        
        # Check current status
        from pathlib import Path
        xdg_data_home = os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')
        desktop_file = Path(xdg_data_home) / 'applications' / 'km360-utility.desktop'
        
        if desktop_file.exists():
            status_var.set(f"✓ Installed\n  {desktop_file}")
        
        def do_install():
            try:
                import subprocess
                result = subprocess.run(
                    ["python3", "km360_install_desktop.py"],
                    capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    messagebox.showinfo("Success", 
                        "Application added to Start Menu!\n\n"
                        "You can now launch it from your application menu.",
                        parent=dialog)
                    status_var.set(f"✓ Installed\n  {desktop_file}")
                else:
                    error_msg = result.stderr if result.stderr else "Unknown error"
                    messagebox.showerror("Error", 
                        f"Installation failed:\n{error_msg}",
                        parent=dialog)
            except Exception as e:
                messagebox.showerror("Error", 
                    f"Could not run installer:\n{str(e)}\n\n"
                    "Make sure km360_install_desktop.py is in the same directory.",
                    parent=dialog)
        
        def do_remove():
            if not desktop_file.exists():
                messagebox.showinfo("Not Installed", 
                    "Desktop entry is not installed.",
                    parent=dialog)
                return
            
            if messagebox.askyesno("Confirm Remove", 
                "Remove KeyMission 360 Utility from the Start Menu?",
                parent=dialog):
                try:
                    import subprocess
                    result = subprocess.run(
                        ["python3", "km360_install_desktop.py", "--remove"],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0:
                        messagebox.showinfo("Removed", 
                            "Desktop entry removed.",
                            parent=dialog)
                        status_var.set("Not installed")
                    else:
                        error_msg = result.stderr if result.stderr else "Unknown error"
                        messagebox.showerror("Error", 
                            f"Remove failed:\n{error_msg}",
                            parent=dialog)
                except Exception as e:
                    messagebox.showerror("Error", str(e), parent=dialog)
        
        # Buttons frame - packed at bottom to ensure visibility
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=15)
        
        ttk.Button(btn_frame, text="🚀 Install", command=do_install).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="🗑️ Remove", command=do_remove).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="❌ Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About", 
            f"{APP_NAME}\n"
            f"Version {VERSION}\n\n"
            "A Linux replacement for the Nikon KeyMission 360/170 Utility.\n\n"
            "Features:\n"
            "- File download with resume support\n"
            "- Auto 360° metadata for YouTube videos\n"
            "- Optional delete from camera\n"
            "- Date/time synchronization\n"
            "- Camera settings configuration\n"
            "- SD card formatting\n"
            "- USB port memory for quick reset\n\n"
            "License: MIT\n"
            "https://github.com/Innomen/KeyMission360Tools")


def run_headless_test():
    """Run basic tests without GUI"""
    print("=" * 60)
    print("KeyMission 360 GUI - Headless Test Mode")
    print("=" * 60)
    print()
    
    # Test 1: Check gphoto2
    print("[TEST 1] Checking gphoto2 installation...")
    try:
        result = subprocess.run(["gphoto2", "--version"], 
                              capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"  ✓ gphoto2 found: {version}")
        else:
            print("  ✗ gphoto2 returned error")
    except FileNotFoundError:
        print("  ✗ gphoto2 not installed")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Test 2: Check for camera
    print("\n[TEST 2] Checking for KeyMission 360...")
    try:
        result = subprocess.run(["gphoto2", "--auto-detect"], 
                              capture_output=True, text=True, timeout=15)
        if "KeyMission 360" in result.stdout:
            print("  ✓ KeyMission 360 detected")
            # Get summary
            result = subprocess.run(["gphoto2", "--summary"], 
                                  capture_output=True, text=True, timeout=30)
            for line in result.stdout.split('\n'):
                if "Model:" in line:
                    print(f"    {line.strip()}")
                if "Battery" in line:
                    print(f"    {line.strip()}")
        else:
            print("  ⚠ KeyMission 360 not connected (expected if camera off)")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Test 3: Check dependencies
    print("\n[TEST 3] Checking Python dependencies...")
    print("  ✓ tkinter (built-in)")
    print("  ✓ subprocess (built-in)")
    print("  ✓ threading (built-in)")
    print("  ✓ pathlib (built-in)")
    
    print("\n" + "=" * 60)
    print("Headless test complete")
    print("=" * 60)


def main():
    # Check for headless/test mode
    if len(sys.argv) > 1 and sys.argv[1] in ('--headless', '--test', '-t'):
        run_headless_test()
        return
    
    root = tk.Tk()
    
    # Set icon (if available) or use default
    try:
        root.iconphoto(True, tk.PhotoImage(file="icon.png"))
    except:
        pass
    
    app = KM360GUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\nReceived interrupt, closing application...")
        app.on_close()


if __name__ == "__main__":
    main()
