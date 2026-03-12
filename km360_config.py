#!/usr/bin/env python3
"""
KeyMission 360 Configuration & Native Dialogs
=============================================

Provides:
- Configuration persistence (JSON-based)
- Native GTK file choosers with Places sidebar
- Last used directory memory

Author: KeyMission 360 Tools Project
License: MIT
"""

import json
import os
from pathlib import Path

# Config file location
CONFIG_DIR = Path.home() / '.config' / 'km360'
CONFIG_FILE = CONFIG_DIR / 'config.json'

# Default configuration
DEFAULT_CONFIG = {
    'last_download_dir': str(Path.home() / 'Pictures' / 'KM360'),
    'delete_after_download': False,
    'verify_checksums': True,
    'window_geometry': None,
    'preferred_file_dialog': 'auto',  # 'auto', 'gtk', 'tk'
    'last_usb_port': None,  # 'bus:addr' format, e.g., '001:015'
    'auto_sync_time': False,
}


def get_config_dir():
    """Get or create the configuration directory"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config():
    """Load configuration from file"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged = DEFAULT_CONFIG.copy()
                merged.update(config)
                return merged
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load config: {e}")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """Save configuration to file"""
    try:
        get_config_dir()
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except IOError as e:
        print(f"Warning: Could not save config: {e}")
        return False


def get_last_download_dir():
    """Get the last used download directory"""
    config = load_config()
    path = Path(config.get('last_download_dir', DEFAULT_CONFIG['last_download_dir']))
    if path.exists() and path.is_dir():
        return str(path)
    # Fallback to default if saved path no longer exists
    return str(Path.home() / 'Pictures')


def set_last_download_dir(path):
    """Set the last used download directory"""
    config = load_config()
    config['last_download_dir'] = str(path)
    save_config(config)


def get_config_value(key, default=None):
    """Get a specific config value"""
    config = load_config()
    return config.get(key, default)


def set_config_value(key, value):
    """Set a specific config value"""
    config = load_config()
    config[key] = value
    save_config(config)


# =============================================================================
# Native File Dialogs with Places Support
# =============================================================================

class FileDialogProvider:
    """Abstract base for file dialog providers"""
    
    def ask_directory(self, title="Select Folder", initialdir=None):
        """Ask for a directory - returns path or None"""
        raise NotImplementedError
    
    def ask_saveas_filename(self, title="Save As", initialdir=None, 
                            initialfile=None, defaultextension=None,
                            filetypes=None):
        """Ask for save filename - returns path or None"""
        raise NotImplementedError
    
    def ask_open_filename(self, title="Open File", initialdir=None,
                          filetypes=None):
        """Ask for open filename - returns path or None"""
        raise NotImplementedError


class TkFileDialog(FileDialogProvider):
    """Standard Tkinter file dialogs (fallback)"""
    
    def __init__(self, parent=None):
        self.parent = parent
    
    def ask_directory(self, title="Select Folder", initialdir=None):
        import tkinter as tk
        from tkinter import filedialog
        
        root = self.parent
        if root is None:
            root = tk.Tk()
            root.withdraw()
        
        result = filedialog.askdirectory(
            parent=root,
            title=title,
            initialdir=initialdir or get_last_download_dir()
        )
        
        # Save the selected directory
        if result:
            set_last_download_dir(result)
        
        return result if result else None
    
    def ask_saveas_filename(self, title="Save As", initialdir=None,
                            initialfile=None, defaultextension=None,
                            filetypes=None):
        import tkinter as tk
        from tkinter import filedialog
        
        root = self.parent
        if root is None:
            root = tk.Tk()
            root.withdraw()
        
        result = filedialog.asksaveasfilename(
            parent=root,
            title=title,
            initialdir=initialdir or get_last_download_dir(),
            initialfile=initialfile,
            defaultextension=defaultextension,
            filetypes=filetypes or [("All files", "*.*")]
        )
        
        if result:
            set_last_download_dir(Path(result).parent)
        
        return result if result else None
    
    def ask_open_filename(self, title="Open File", initialdir=None,
                          filetypes=None):
        import tkinter as tk
        from tkinter import filedialog
        
        root = self.parent
        if root is None:
            root = tk.Tk()
            root.withdraw()
        
        result = filedialog.askopenfilename(
            parent=root,
            title=title,
            initialdir=initialdir or get_last_download_dir(),
            filetypes=filetypes or [("All files", "*.*")]
        )
        
        if result:
            set_last_download_dir(Path(result).parent)
        
        return result if result else None


class GtkFileDialog(FileDialogProvider):
    """Native GTK file dialogs with Places sidebar"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.gtk_available = self._check_gtk()
    
    def _check_gtk(self):
        """Check if GTK is available"""
        try:
            import gi
            gi.require_version('Gtk', '3.0')
            from gi.repository import Gtk, Gio, GLib
            self.Gtk = Gtk
            self.Gio = Gio
            self.GLib = GLib
            return True
        except (ImportError, ValueError):
            return False
    
    def _add_shortcuts(self, dialog, Gtk, Gio):
        """Add common shortcuts to the places sidebar"""
        # Add common locations
        shortcuts = [
            (Path.home(), "Home"),
            (Path.home() / 'Desktop', "Desktop"),
            (Path.home() / 'Documents', "Documents"),
            (Path.home() / 'Pictures', "Pictures"),
            (Path.home() / 'Videos', "Videos"),
            (Path.home() / 'Downloads', "Downloads"),
        ]
        
        for path, name in shortcuts:
            if path.exists():
                try:
                    file = Gio.File.new_for_path(str(path))
                    dialog.add_shortcut_folder(str(path))
                except Exception:
                    pass
        
        # Try to add mounted drives/removable media
        try:
            volume_monitor = Gio.VolumeMonitor.get()
            for mount in volume_monitor.get_mounts():
                try:
                    path = mount.get_root().get_path()
                    if path and Path(path).exists():
                        dialog.add_shortcut_folder(path)
                except Exception:
                    pass
        except Exception:
            pass
    
    def ask_directory(self, title="Select Folder", initialdir=None):
        if not self.gtk_available:
            # Fallback to Tk
            fallback = TkFileDialog(self.parent)
            return fallback.ask_directory(title, initialdir)
        
        Gtk = self.Gtk
        Gio = self.Gio
        
        initialdir = initialdir or get_last_download_dir()
        
        # Use the new GTK3+ native file chooser dialog
        dialog = Gtk.FileChooserDialog(
            title=title,
            parent=None,  # Can't easily pass tk parent to gtk
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
        )
        
        # Set initial folder
        if initialdir and Path(initialdir).exists():
            dialog.set_current_folder(initialdir)
        
        # Add shortcuts/places
        self._add_shortcuts(dialog, Gtk, Gio)
        
        # Enable multiple selection (though we only use one)
        dialog.set_select_multiple(False)
        
        # Show the dialog and get response
        response = dialog.run()
        result = None
        
        if response == Gtk.ResponseType.OK:
            result = dialog.get_filename()
        
        dialog.destroy()
        
        # Process GTK events to close the dialog
        while Gtk.events_pending():
            Gtk.main_iteration()
        
        # Force tkinter parent window to refresh (fixes black window issue)
        if self.parent:
            try:
                self.parent.update_idletasks()
                self.parent.update()
            except:
                pass
        
        # Save the selected directory
        if result:
            set_last_download_dir(result)
        
        return result
    
    def ask_saveas_filename(self, title="Save As", initialdir=None,
                            initialfile=None, defaultextension=None,
                            filetypes=None):
        if not self.gtk_available:
            fallback = TkFileDialog(self.parent)
            return fallback.ask_saveas_filename(title, initialdir, 
                                                initialfile, defaultextension,
                                                filetypes)
        
        Gtk = self.Gtk
        Gio = self.Gio
        
        initialdir = initialdir or get_last_download_dir()
        
        dialog = Gtk.FileChooserDialog(
            title=title,
            parent=None,
            action=Gtk.FileChooserAction.SAVE,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_SAVE, Gtk.ResponseType.OK
            )
        )
        
        # Set initial folder and filename
        if initialdir and Path(initialdir).exists():
            dialog.set_current_folder(initialdir)
        
        if initialfile:
            dialog.set_current_name(initialfile)
        
        # Add shortcuts/places
        self._add_shortcuts(dialog, Gtk, Gio)
        
        # Set do-overwrite confirmation
        dialog.set_do_overwrite_confirmation(True)
        
        # Add file filters if provided
        if filetypes:
            for label, pattern in filetypes:
                filter_pattern = Gtk.FileFilter()
                filter_pattern.set_name(label)
                # Handle multiple patterns like "*.mp4 *.mov"
                for p in pattern.split():
                    filter_pattern.add_pattern(p.strip())
                dialog.add_filter(filter_pattern)
            
            # Add "All files" filter
            all_filter = Gtk.FileFilter()
            all_filter.set_name("All files")
            all_filter.add_pattern("*")
            dialog.add_filter(all_filter)
        
        response = dialog.run()
        result = None
        
        if response == Gtk.ResponseType.OK:
            result = dialog.get_filename()
        
        dialog.destroy()
        
        while Gtk.events_pending():
            Gtk.main_iteration()
        
        # Force tkinter parent window to refresh (fixes black window issue)
        if self.parent:
            try:
                self.parent.update_idletasks()
                self.parent.update()
            except:
                pass
        
        if result:
            set_last_download_dir(Path(result).parent)
        
        return result
    
    def ask_open_filename(self, title="Open File", initialdir=None,
                          filetypes=None):
        if not self.gtk_available:
            fallback = TkFileDialog(self.parent)
            return fallback.ask_open_filename(title, initialdir, filetypes)
        
        Gtk = self.Gtk
        Gio = self.Gio
        
        initialdir = initialdir or get_last_download_dir()
        
        dialog = Gtk.FileChooserDialog(
            title=title,
            parent=None,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
        )
        
        if initialdir and Path(initialdir).exists():
            dialog.set_current_folder(initialdir)
        
        self._add_shortcuts(dialog, Gtk, Gio)
        
        # Add file filters
        if filetypes:
            for label, pattern in filetypes:
                filter_pattern = Gtk.FileFilter()
                filter_pattern.set_name(label)
                for p in pattern.split():
                    filter_pattern.add_pattern(p.strip())
                dialog.add_filter(filter_pattern)
            
            all_filter = Gtk.FileFilter()
            all_filter.set_name("All files")
            all_filter.add_pattern("*")
            dialog.add_filter(all_filter)
        
        response = dialog.run()
        result = None
        
        if response == Gtk.ResponseType.OK:
            result = dialog.get_filename()
        
        dialog.destroy()
        
        while Gtk.events_pending():
            Gtk.main_iteration()
        
        # Force tkinter parent window to refresh (fixes black window issue)
        if self.parent:
            try:
                self.parent.update_idletasks()
                self.parent.update()
            except:
                pass
        
        if result:
            set_last_download_dir(Path(result).parent)
        
        return result


