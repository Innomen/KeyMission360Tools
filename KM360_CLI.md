# KeyMission 360 - Standalone CLI

A comprehensive, single-file command-line interface for the Nikon KeyMission 360 camera.

## Overview

`km360` is a standalone CLI tool that combines all functionality from the KeyMission 360 Tools suite into a single command with subcommands.

## Features

- **Camera Info** - Display USB and PTP device information
- **SD Card Format** - Format memory card via raw PTP commands
- **Time Sync** - Synchronize camera time to system time
- **File Management** - List and download files with resume/checksum support
- **USB Reset** - Reset USB port when camera times out
- **360° Viewer** - Interactive photo/video viewer
- **YouTube Export** - Inject 360° spherical metadata
- **WiFi Config** - Change camera WiFi settings
- **Camera Settings** - White balance, copyright, capture target
- **Desktop Install** - Add to application menu

## Installation

### Option 1: Run directly

```bash
# Make executable
chmod +x km360

# Run from current directory
./km360 --help
```

### Option 2: Install to PATH

```bash
# Copy to a directory in your PATH
sudo cp km360 /usr/local/bin/

# Now you can run from anywhere
km360 --help
```

## Requirements

### Core dependencies:
```bash
# gphoto2 for camera communication
sudo apt-get install gphoto2

# Python USB library for PTP commands
pip install libusb1
```

### Optional dependencies:
```bash
# For 360° viewer
pip install numpy pillow opencv-python

# For YouTube export
sudo apt-get install ffmpeg
# or: pip install spatialmedia
```

## Usage

### Quick Reference

```bash
# Camera information
km360 info

# Format SD card
km360 format              # With confirmation
km360 format --force      # Without confirmation

# Time synchronization
km360 time                # Sync to system time
km360 time --check        # Check current time only

# File management
km360 list                # List all files
km360 download --all ~/Photos     # Download all files
km360 download 5 ~/video.mp4      # Download specific file

# USB reset (when camera times out)
km360 reset

# 360° viewer
km360 viewer photo.jpg
km360 viewer video.mp4

# YouTube export (adds 360° metadata)
km360 youtube video.mp4           # Creates video_youtube.mp4
km360 youtube --in-place video.mp4  # Modify in-place
km360 youtube --batch ~/Videos/     # Process all videos

# WiFi configuration
km360 wifi --ssid MyCamera360
km360 wifi --password MyNewPass123
km360 wifi --channel 6

# Camera settings
km360 settings --show                    # Show all settings
km360 settings --whitebalance daylight   # Set white balance
km360 settings --copyright "© 2026 Me"   # Set copyright
km360 settings --target card             # Set capture target

# Desktop integration
km360 install             # Add to application menu
km360 install --remove    # Remove from menu

# GUI (if km360_gui.py exists)
km360 gui
```

### Detailed Help

Each command has its own help:

```bash
km360 info --help
km360 download --help
km360 youtube --help
# etc.
```

## Command Reference

### `km360 info`

Display detailed information about the connected camera via USB/PTP.

- USB device information (Vendor/Product IDs, bus, address)
- Device strings (manufacturer, product, serial)
- PTP communication endpoints
- Storage devices (internal memory, SD card)

### `km360 format`

Format the SD card using raw PTP commands.

**Options:**
- `--storage ID` - Format specific storage (hex, e.g., `0x00010001`)
- `--force` - Skip confirmation prompt (DANGEROUS)
- `--list` - List storage devices without formatting

### `km360 time`

Synchronize camera date/time to system time. The KeyMission 360 has no RTC battery and loses time when the battery is removed.

**Options:**
- `--check` - Only display current camera time without changing it

### `km360 list`

List all files on the camera with file numbers, names, and sizes.

### `km360 download`

Download files from camera with resume support and checksum verification.

**Options:**
- `--output PATH` - Output directory or file
- `--all` - Download all files
- `--retries N` - Max retry attempts (default: 3)
- `--no-verify` - Skip checksum verification
- `--no-metadata` - Skip YouTube 360° metadata injection for videos

**Examples:**
```bash
km360 download --all ~/Pictures/KM360
km360 download 5 ~/Videos/myvideo.mp4
km360 download 12 photo.jpg --output ~/Photos/
```

### `km360 reset`

Reset the USB port when the camera becomes unresponsive or times out.

**Options:**
- `--force` - Skip confirmation

### `km360 viewer`

Interactive 360° photo and video viewer with equirectangular-to-rectilinear projection.

**Controls:**
- Mouse drag - Look around
- Scroll - Zoom in/out
- Arrow keys / WASD - Look around
- +/- - Zoom
- Space - Play/pause (video)
- R - Reset view
- Q/Esc - Quit

### `km360 youtube`

Inject 360° spherical metadata into videos for YouTube upload. Does NOT re-encode video.

**Options:**
- `--output FILE` - Specify output filename
- `--batch` - Process all videos in directory
- `--in-place` - Modify files in-place (no `_youtube` suffix)

**Examples:**
```bash
km360 youtube video.mp4                    # Creates video_youtube.mp4
km360 youtube video.mp4 -o out.mp4         # Specify output name
km360 youtube --in-place video.mp4         # Modify in-place
km360 youtube --batch ~/Videos/KM360/      # Process folder
```

### `km360 wifi`

Configure camera WiFi settings.

**Options:**
- `--ssid NAME` - Set WiFi network name (SSID)
- `--password PASS` - Set WiFi password
- `--channel N` - Set WiFi channel (1-11)

### `km360 settings`

View and modify camera settings.

**Options:**
- `--show` - Show all current settings (default if no options)
- `--whitebalance MODE` - Set white balance (auto/daylight/fluorescent/tungsten)
- `--copyright TEXT` - Set copyright info
- `--target TYPE` - Set capture target (ram/card/sd)

### `km360 install`

Install a desktop entry to add KeyMission 360 to your application menu.

**Options:**
- `--remove` - Remove the desktop entry

## USB Permissions (Linux)

For non-root access, create a udev rule:

```bash
sudo tee /etc/udev/rules.d/99-keymission360.rules << 'EOF'
# Nikon KeyMission 360
SUBSYSTEM=="usb", ATTR{idVendor}=="04b0", ATTR{idProduct}=="019f", MODE="0666", GROUP="plugdev"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger
sudo usermod -a -G plugdev $USER
# Log out and back in for changes to take effect
```

## Troubleshooting

### "Camera not found"
- Ensure camera is connected via USB
- Make sure camera is powered on (press Photo or Video button)
- Try `km360 reset` to reset USB port
- Check USB permissions (see above)

### "gphoto2 not installed"
```bash
sudo apt-get install gphoto2
```

### "usb1 module not installed"
```bash
pip install libusb1
```

### "Could not claim interface"
- Another program may be using the camera
- Kill competing processes: `killall gphoto2 gvfs-gphoto2-volume-monitor`
- Use `km360 reset` to force release

## Differences from GUI Version

This CLI provides the same core functionality as `km360_gui.py` but in a terminal-friendly format:

| Feature | CLI | GUI |
|---------|-----|-----|
| Camera info | ✓ | ✓ |
| Format SD | ✓ | ✓ |
| Time sync | ✓ | ✓ |
| Download files | ✓ | ✓ (with progress bars) |
| USB reset | ✓ | ✓ |
| 360° viewer | ✓ | ✓ |
| YouTube export | ✓ | ✓ |
| WiFi config | ✓ | ✓ |
| Batch operations | ✓ | Partial |
| Drag-drop interface | - | ✓ |
| Native file dialogs | - | ✓ |

## License

MIT License - See LICENSE file

## Author

KeyMission 360 Tools Project
