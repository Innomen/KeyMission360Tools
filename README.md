# KeyMission 360 Tools

<img width="1207" height="871" alt="Screenshot_20260310_141707" src="https://github.com/user-attachments/assets/ee560110-d94e-4c74-842e-96ed1b80ba7b" />

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A comprehensive toolkit for the **Nikon KeyMission 360** camera, providing direct USB/PTP communication, SD card formatting, camera control via gphoto2, and complete device configuration.

## 🎯 Purpose

The Nikon KeyMission 360 has limited physical controls (only 2 buttons) and can be difficult to manage when the SD card becomes corrupted or when you need to change advanced settings. This toolkit provides:

- **SD Card Formatting** - Direct PTP format command bypassing camera menus
- **Date/Time Sync** - Fix incorrect timestamps on your photos
- **Complete Camera Control** - Access all 80+ camera settings via gphoto2
- **File Management** - Download/upload/delete files
- **WiFi Configuration** - Change camera's WiFi password and IP settings
- **Raw PTP Commands** - Full low-level camera access

## 📁 Repository Contents

| File | Description |
|------|-------------|
| `km360_gui.py` | **🆕 MAIN GUI APPLICATION** - Complete camera management interface |
| `km360_formatter.py` | Format SD card via raw PTP commands |
| `km360_set_time.py` | **Sync camera time to system time** (fixes 2016 timestamp issue) |
| `km360_info.py` | Display camera information and PTP endpoints |
| `manual_format.sh` | Format SD card manually (without camera) |
| `GPHOTO2_COMMANDS.md` | Complete gphoto2 command reference |
| `RESEARCH.md` | Technical PTP protocol documentation |

## 🚀 Quick Start

### Prerequisites

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install gphoto2 (for advanced features)
# Ubuntu/Debian:
sudo apt-get install gphoto2

# Fedora:
sudo dnf install gphoto2

# macOS:
brew install gphoto2
```

### USB Permissions (Linux)

Create a udev rule for non-root access:

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

## 📖 Usage

### 1. Launch the GUI (Recommended)

The GUI provides an easy-to-use interface for all camera functions:

```bash
python3 km360_gui.py
```

Features:
- 📁 **File Browser** - Browse and download photos/videos
- ⚡ **Quick Actions** - Sync time, format SD, WiFi config
- ⚙️ **Camera Settings** - White balance, movie mode, etc.
- ℹ️ **Camera Info** - Battery, storage, firmware version
- 👁️ **360° Viewer** - Interactive photo/video viewer
- ▶️ **YouTube Export** - Inject 360° metadata for upload

### 2. Fix Date/Time (Most Important!)

**The KeyMission 360 has NO RTC battery!** When the battery dies or is removed, the camera forgets the date/time and reverts to 2016. This causes all your photos to have wrong timestamps.

```bash
# Sync camera time to your computer's time
python3 km360_set_time.py

# Check current camera time without changing
python3 km360_set_time.py --check

# Quiet mode (minimal output)
python3 km360_set_time.py --quiet
```

**Run this every time you:**
- Insert a fresh battery
- See photos with 2015/2016 timestamps
- Haven't used the camera in a while

### 2. Format SD Card (Python Tool)

The most reliable way to format when the camera's interface isn't working:

```bash
# Auto-detect and format
python3 km360_formatter.py

# List storage devices only
python3 km360_formatter.py --list

# Format without confirmation (DANGEROUS)
python3 km360_formatter.py --force
```

### 3. Camera Information

```bash
python3 km360_info.py
```

### 3. gphoto2 Commands

The camera exposes 80+ settings via gphoto2. See [GPHOTO2_COMMANDS.md](GPHOTO2_COMMANDS.md) for the complete reference.

#### Quick Examples:

```bash
# FIX DATE/TIME FIRST (camera has no RTC battery!)
python3 km360_set_time.py
# OR
gphoto2 --set-config datetime=now

# Start/stop video recording
gphoto2 --set-config movie=1  # Start
gphoto2 --set-config movie=0  # Stop

# Change WiFi password
gphoto2 --set-config /main/other/d340=MyNewPassword

# Change camera name (SSID)
gphoto2 --set-config /main/other/d338=MyCamera360

# Set copyright info in photos
gphoto2 --set-config /main/other/501f="© 2026 Your Name"

# Download all photos
gphoto2 --get-all-files

# Take a photo
gphoto2 --capture-image

