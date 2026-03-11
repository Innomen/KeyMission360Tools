# Quick Start Guide

## 1-Minute Setup

```bash
# Install dependencies
pip install libusb1

# Launch the GUI (recommended)
python3 km360_gui.py

# Or use command-line tools:

# Format SD card
python3 km360_formatter.py

# Sync camera time (fixes 2016 timestamp issue)
python3 km360_set_time.py

# Download files reliably
python3 km360_download.py --all ~/Pictures/KM360/
```

## Common Commands

| Command | Description |
|---------|-------------|
| `python3 km360_gui.py` | **Launch GUI application** |
| `python3 km360_formatter.py` | Format SD card with auto-detect |
| `python3 km360_formatter.py --list` | List storage devices |
| `python3 km360_set_time.py` | Sync camera time to system |
| `python3 km360_download.py <num> <path>` | Download file with resume/checksum |
| `python3 km360_download.py --all <dir>` | Download all files |
| `python3 km360_usb_reset.py` | Reset USB port (no unplugging) |
| `python3 km360_info.py` | Show camera information |

## If You Get Permission Errors

```bash
# Temporary (until reboot)
sudo chmod 666 /dev/bus/usb/XXX/YYY

# Permanent (recommended)
sudo cp 99-keymission360.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
```

## Finding Your Camera's USB Path

```bash
lsusb | grep Nikon
# Output: Bus 003 Device 015: ID 04b0:019f Nikon Corp. NIKON KeyMission 360
```

## Emergency: Format Card Without Camera

If the camera won't connect or you don't have USB access:

```bash
# Linux
sudo mkfs.vfat -F 32 -s 64 -n "KM360" /dev/sdc1

# macOS  
diskutil eraseDisk FAT32 KM360 MBRFormat /dev/disk2

# Windows Command Prompt (Admin)
format F: /FS:FAT32 /V:KM360
```

## Troubleshooting

**"Camera not found" or timeout errors**
- Use USB Reset (no unplugging required):
  ```bash
  python3 km360_usb_reset.py
  ```
- Or click "🔄 Reset USB" button in GUI
- Unplug and reconnect USB (if reset fails)
- Check camera is powered on

**"Could not claim interface"**
```bash
killall gphoto2 gvfs-gphoto2-volume-monitor
python3 km360_usb_reset.py
```

**"Invalid Storage ID"**
```bash
python3 km360_formatter.py --list
# Then use correct ID: python3 km360_formatter.py --storage 0x00010001
```

**Downloads failing or incomplete**
```bash
# Use the reliable download tool
python3 km360_download.py 5 ~/Videos/myvideo.mp4

# It will auto-retry and verify checksums
```