class KdeFileDialog(FileDialogProvider):
    """Native KDE file dialogs using kdialog"""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.kdialog_available = self._check_kdialog()
    
    def _check_kdialog(self):
        """Check if kdialog is available"""
        import shutil
        return shutil.which('kdialog') is not None
    
    def _run_kdialog(self, args):
        """Run kdialog and return result"""
        import subprocess
        try:
            result = subprocess.run(
                ['kdialog'] + args,
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None
    
    def ask_directory(self, title="Select Folder", initialdir=None):
        if not self.kdialog_available:
            fallback = TkFileDialog(self.parent)
            return fallback.ask_directory(title, initialdir)
        
        initialdir = initialdir or get_last_download_dir()
        
        args = ['--getexistingdirectory', initialdir, '--title', title]
        result = self._run_kdialog(args)
        
        if result:
            set_last_download_dir(result)
        
        return result
    
    def ask_saveas_filename(self, title="Save As", initialdir=None,
                            initialfile=None, defaultextension=None,
                            filetypes=None):
        if not self.kdialog_available:
            fallback = TkFileDialog(self.parent)
            return fallback.ask_saveas_filename(title, initialdir,
                                                initialfile, defaultextension,
                                                filetypes)
        
        initialdir = initialdir or get_last_download_dir()
        
        args = ['--getsavefilename', initialdir, '--title', title]
        if initialfile:
            args.extend(['--default', initialfile])
        
        result = self._run_kdialog(args)
        
        if result:
            set_last_download_dir(Path(result).parent)
        
        return result
    
    def ask_open_filename(self, title="Open File", initialdir=None,
                          filetypes=None):
        if not self.kdialog_available:
            fallback = TkFileDialog(self.parent)
            return fallback.ask_open_filename(title, initialdir, filetypes)
        
        initialdir = initialdir or get_last_download_dir()
        
        # Build filter string for kdialog
        filter_str = ""
        if filetypes:
            patterns = []
            for label, pattern in filetypes:
                patterns.append(pattern)
            filter_str = " ".join(patterns)
        
        start_dir = initialdir
        if filter_str:
            start_dir = f"{initialdir} {filter_str}"
        
        args = ['--getopenfilename', start_dir, '--title', title]
        result = self._run_kdialog(args)
        
        if result:
            set_last_download_dir(Path(result).parent)
        
        return result


def get_file_dialog(parent=None, prefer=None):
    """
    Get the best available file dialog provider.
    
    Args:
        parent: Tkinter parent window (if any)
        prefer: Force a specific provider ('gtk', 'kde', 'tk', or None for auto)
    
    Returns:
        FileDialogProvider instance
    """
    config = load_config()
    preferred = prefer or config.get('preferred_file_dialog', 'auto')
    
    # Check desktop environment
    desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').upper()
    session = os.environ.get('DESKTOP_SESSION', '').lower()
    
    # Determine order of preference
    if preferred == 'gtk':
        order = [GtkFileDialog, KdeFileDialog, TkFileDialog]
    elif preferred == 'kde':
        order = [KdeFileDialog, GtkFileDialog, TkFileDialog]
    elif preferred == 'tk':
        order = [TkFileDialog]
    else:
        # Auto-detect based on desktop
        if 'KDE' in desktop or session in ['kde', 'plasma']:
            order = [KdeFileDialog, GtkFileDialog, TkFileDialog]
        elif any(d in desktop for d in ['GNOME', 'UNITY', 'MATE', 'XFCE', 'CINNAMON', 'BUDGIE', 'PANTHEON']):
            order = [GtkFileDialog, KdeFileDialog, TkFileDialog]
        else:
            # Try GTK first (most common), then KDE, then Tk
            order = [GtkFileDialog, KdeFileDialog, TkFileDialog]
    
    # Try each provider
    for provider_class in order:
        try:
            provider = provider_class(parent)
            # Check if it's actually available
            if hasattr(provider, 'gtk_available') and not provider.gtk_available:
                continue
            if hasattr(provider, 'kdialog_available') and not provider.kdialog_available:
                continue
            return provider
        except Exception:
            continue
    
    # Ultimate fallback
    return TkFileDialog(parent)


# Convenience functions for direct use
def ask_directory(title="Select Folder", initialdir=None, parent=None):
    """Ask user to select a directory - returns path or None"""
    dialog = get_file_dialog(parent)
    return dialog.ask_directory(title, initialdir)


def ask_saveas_filename(title="Save As", initialdir=None,
                        initialfile=None, defaultextension=None,
                        filetypes=None, parent=None):
    """Ask user for a filename to save as - returns path or None"""
    dialog = get_file_dialog(parent)
    return dialog.ask_saveas_filename(title, initialdir, initialfile,
                                      defaultextension, filetypes)


def ask_open_filename(title="Open File", initialdir=None,
                      filetypes=None, parent=None):
    """Ask user for a file to open - returns path or None"""
    dialog = get_file_dialog(parent)
    return dialog.ask_open_filename(title, initialdir, filetypes)


# =============================================================================
# Legacy compatibility
# =============================================================================

# Make this module compatible with direct import of functions
if __name__ == "__main__":
    # Test mode
    print("KeyMission 360 Configuration & Native Dialogs")
    print("=" * 50)
    print()
    
    config = load_config()
    print(f"Config file: {CONFIG_FILE}")
    print(f"Config loaded: {config}")
    print()
    
    print("Testing file dialog provider...")
    dialog = get_file_dialog()
    print(f"Provider: {type(dialog).__name__}")
    print()
    
    print("Available functions:")
    print("  - ask_directory(title, initialdir, parent)")
    print("  - ask_saveas_filename(...)")
    print("  - ask_open_filename(...)")
    print("  - load_config()")
    print("  - save_config(config)")
    print("  - get_last_download_dir()")
    print("  - set_last_download_dir(path)")