# List all files
gphoto2 --list-files
```

## 🔧 All Available Settings

### Actions (Triggers)
- `bulb` - Long exposure mode
- `autofocusdrive` - Trigger autofocus
- `movie` - Start/stop video recording
- `viewfinder` - Enable live view
- `opcode` - Send raw PTP commands

### Settings (Read/Write)
- `datetime` - Camera date/time (use `now` for current time)
- `capturetarget` - Save to `Internal RAM` or `Memory card`
- `autofocus` - On/Off
- `whitebalance` - Automatic, Daylight, Fluorescent, Tungsten
- `movielooplength` - 5, 10, 30, 60 seconds (likely for loop recording/dashcam mode buffer)
- `liveviewafmode` - Face-priority AF or Wide-area AF
- `thumbsize` - normal or large
- `fastfs` - Fast filesystem toggle

### Image Settings (Read-Only)
- `iso` - ISO 100-25600
- `exposurecompensation` - -2 to +2 stops
- `expprogram` - M, P, A, S, Auto modes
- `shutterspeed2` - 30s to 1/32000

### Status (Read-Only)
- `batterylevel` - Battery percentage
- `availableshots` - Number of photos remaining
- `serialnumber` - Camera serial number
- `deviceversion` - Firmware version

### Nikon Vendor Extensions (Writable!)
- `d304` - Movie Capture Mode (0-3) - Unknown values: likely Standard, Loop, Timelapse, Superlapse
- `d0a0` - Movie Screen Size (10, 20, 40, 80, 90)
- `d0aa` - Wind Noise Reduction (0/1)
- `d338` - Camera Name/SSID (text)
- `d340` - WiFi Password (text!)
- `d341` - WiFi Channel (1-11)
- `d342` - IP Address (text)
- `d343` - Subnet Mask (text)
- `d323` - Movie Loop Length (50, 100, 300, 600)
- `501f` - Copyright Info (text)

## 🛠️ Alternative: Manual SD Card Format

If you prefer to format the SD card without the camera:

```bash
# Find your SD card (BE CAREFUL!)
lsblk

# Example: /dev/sdc
DEVICE="/dev/sdc"

# Unmount
sudo umount ${DEVICE}* 2>/dev/null

# Create partition table and FAT32 partition
sudo parted -s $DEVICE mklabel msdos
sudo parted -s $DEVICE mkpart primary fat32 1MiB 100%
sudo partprobe $DEVICE

# Format with optimal settings for video
sudo mkfs.vfat -F 32 -s 64 -n "KM360" ${DEVICE}1
```

Or use the included script:
```bash
./manual_format.sh
```

## ⚠️ Safety Notes

- **Formatting erases all data** - The formatter has a confirmation prompt
- **Quick format only** - Data may be recoverable with specialized tools
- **Battery level** - Ensure camera has charge before formatting
- **WiFi password** - Changing `d340` will affect the SnapBridge app connection

## 📊 Camera Specifications

| Property | Value |
|----------|-------|
| USB Vendor ID | 0x04B0 (Nikon Corp.) |
| USB Product ID | 0x019F |
| Firmware | KeyMission 360 Ver.1.3 |
| PTP Standard | PIMA 15740 |
| Storage IDs | 0x00000001 (Internal), 0x00010001 (SD Card) |
| Video Resolutions | 4K/24fps, 1080p/60fps, etc. |
| Photo Resolution | 7744 × 3872 (30 MP) |

## 🔬 Technical Details

The camera supports:
- **File Download, Deletion, Upload**
- **Generic Image Capture**
- **Nikon Capture 3**
- **Live View**
- **Movie Recording**

The raw PTP formatter uses:
- `0x1002` - OpenSession
- `0x1004` - GetStorageIDs
- `0x100F` - FormatStore (the magic command)

See [RESEARCH.md](RESEARCH.md) for complete protocol documentation.

## 🐛 Troubleshooting

### "Camera not found"
- Ensure camera is connected via USB
- Make sure camera is powered on (press Photo or Video button)
- Try unplugging and reconnecting USB
- Check USB permissions (udev rules)

### "Could not claim interface"
- Another program may be using the camera
- Kill competing processes: `killall gphoto2 gvfs-gphoto2-volume-monitor`

### "Invalid Storage ID"
- Use `--list` to see current storage IDs
- Try unplugging and reconnecting

### Date/time reverts to 2016
- The camera has no RTC battery
- **Use the time sync tool:** `python3 km360_set_time.py`
- Or manually: `gphoto2 --set-config datetime=now`

## 📚 Further Reading

- [GPHOTO2_COMMANDS.md](GPHOTO2_COMMANDS.md) - Complete command reference
- [RESEARCH.md](RESEARCH.md) - PTP protocol reverse engineering
- [PTP Specification](http://www.ntfs.com/img/15740-3.pdf) - PIMA 15740 spec
- [libgphoto2](https://github.com/gphoto/libgphoto2) - gphoto2 source

## 📄 License

MIT License - See [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- [libgphoto2](https://github.com/gphoto/libgphoto2) team for PTP support
- Nikon for documented PTP protocols
- The KeyMission 360 community for testing

---

**Disclaimer**: This tool is not affiliated with or endorsed by Nikon Corporation. Use at your own risk.
