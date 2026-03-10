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
- (Planned: 360° viewer, YouTube export, video player)

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
from datetime import datetime
from pathlib import Path

# Version info
VERSION = "1.0"
APP_NAME = "KeyMission 360 Linux Utility"

# Placeholder features for future versions
PLACEHOLDER_FEATURES = {
    "360_viewer": "360° Image Viewer - Coming in v2.0",
    "youtube_export": "YouTube Export - Coming in v2.0", 
    "video_player": "Video Player - Coming in v2.0",
    "batch_ops": "Batch Operations - Coming in v2.0",
    "advanced_settings": "Advanced Settings - Coming in v2.0",
    "tethered": "Tethered Shooting - Coming in v2.0",
    "gps": "GPS Data Editor - Coming in v2.0",
}


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
        
        # Setup UI
        self.setup_menu()
        self.setup_main_layout()
        self.setup_status_bar()
        
        # Try auto-connect
        self.root.after(1000, self.check_connection)
    
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
        
        # Placeholder features
        tools_menu.add_command(label="🚧 360° Image Viewer", 
                              command=lambda: self.show_placeholder("360° Image Viewer"))
        tools_menu.add_command(label="🚧 YouTube Export", 
                              command=lambda: self.show_placeholder("YouTube Export"))
        tools_menu.add_command(label="🚧 Video Player", 
                              command=lambda: self.show_placeholder("Video Player"))
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
        
        # Treeview for files
        columns = ("name", "size", "date")
        self.file_tree = ttk.Treeview(files_frame, columns=columns, 
                                      show="headings", selectmode="extended")
        
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
                  command=self.delete_selected).pack(side=tk.LEFT)
    
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
        
        # Tab 4: 360° Viewer (Placeholder)
        self.setup_placeholder_tab("360° Viewer", "360_viewer")
        
        # Tab 5: YouTube Export (Placeholder)
        self.setup_placeholder_tab("YouTube Export", "youtube_export")
    
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
        self.info_text.insert(tk.END, "- File download and management\n")
        self.info_text.insert(tk.END, "- Date/time synchronization\n")
        self.info_text.insert(tk.END, "- Camera settings configuration\n")
        self.info_text.insert(tk.END, "- SD card formatting\n\n")
        self.info_text.insert(tk.END, "Planned (v2.0):\n")
        self.info_text.insert(tk.END, "- 360° Image Viewer\n")
        self.info_text.insert(tk.END, "- YouTube Export\n")
        self.info_text.insert(tk.END, "- Video Player\n")
        self.info_text.insert(tk.END, "- Batch Operations\n")
        self.info_text.configure(state=tk.DISABLED)
    
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
            "360_viewer": [
                "Equirectangular image display",
                "Mouse drag to pan around",
                "Zoom in/out",
                "Split-screen mode",
                "Export current view"
            ],
            "youtube_export": [
                "Re-encode video for YouTube",
                "Inject 360° metadata",
                "Quality presets",
                "Batch processing",
                "Upload assistant"
            ],
            "video_player": [
                "MP4 playback",
                "Highlight tag navigation",
                "Trim and split",
                "Frame extraction",
                "360° video playback"
            ],
            "batch_ops": [
                "Batch rename files",
                "Batch convert formats",
                "Batch delete",
                "Batch metadata edit",
                "Batch download"
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
        """Check if camera is connected"""
        try:
            result = subprocess.run(["gphoto2", "--auto-detect"], 
                                  capture_output=True, text=True, timeout=5)
            if "KeyMission 360" in result.stdout:
                if not self.connected:
                    self.connect_camera()
            else:
                if self.connected:
                    self.disconnect_camera()
        except:
            pass
        
        # Schedule next check
        self.root.after(5000, self.check_connection)
    
    def connect_camera(self):
        """Connect to the camera"""
        self.set_status("Connecting to camera...")
        
        try:
            # Check if camera is present
            result = subprocess.run(["gphoto2", "--auto-detect"], 
                                  capture_output=True, text=True, timeout=10)
            
            if "KeyMission 360" not in result.stdout:
                messagebox.showerror("Connection Failed", 
                    "KeyMission 360 not found.\n\nMake sure the camera is:\n"
                    "- Connected via USB\n- Powered on (press Photo or Video button)")
                self.set_status("Not connected")
                return
            
            # Get camera info
            self.update_camera_info()
            
            self.connected = True
            self.status_label.config(text="● Connected", foreground="green")
            self.set_status("Connected to KeyMission 360")
            
            # Load files
            self.refresh_files()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {str(e)}")
            self.set_status("Connection error")
    
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
                                  capture_output=True, text=True, timeout=10)
            
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
        """Refresh file list from camera"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to camera first.")
            return
        
        self.set_status("Reading file list...")
        self.file_tree.delete(*self.file_tree.get_children())
        
        try:
            result = subprocess.run(["gphoto2", "--list-files"], 
                                  capture_output=True, text=True, timeout=30)
            
            lines = result.stdout.split('\n')
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
                        
                        self.file_tree.insert('', 'end', values=(name, size, date))
            
            self.set_status(f"Loaded {len(self.file_tree.get_children())} files")
            
        except Exception as e:
            self.set_status(f"Error reading files: {str(e)}")
    
    def download_selected(self):
        """Download selected files"""
        selected = self.file_tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select files to download.")
            return
        
        # Ask for destination
        dest = filedialog.askdirectory(title="Select Download Destination")
        if not dest:
            return
        
        # Get file numbers from selection
        files_to_download = []
        for item in selected:
            values = self.file_tree.item(item, 'values')
            name = values[0]
            # Find file number from tree index
            idx = self.file_tree.index(item) + 1
            files_to_download.append((idx, name))
        
        # Start download in thread
        self.download_thread = threading.Thread(
            target=self._download_files, 
            args=(files_to_download, dest)
        )
        self.download_thread.start()
    
    def download_all(self):
        """Download all files"""
        if not self.file_tree.get_children():
            messagebox.showinfo("No Files", "No files to download.")
            return
        
        dest = filedialog.askdirectory(title="Select Download Destination")
        if not dest:
            return
        
        self.download_thread = threading.Thread(
            target=self._download_all_files,
            args=(dest,)
        )
        self.download_thread.start()
    
    def _download_files(self, files, dest):
        """Download specific files (runs in thread)"""
        total = len(files)
        for i, (num, name) in enumerate(files, 1):
            self.set_status(f"Downloading {name} ({i}/{total})...")
            try:
                subprocess.run(
                    ["gphoto2", "--get-file", str(num), 
                     f"--filename={dest}/{name}"],
                    capture_output=True, timeout=300
                )
            except Exception as e:
                print(f"Error downloading {name}: {e}")
        
        self.set_status(f"Downloaded {total} files to {dest}")
        messagebox.showinfo("Download Complete", f"Downloaded {total} files.")
    
    def _download_all_files(self, dest):
        """Download all files (runs in thread)"""
        self.set_status("Downloading all files...")
        try:
            subprocess.run(
                ["gphoto2", "--get-all-files", f"--folder={dest}"],
                capture_output=True, timeout=600
            )
            self.set_status(f"All files downloaded to {dest}")
            messagebox.showinfo("Download Complete", "All files downloaded.")
        except Exception as e:
            self.set_status(f"Download error: {str(e)}")
    
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
        
        # Delete files
        for item in selected:
            idx = self.file_tree.index(item) + 1
            try:
                subprocess.run(["gphoto2", "--delete-file", str(idx)], 
                             capture_output=True, timeout=30)
            except Exception as e:
                print(f"Error deleting file: {e}")
        
        self.refresh_files()
        self.set_status("Files deleted")
    
    # --- Settings Methods ---
    
    def sync_datetime(self):
        """Sync camera time to system time"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to camera first.")
            return
        
        try:
            subprocess.run(["gphoto2", "--set-config", "datetime=now"], 
                         capture_output=True, timeout=10)
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
                         capture_output=True, timeout=10)
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
                         capture_output=True, timeout=10)
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
                         capture_output=True, timeout=10)
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
                         capture_output=True, timeout=10)
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
                             capture_output=True, timeout=10)
                subprocess.run(["gphoto2", "--set-config", 
                              f"/main/other/d340={pass_var.get()}"], 
                             capture_output=True, timeout=10)
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
                                  capture_output=True, text=True, timeout=10)
            
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
                                  capture_output=True, text=True, timeout=10)
            
            messagebox.showinfo("Storage Information", result.stdout)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get storage info: {str(e)}")
    
    def refresh_info(self):
        """Refresh info tab"""
        if not self.connected:
            return
        
        try:
            result = subprocess.run(["gphoto2", "--summary"], 
                                  capture_output=True, text=True, timeout=10)
            
            self.info_text.configure(state=tk.NORMAL)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, result.stdout)
            self.info_text.configure(state=tk.DISABLED)
            
        except Exception as e:
            print(f"Error refreshing info: {e}")
    
    # --- Menu Methods ---
    
    def show_settings(self):
        """Show application settings"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Application Settings")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        
        ttk.Label(dialog, text="Application Settings", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Download directory
        ttk.Label(dialog, text="Default Download Directory:").pack(anchor=tk.W, padx=20)
        dir_frame = ttk.Frame(dialog)
        dir_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        download_dir = tk.StringVar(value=str(Path.home() / "Pictures" / "KM360"))
        ttk.Entry(dir_frame, textvariable=download_dir).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        def browse_dir():
            d = filedialog.askdirectory()
            if d:
                download_dir.set(d)
        
        ttk.Button(dir_frame, text="Browse...", command=browse_dir).pack(side=tk.LEFT, padx=(5, 0))
        
        # Auto-sync time option
        auto_sync = tk.BooleanVar(value=False)
        ttk.Checkbutton(dialog, text="Auto-sync time on connect", 
                       variable=auto_sync).pack(anchor=tk.W, padx=20, pady=10)
        
        ttk.Button(dialog, text="Save", command=dialog.destroy).pack(pady=20)
    
    def show_download_manager(self):
        """Show download manager"""
        messagebox.showinfo("Download Manager", 
            "The Download Manager is integrated into the main window.\n\n"
            "Use the file browser on the left to select and download files.")
    
    def show_docs(self):
        """Show documentation"""
        try:
            with open("README.md", "r") as f:
                content = f.read()
            
            dialog = tk.Toplevel(self.root)
            dialog.title("Documentation")
            dialog.geometry("800x600")
            
            text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD)
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert(tk.END, content)
            text.configure(state=tk.DISABLED)
            
        except FileNotFoundError:
            messagebox.showinfo("Documentation", 
                "Documentation is available at:\n"
                "https://github.com/Innomen/KeyMission360Tools")
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About", 
            f"{APP_NAME}\n"
            f"Version {VERSION}\n\n"
            "A Linux replacement for the Nikon KeyMission 360/170 Utility.\n\n"
            "Features:\n"
            "- File download and management\n"
            "- Date/time synchronization\n"
            "- Camera settings configuration\n"
            "- SD card formatting\n\n"
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
                              capture_output=True, text=True, timeout=5)
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
                              capture_output=True, text=True, timeout=5)
        if "KeyMission 360" in result.stdout:
            print("  ✓ KeyMission 360 detected")
            # Get summary
            result = subprocess.run(["gphoto2", "--summary"], 
                                  capture_output=True, text=True, timeout=10)
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
    root.mainloop()


if __name__ == "__main__":
    main()
