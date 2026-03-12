#!/usr/bin/env python3
"""
KeyMission 360 Desktop Entry Installer
======================================

Installs the KeyMission 360 GUI to the system application menu (Start Menu).

Usage:
    python3 km360_install_desktop.py          # Interactive install
    python3 km360_install_desktop.py --remove # Remove from menu
    python3 km360_install_desktop.py --check  # Check if installed

This creates a .desktop file that allows launching the GUI from:
- GNOME/KDE/XFCE application menu
- Desktop launchers
- Alt+F2 run dialog

Author: KeyMission 360 Tools Project
License: MIT
"""

import argparse
import os
import sys
from pathlib import Path


def get_desktop_dirs():
    """Get desktop entry directories based on XDG spec"""
    # Get XDG directories
    xdg_data_home = os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')
    xdg_data_dirs = os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':')
    
    # User-local applications dir (preferred for user install)
    user_apps_dir = Path(xdg_data_home) / 'applications'
    
    # System-wide directories (requires sudo)
    system_apps_dirs = [Path(d) / 'applications' for d in xdg_data_dirs if d]
    
    return user_apps_dir, system_apps_dirs


def get_icon_dirs():
    """Get icon directories"""
    xdg_data_home = os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')
    
    user_icons_dir = Path(xdg_data_home) / 'icons' / 'hicolor' / '256x256' / 'apps'
    system_icons_dir = Path('/usr/share/icons/hicolor/256x256/apps')
    
    return user_icons_dir, system_icons_dir


def create_icon_png(icon_path):
    """Create a simple PNG icon for the application"""
    try:
        # Try to use PIL/Pillow if available
        from PIL import Image, ImageDraw
        
        # Create a 256x256 image with a gradient background
        img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw a circular camera-like icon
        # Outer circle (camera body)
        draw.ellipse([20, 40, 236, 216], fill='#1a1a2e', outline='#16213e', width=4)
        
        # Inner circle (lens)
        draw.ellipse([60, 80, 196, 176], fill='#0f3460', outline='#e94560', width=3)
        
        # Lens center
        draw.ellipse([100, 110, 156, 146], fill='#e94560')
        
        # Top button
        draw.rectangle([100, 25, 156, 45], fill='#16213e', outline='#0f3460', width=2)
        
        # 360° indicator
        draw.text((110, 125), "360", fill='white', anchor='mm')
        
        # Save
        img.save(icon_path)
        return True
        
    except ImportError:
        # PIL not available, try using ImageMagick convert
        try:
            import subprocess
            
            # Create a simple SVG and convert to PNG
            svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="256" height="256" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a2e"/>
      <stop offset="100%" style="stop-color:#16213e"/>
    </linearGradient>
  </defs>
  <circle cx="128" cy="128" r="108" fill="url(#bg)" stroke="#e94560" stroke-width="4"/>
  <circle cx="128" cy="128" r="68" fill="#0f3460" stroke="#e94560" stroke-width="2"/>
  <circle cx="128" cy="128" r="28" fill="#e94560"/>
  <rect x="100" y="25" width="56" height="20" rx="4" fill="#16213e"/>
  <text x="128" y="140" font-family="Arial" font-size="24" font-weight="bold" 
        fill="white" text-anchor="middle">360</text>
