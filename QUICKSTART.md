# Quick Start Guide

## 1-Minute Setup

```bash
# Install dependencies
pip install libusb1

# Run formatter (requires confirmation)
python km360_formatter.py

# Or list storage devices first
python km360_formatter.py --list
```

## Common Commands

| Command | Description |
|---------|-------------|
| `python km360_formatter.py` | Format with auto-detect |
| `python km360_formatter.py --list` | List storage devices |
| `python km360_formatter.py --force` | Format without confirmation |
| `python km360_info.py` | Show camera information |
| `sudo ./manual_format.sh` | Format card without camera |

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

**"Camera not found"**
- Unplug and reconnect USB
- Check camera is in PTP mode

**"Could not claim interface"**
```bash
killall gphoto2 gvfs-gphoto2-volume-monitor
```

**"Invalid Storage ID"**
```bash
python km360_formatter.py --list
# Then use correct ID: python km360_formatter.py --storage 0x00010001
```
