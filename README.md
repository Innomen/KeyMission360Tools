# KeyMission 360 Formatter

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python tool to format the SD card of a **Nikon KeyMission 360** camera via USB using raw PTP (Picture Transfer Protocol) commands.

## 🎯 Purpose

The Nikon KeyMission 360 has a known issue where the SD card can become corrupted or show as "unformatted" through the camera's interface. This tool allows you to format the memory card directly via USB, bypassing the camera's limited button interface.

## ⚡ Features

- ✨ **Direct USB Communication** - Uses raw PTP protocol over USB bulk endpoints
- 🔍 **Auto-Detection** - Automatically finds the camera and identifies storage devices
- 🛡️ **Safety First** - Confirmation prompt before formatting (unless `--force` is used)
- 📋 **Storage Listing** - Can list storage devices without formatting
- 🔧 **Manual Storage Selection** - Override auto-detection with specific storage IDs

## 📋 Requirements

- Python 3.8 or higher
- USB access permissions (see Installation)
- Nikon KeyMission 360 camera connected via USB

## 🚀 Installation

### 1. Clone or Download

```bash
git clone https://github.com/yourusername/KeyMission360Formatter.git
cd KeyMission360Formatter
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set USB Permissions (Linux)

Create a udev rule to allow non-root access:

```bash
sudo tee /etc/udev/rules.d/99-keymission360.rules << 'EOF'
# Nikon KeyMission 360
SUBSYSTEM=="usb", ATTR{idVendor}=="04b0", ATTR{idProduct}=="019f", MODE="0666", GROUP="plugdev"
EOF

# Reload rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then add your user to the `plugdev` group:
```bash
sudo usermod -a -G plugdev $USER
# Log out and back in for changes to take effect
```

## 📖 Usage

### Basic Usage

Format the memory card with auto-detection:

```bash
python km360_formatter.py
```

### List Storage Devices

Just see what storage devices are available:

```bash
python km360_formatter.py --list
```

Output:
```
============================================================
Nikon KeyMission 360 Memory Card Formatter
============================================================

[✓] Found Nikon KeyMission 360 at Bus 3 Device 15
[*] Interface 0 claimed
[*] Bulk endpoints: OUT=0x01, IN=0x82

[+] Opening PTP session...
[✓] Session opened (code: 0x201e)

[+] Querying storage devices...
[*] Found 2 storage device(s)
    Storage 1: 0x00000001
    Storage 2: 0x00010001
[*] Interface released
```

### Format Specific Storage

If you need to format a specific storage device:

```bash
python km360_formatter.py --storage 0x00010001
```

### Force Format (No Confirmation)

⚠️ **DANGEROUS** - This will erase all data without asking!

```bash
python km360_formatter.py --force
```

## 🔬 Technical Details

### How It Works

1. **USB Connection** - Opens a direct USB connection to the camera
2. **PTP Session** - Opens a PTP (Picture Transfer Protocol) session
3. **Storage Discovery** - Queries available storage devices (returns IDs like `0x00010001` for the SD card)
4. **Format Command** - Sends the `FormatStore (0x100F)` PTP command
5. **Wait & Verify** - Waits for the camera to complete formatting and returns status

### Storage IDs

The KeyMission 360 exposes two storage devices:

| Storage ID | Description |
|------------|-------------|
| `0x00000001` | Internal storage/RAM |
| `0x00010001` | **SD Card** (this is what you want to format) |

### PTP Protocol

The tool constructs raw PTP packets:

```
FormatStore Command (16 bytes):
  10 00 00 00  - Length (16)
  01 00        - Type (Command)
  0F 10        - Opcode (0x100F = FormatStore)
  03 00 00 00  - Transaction ID
  01 00 01 00  - Storage ID (0x00010001)
```

See [RESEARCH.md](RESEARCH.md) for complete protocol documentation.

## 🛠️ Alternative: Manual Format Without Camera

If you prefer to format the SD card without the camera, you can use standard tools. The camera expects a **FAT32** filesystem:

### Linux
```bash
# Find your SD card (BE CAREFUL!)
lsblk

# Example: /dev/sdc1
DEVICE="/dev/sdc1"

# Unmount
sudo umount $DEVICE

# Format FAT32 with 32KB clusters (optimal for video)
sudo mkfs.vfat -F 32 -s 64 -n "KM360" $DEVICE
```

### macOS
```bash
# Find disk
diskutil list

# Format (example: disk2s1)
sudo diskutil eraseDisk FAT32 KM360 MBRFormat /dev/disk2
```

### Windows
```powershell
# In Command Prompt (Admin)
format F: /FS:FAT32 /V:KM360
```

**Note**: While manual formatting works, the camera may write additional metadata during its native format process. For best compatibility, use the PTP format method or format in-camera.

## ⚠️ Warnings & Limitations

- **Data Loss**: Formatting will erase ALL data on the memory card
- **Quick Format**: This performs a quick format (file system reset), not a secure erase
- **Camera-Specific**: This tool is designed for the Nikon KeyMission 360. Other cameras may use different storage IDs
- **USB Only**: Requires USB connection; does not work over Wi-Fi

## 🐛 Troubleshooting

### "Camera not found"
- Ensure the camera is connected via USB
- Check that the camera is in PTP mode (not Mass Storage mode)
- Try unplugging and reconnecting the USB cable

### "Could not claim interface"
- Another program (like gphoto2, file manager) may be using the camera
- Kill any competing processes: `killall gphoto2 gvfs-gphoto2-volume-monitor`

### "Invalid Storage ID"
- The storage ID may have changed; use `--list` to see current IDs
- Try unplugging and reconnecting the camera

### "Device is busy"
- The camera may be processing something
- Wait a moment and try again
- Check that the camera isn't in the middle of another operation

## 📄 License

MIT License - See [LICENSE](LICENSE) file

## 🙏 Acknowledgments

- [libgphoto2](https://github.com/gphoto/libgphoto2) team for PTP protocol documentation
- [pyusb](https://github.com/pyusb/pyusb) project for USB access
- Nikon for making interesting cameras with documented protocols

## 📚 Further Reading

- [RESEARCH.md](RESEARCH.md) - Complete technical documentation of the PTP protocol implementation
- [PTP Specification](http://www.ntfs.com/img/15740-3.pdf) - PTP Specification (PIMA 15740)

---

**Disclaimer**: This tool is not affiliated with or endorsed by Nikon Corporation. Use at your own risk. The authors are not responsible for data loss or camera damage.