</svg>'''
            
            svg_path = icon_path.with_suffix('.svg')
            svg_path.write_text(svg_content)
            
            # Convert to PNG using ImageMagick or Inkscape
            result = subprocess.run(
                ['convert', str(svg_path), str(icon_path)],
                capture_output=True, timeout=30
            )
            
            if result.returncode != 0:
                # Try inkscape
                result = subprocess.run(
                    ['inkscape', str(svg_path), '-o', str(icon_path)],
                    capture_output=True, timeout=30
                )
            
            # Clean up SVG
            svg_path.unlink(missing_ok=True)
            
            return icon_path.exists()
            
        except Exception as e:
            print(f"Warning: Could not create icon: {e}")
            return False


def create_desktop_entry(desktop_path, icon_name=None, system_wide=False):
    """Create the .desktop file"""
    
    # Get the absolute path to the km360_gui.py script
    script_dir = Path(__file__).parent.absolute()
    gui_script = script_dir / 'km360_gui.py'
    
    if not gui_script.exists():
        print(f"Error: Could not find {gui_script}")
        print("Make sure you're running this from the KeyMission360Tools directory.")
        return False
    
    # Build the desktop entry content
    exec_line = f'python3 "{gui_script}"'
    
    desktop_content = f"""[Desktop Entry]
Name=KeyMission 360 Utility
Comment=Nikon KeyMission 360/170 Camera Manager for Linux
Exec={exec_line}
Type=Application
Terminal=false
Icon={icon_name or 'camera-video'}
Categories=Graphics;Photography;AudioVideo;Video;
Keywords=Camera;Nikon;360;Video;Photo;KeyMission;
StartupNotify=true
StartupWMClass=KeyMission 360 Linux Utility
MimeType=image/jpeg;image/png;video/mp4;video/quicktime;
"""

    try:
        # Ensure directory exists
        desktop_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the desktop file
        desktop_path.write_text(desktop_content)
        
        # Make executable
        desktop_path.chmod(0o755)
        
        return True
        
    except PermissionError:
        if system_wide:
            print("Error: Permission denied. Try running with sudo for system-wide install.")
        else:
            print("Error: Could not write to applications directory.")
        return False
    except Exception as e:
        print(f"Error creating desktop entry: {e}")
        return False


def install(system_wide=False):
    """Install the desktop entry"""
    user_apps_dir, system_apps_dirs = get_desktop_dirs()
    user_icons_dir, system_icons_dir = get_icon_dirs()
    
    if system_wide:
        desktop_path = system_apps_dirs[0] / 'km360-utility.desktop'
        icon_dir = system_icons_dir
    else:
        desktop_path = user_apps_dir / 'km360-utility.desktop'
        icon_dir = user_icons_dir
    
    print(f"KeyMission 360 Desktop Entry Installer")
    print(f"{'='*50}")
    print()
    
    # Check if already installed
    if desktop_path.exists():
        print(f"Desktop entry already exists at:")
        print(f"  {desktop_path}")
        response = input("\nReinstall? [y/N]: ").strip().lower()
        if response != 'y':
            print("Installation cancelled.")
            return
    
    # Create icon
    print("Creating application icon...")
    icon_dir.mkdir(parents=True, exist_ok=True)
    icon_path = icon_dir / 'km360-utility.png'
    
    icon_created = create_icon_png(icon_path)
    icon_name = 'km360-utility' if icon_created else 'camera-video'
    
    if icon_created:
        print(f"  ✓ Icon created: {icon_path}")
        
        # Update icon cache for system-wide installs
        if system_wide:
            try:
                import subprocess
                subprocess.run(['gtk-update-icon-cache', '-f', '-t', 
                              str(icon_dir.parent.parent)], 
                             capture_output=True, timeout=10)
            except:
                pass
    else:
        print("  ⚠ Using system default icon")
    
    # Create desktop entry
    print("\nCreating desktop entry...")
    if create_desktop_entry(desktop_path, icon_name, system_wide):
        print(f"  ✓ Desktop entry created: {desktop_path}")
    else:
        print("  ✗ Failed to create desktop entry")
        return
    
    print()
    print("="*50)
    print("Installation successful!")
    print()
    print("You can now launch the KeyMission 360 Utility from:")
    print("  • Application menu (search for 'KeyMission')")
    print("  • Activities overview (GNOME)")
    print("  • Alt+F2 run dialog")
    print()
    
    if not system_wide:
        print("To install system-wide for all users, run with --system:")
        print("  sudo python3 km360_install_desktop.py --system")
        print()


def remove(system_wide=False):
    """Remove the desktop entry"""
    user_apps_dir, system_apps_dirs = get_desktop_dirs()
    user_icons_dir, system_icons_dir = get_icon_dirs()
    
    if system_wide:
        desktop_path = system_apps_dirs[0] / 'km360-utility.desktop'
        icon_path = system_icons_dir / 'km360-utility.png'
    else:
        desktop_path = user_apps_dir / 'km360-utility.desktop'
        icon_path = user_icons_dir / 'km360-utility.png'
    
    print("Removing KeyMission 360 desktop entry...")
    print()
    
    removed = False
    
    if desktop_path.exists():
        try:
            desktop_path.unlink()
            print(f"  ✓ Removed: {desktop_path}")
            removed = True
        except PermissionError:
            print(f"  ✗ Permission denied: {desktop_path}")
            if system_wide:
                print("    Try running with sudo.")
        except Exception as e:
            print(f"  ✗ Error removing {desktop_path}: {e}")
    else:
        print(f"  - Not found: {desktop_path}")
    
    if icon_path.exists():
        try:
            icon_path.unlink()
            print(f"  ✓ Removed: {icon_path}")
        except Exception as e:
            print(f"  ✗ Error removing icon: {e}")
    
    if removed:
        print()
        print("Desktop entry removed successfully.")
    else:
        print()
        print("Nothing to remove (desktop entry not found).")


def check_status():
    """Check if desktop entry is installed"""
    user_apps_dir, system_apps_dirs = get_desktop_dirs()
    
    user_desktop = user_apps_dir / 'km360-utility.desktop'
    system_desktop = system_apps_dirs[0] / 'km360-utility.desktop' if system_apps_dirs else None
    
    print("KeyMission 360 Desktop Entry Status")
    print("="*50)
    print()
    
    if user_desktop.exists():
        print(f"✓ User install: {user_desktop}")
        # Try to read and display the Exec line
        try:
            content = user_desktop.read_text()
            for line in content.split('\n'):
                if line.startswith('Exec='):
                    print(f"  Command: {line[5:]}")
                    break
        except:
            pass
    else:
        print("✗ User install: Not found")
    
    print()
    
    if system_desktop and system_desktop.exists():
        print(f"✓ System install: {system_desktop}")
    else:
        print("✗ System install: Not found")
    
    print()
    
    # Check if desktop files are actually enabled
    user_apps_dir.mkdir(parents=True, exist_ok=True)
    if user_apps_dir.exists():
        print(f"User applications directory: {user_apps_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="Install KeyMission 360 Utility to the application menu",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s              # Interactive install to user menu
  %(prog)s --system     # Install system-wide (requires sudo)
  %(prog)s --remove     # Remove from user menu
  %(prog)s --check      # Check installation status

Notes:
  - User install goes to: ~/.local/share/applications/
  - System install goes to: /usr/share/applications/
  - The desktop entry will launch: python3 km360_gui.py
"""
    )
    
    parser.add_argument('--system', '-s', action='store_true',
                       help='Install system-wide (requires sudo)')
    parser.add_argument('--remove', '-r', action='store_true',
                       help='Remove the desktop entry')
    parser.add_argument('--check', '-c', action='store_true',
                       help='Check installation status')
    parser.add_argument('--force', '-f', action='store_true',
                       help='Force reinstall without prompting')
    
    args = parser.parse_args()
    
    if args.check:
        check_status()
    elif args.remove:
        remove(system_wide=args.system)
    else:
        install(system_wide=args.system)


if __name__ == "__main__":
    main()
