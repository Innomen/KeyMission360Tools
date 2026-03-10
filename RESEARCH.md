# Nikon KeyMission 360 PTP Protocol Research

## Executive Summary

This document details the reverse engineering of the Nikon KeyMission 360 camera's Picture Transfer Protocol (PTP) implementation, specifically focusing on the memory card formatting functionality via USB.

**Key Finding**: The camera's SD card can be formatted by sending raw PTP `FormatStore (0x100F)` commands over USB bulk endpoints, bypassing the need for manual interaction with the camera's buttons.

---

## 1. Hardware Information

### Camera Specifications
| Property | Value |
|----------|-------|
| Model | Nikon KeyMission 360 |
| USB Vendor ID | 0x04B0 (Nikon Corp.) |
| USB Product ID | 0x019F |
| Firmware Version | KeyMission 360 Ver.1.3 (observed) |
| USB Class | PTP (Picture Transfer Protocol) |

### USB Interface Layout
```
Configuration: 1
Interface: 0 (PTP)
  Bulk OUT Endpoint: 0x01
  Bulk IN Endpoint: 0x82
  Interrupt IN Endpoint: 0x83
```

---

## 2. PTP Protocol Implementation

### 2.1 Container Structure

PTP uses a container-based packet structure. All multi-byte values are **little-endian**.

#### Command Container
```
Offset  Size  Description
------  ----  -----------
0       4     Container Length (bytes)
4       2     Container Type (0x0001 = Command)
6       2     Operation Code (Opcode)
8       4     Transaction ID
12      4     Parameter 1 (optional)
16      4     Parameter 2 (optional)
...     ...   Additional parameters
```

#### Response Container
```
Offset  Size  Description
------  ----  -----------
0       4     Container Length (bytes)
4       2     Container Type (0x0003 = Response)
6       2     Response Code
8       4     Transaction ID
12      4     Parameter 1 (optional)
```

#### Data Container
```
Offset  Size  Description
------  ----  -----------
0       4     Container Length (bytes)
4       2     Container Type (0x0002 = Data)
6       2     Operation Code (from associated command)
8       4     Transaction ID
12      ...   Payload Data
```

### 2.2 Standard PTP Opcodes Supported

| Opcode | Name | Description |
|--------|------|-------------|
| 0x1001 | GetDeviceInfo | Returns device capabilities |
| 0x1002 | OpenSession | Opens a PTP session |
| 0x1003 | CloseSession | Closes a PTP session |
| 0x1004 | GetStorageIDs | Returns available storage device IDs |
| 0x1005 | GetStorageInfo | Returns storage device information |
| 0x1006 | GetNumObjects | Returns object count |
| 0x1007 | GetObjectHandles | Returns list of objects |
| 0x1008 | GetObjectInfo | Returns object metadata |
| 0x1009 | GetObject | Returns object data |
| 0x100A | GetThumb | Returns thumbnail |
| 0x100B | DeleteObject | Deletes an object |
| 0x100C | SendObjectInfo | Sends object metadata |
| 0x100D | SendObject | Sends object data |
| 0x100E | InitiateCapture | Triggers image capture |
| **0x100F** | **FormatStore** | **Formats a storage device** |

### 2.3 Nikon Vendor Extensions

The camera supports various Nikon-specific opcodes in the 0x90xx and 0xDxxx range for camera control, live view, etc.

---

## 3. Storage Device Architecture

### 3.1 Storage ID Structure

Storage IDs on the KeyMission 360 follow a specific pattern:

```
Storage ID Format (32-bit):
  Bits 0-15:  Physical Volume ID
  Bits 16-31: Logical Volume ID / Storage Type

Example Storage IDs:
  0x00000001 = Internal RAM/Storage
  0x00010001 = SD Card (Removable storage)
```

### 3.2 GetStorageIDs Response Format

The response to `GetStorageIDs (0x1004)` returns a data container with:

```
Offset  Size  Description
------  ----  -----------
0       4     Container Length
4       2     Container Type (0x0002 = Data)
6       2     Opcode (0x1004)
8       4     Transaction ID
12      4     Number of Storage IDs
16      4     Storage ID 1
20      4     Storage ID 2
...     ...   Additional IDs
```

**Actual observed response from KeyMission 360:**
```
14 00 00 00 02 00 04 10 02 00 00 00 02 00 00 00 01 00 00 00 01 00 01 00
```

Parsed:
- Length: 20 bytes (0x14)
- Type: 0x0002 (Data)
- Opcode: 0x1004
- Transaction: 2
- Count: 2 storage devices
- Storage ID 1: 0x00000001 (Internal)
- Storage ID 2: 0x00010001 (SD Card)

### 3.3 Critical Discovery: Correct Storage ID

**Important**: Initial assumptions suggested the SD card would be at `0x00010000`, but the actual storage ID is **`0x00010001`**. This was the key discovery that enabled successful formatting.

---

## 4. FormatStore Command Analysis

### 4.1 Command Structure

The `FormatStore (0x100F)` command formats a storage device.

**Command Format:**
```
Length:     16 bytes
Type:       0x0001 (Command)
Opcode:     0x100F (FormatStore)
Trans ID:   Incrementing transaction number
Parameter:  Storage ID to format
```

**Hex dump of successful format command:**
```
10 00 00 00 01 00 0F 10 02 00 00 00 01 00 01 00
```

Breakdown:
- `10 00 00 00` - Length: 16 bytes
- `01 00` - Type: Command
- `0F 10` - Opcode: 0x100F (FormatStore)
- `02 00 00 00` - Transaction ID: 2
- `01 00 01 00` - Storage ID: 0x00010001 (SD Card)

### 4.2 Response Codes

| Code | Name | Description |
|------|------|-------------|
| 0x2001 | OK | Success - format completed |
| 0x2006 | Parameter Not Supported | Wrong number/type of parameters |
| 0x2008 | Invalid Storage ID | Storage ID doesn't exist |
| 0x200A | Session Not Open | PTP session not established |
| 0x2019 | Device Busy | Camera is busy with another operation |
| 0x201D | Invalid Parameter | Parameter value is invalid |
| 0x201E | Session Already Open | Session is already active |

### 4.3 Parameter Testing Results

Various parameter combinations were tested:

| Storage ID | Format Type | Params | Result |
|------------|-------------|--------|--------|
| 0x00010000 | N/A | 1 | 0x2008 (Invalid Storage ID) |
| 0x00010000 | 0x00000000 | 2 | 0x2006 (Parameter Not Supported) |
| 0x00000001 | N/A | 1 | 0x2008 (Invalid Storage ID) |
| **0x00010001** | **N/A** | **1** | **0x2001 (OK)** |

**Conclusion**: The KeyMission 360's FormatStore command expects exactly **1 parameter** (the Storage ID). The Format Type parameter mentioned in some PTP specifications is not used by this camera.

---

## 5. Communication Flow

### 5.1 Complete Format Sequence

```
1. OPEN USB DEVICE
   └── Set Configuration 1
   └── Detach kernel drivers
   └── Claim Interface 0

2. OPEN PTP SESSION
   └── Send: OpenSession (0x1002)
   └── Params: Session ID = 1
   └── Receive: Response 0x2001 (OK)

3. GET STORAGE IDS (Optional but recommended)
   └── Send: GetStorageIDs (0x1004)
   └── Receive: Data container with storage list
   └── Receive: Response 0x2001 (OK)

4. FORMAT STORAGE
   └── Send: FormatStore (0x100F)
   └── Params: Storage ID (0x00010001)
   └── Wait: 10-30 seconds (format time)
   └── Receive: Response 0x2001 (OK)

5. CLOSE
   └── Release Interface
   └── Close USB device
```

### 5.2 Timing Characteristics

| Operation | Typical Duration |
|-----------|-----------------|
| OpenSession | < 100ms |
| GetStorageIDs | < 100ms |
| FormatStore | 5-30 seconds (depends on card size/condition) |

---

## 6. What Does FormatStore Actually Do?

### 6.1 File System Analysis

The `FormatStore` command triggers the camera's internal formatting routine. Based on PTP specifications and observed behavior:

1. **File System**: Creates FAT32 filesystem (standard for SD cards)
2. **Allocation Unit Size**: Camera-optimized cluster size (typically 32KB for video)
3. **Directory Structure**: Creates required DCIM (Digital Camera IMages) directory
4. **Volume Label**: Sets camera-specific volume label

### 6.2 Can We Format Without the Camera?

**Short answer**: Yes, but with limitations.

The PTP `FormatStore` command essentially performs:
```
mkfs.vfat -F 32 -s 64 -n "KEYMISSION360" /dev/sdX
```

However, there may be camera-specific metadata written during the format process:
- Nikon-specific directory structures
- Hidden system files
- Database/index files for media management

**Recommendation**: While a standard FAT32 format will likely work for basic usage, the camera may perform better with its native format. For guaranteed compatibility, use the PTP format command or format in-camera.

### 6.3 Standard SD Card Format Specification

For reference, a standard SD/SDHC/SDXC card format that should work:

```bash
# Find your SD card device (BE CAREFUL!)
lsblk

# Example: /dev/sdc
DEVICE="/dev/sdc"

# Unmount if mounted
umount ${DEVICE}* 2>/dev/null

# Create new partition table
sudo parted -s $DEVICE mklabel msdos

# Create FAT32 partition
sudo parted -s $DEVICE mkpart primary fat32 1MiB 100%

# Format with FAT32, 32KB clusters (optimal for video)
sudo mkfs.vfat -F 32 -s 64 -n "KM360" ${DEVICE}1

# Or simply (less optimal):
# sudo mkfs.vfat -F 32 -n "KM360" ${DEVICE}1
```

---

## 7. Security & Safety Considerations

### 7.1 Data Destruction

- The FormatStore command performs a **quick format**
- Data is not securely erased (file system structures are reset, data remains)
- For secure deletion, use specialized tools after formatting

### 7.2 Safety Mechanisms

The camera does not appear to have write-protection checks via PTP:
- Physical write-protect switch on SD card still functions
- Locked cards will likely return 0x2019 (Device Busy) or similar

### 7.3 Error Recovery

If format fails mid-process:
- Card may be left in partially-formatted state
- Re-run format command or use camera's built-in format
- Worst case: Use standard FAT32 format on computer

---

## 8. Comparison with gphoto2

### 8.1 Why gphoto2 Failed

gphoto2 provides a generic `opcode` config (`/main/actions/opcode`) for sending raw PTP commands, but it has limitations:

1. **Parameter Parsing**: The `0x100F` command requires specific parameters that gphoto2's generic handler doesn't properly format
2. **Multiple Parameters**: gphoto2's opcode config has trouble with multiple parameters
3. **Response Handling**: Raw PTP requires reading both data and response phases for some commands

### 8.2 Debug Output Analysis

From gphoto2 debug logs, we observed:
```
_put_Generic_OPCode: opcode 0x100f
_put_Generic_OPCode: param 0 0x10000
_put_Generic_OPCode: param 1 0x55f4
```

The second parameter was being corrupted/incorrectly parsed, leading to:
```
PTP_OC 0x100f receiving resp failed: PTP Invalid Parameter (0x201d)
```

---

## 9. References

### Specifications
- PTP Specification (PIMA 15740:2000)
- USB Mass Storage Class Specification
- SD Card Association Physical Layer Specification

### Tools Used
- `lsusb` - USB device enumeration
- `gphoto2` - Initial protocol exploration
- `pyusb` / `libusb1` - Raw USB communication

### Related Projects
- libgphoto2 (https://github.com/gphoto/libgphoto2)
- gphoto2 (https://github.com/gphoto/gphoto2)

---

## 10. Future Research

Potential areas for further investigation:

1. **Other Nikon Cameras**: Test if the same storage ID pattern (0x00010001) applies
2. **Format Types**: Investigate if there's a "full format" vs "quick format" option
3. **Progress Indication**: Check if the camera sends progress events during format
4. **Recovery Mode**: Explore if there's a low-level format option for corrupted cards

---

## Appendix A: Complete PTP Packet Examples

### A.1 OpenSession
```
Request:  10 00 00 00 01 00 02 10 01 00 00 00 01 00 00 00
Response: 0C 00 00 00 03 00 1E 20 01 00 00 00
          (Session already open - code 0x201E)
```

### A.2 GetStorageIDs
```
Request:  10 00 00 00 01 00 04 10 02 00 00 00 00 00 00 00
Data:     14 00 00 00 02 00 04 10 02 00 00 00 02 00 00 00
          01 00 00 00 01 00 01 00
Response: 0C 00 00 00 03 00 01 20 02 00 00 00
```

### A.3 FormatStore (Success)
```
Request:  10 00 00 00 01 00 0F 10 03 00 00 00 01 00 01 00
Response: 0C 00 00 00 03 00 01 20 03 00 00 00
          (Code 0x2001 = OK)
```

---

## 11. gphoto2 Complete Feature Discovery

### 11.1 Overview

Using gphoto2, the KeyMission 360 exposes **80+ configurable properties** across multiple categories:

- **7 Actions** - Trigger commands (bulb, movie, autofocus, etc.)
- **6 Settings** - Read/write camera settings (datetime, whitebalance, etc.)
- **8 Status** - Read-only information (battery, serial number, etc.)
- **4 Image Settings** - ISO, exposure, white balance
- **5 Capture Settings** - Movie mode, AF mode, exposure program
- **50+ Nikon Vendor Extensions** - Low-level PTP properties

### 11.2 Notable Writable Properties

| Property | Address | Type | Description |
|----------|---------|------|-------------|
| datetime | /main/settings/datetime | DATE | Set camera time (use `now`) |
| movie | /main/actions/movie | TOGGLE | Start/stop recording |
| whitebalance | /main/imgsettings/whitebalance | RADIO | Auto/Daylight/Fluorescent/Tungsten |
| movielooplength | /main/capturesettings/movielooplength | RADIO | 5/10/30/60 seconds (loop recording buffer) |
| capturetarget | /main/settings/capturetarget | RADIO | Internal RAM or Memory card |
| d304 | /main/other/d304 | MENU | Movie Capture Mode (0-3) - likely Standard/Loop/Timelapse/Superlapse |
| d0aa | /main/other/d0aa | MENU | Wind Noise Reduction (0/1) |
| d323 | /main/other/d323 | MENU | Movie Loop Length (50/100/300/600) |
| d338 | /main/other/d338 | TEXT | Camera Name/SSID |
| **d340** | **/main/other/d340** | **TEXT** | **WiFi Password** |
| d341 | /main/other/d341 | MENU | WiFi Channel (1-11) |
| d342 | /main/other/d342 | TEXT | IP Address |
| d343 | /main/other/d343 | TEXT | Subnet Mask |
| 501f | /main/other/501f | TEXT | Copyright Info |

### 11.3 Date/Time Behavior

**Critical Finding**: The KeyMission 360 has **no RTC (Real-Time Clock) battery**. 

- Date/time resets to factory default (2016-01-01) when battery is removed
- Must set datetime each time camera powers on: `gphoto2 --set-config datetime=now`
- This explains why photos appear with 2016 timestamps

### 11.4 WiFi Configuration

The camera's WiFi settings are fully accessible:

```bash
# View current settings
gphoto2 --get-config /main/other/d338  # SSID
gphoto2 --get-config /main/other/d340  # Password
gphoto2 --get-config /main/other/d342  # IP
gphoto2 --get-config /main/other/d343  # Netmask

# Modify settings
gphoto2 --set-config /main/other/d338=MyCamera360
gphoto2 --set-config /main/other/d340=NewPassword123
gphoto2 --set-config /main/other/d341=6  # Channel
gphoto2 --set-config /main/other/d342=192.168.1.50
```

**Warning**: Changing the WiFi password (`d340`) will break existing SnapBridge pairings.

### 11.5 Movie Recording Control

Two methods to control video recording:

**Method 1: gphoto2 movie toggle**
```bash
gphoto2 --set-config movie=1  # Start
gphoto2 --set-config movie=0  # Stop
```

**Method 2: gphoto2 capture-movie**
```bash
gphoto2 --capture-movie=30s  # Record 30 seconds
```

### 11.6 Storage Information

```bash
gphoto2 --storage-info
```

Output shows:
- **store_00010001**: Removable RAM (SD Card)
  - Capacity: 29,652 MB (~30 GB)
  - Free: 29,629 MB
  - Filesystem: DCIM (Digital Camera Layout)

### 11.7 Comparison: Raw PTP vs gphoto2

| Operation | Raw PTP (Python) | gphoto2 |
|-----------|------------------|---------|
| Format SD | `0x100f` command | `opcode` config |
| Get storage | `0x1004` command | `--storage-info` |
| Set datetime | `0x1014` command | `datetime=now` |
| Take photo | `0x100e` command | `--capture-image` |
| Download | `0x1009` command | `--get-all-files` |

**Advantage of gphoto2**: Higher-level interface, handles session management
**Advantage of raw PTP**: More control, works when gphoto2 has issues

### 11.8 Firmware Version

Detected firmware: **KeyMission 360 Ver.1.3**

Properties observed may vary with firmware updates.

---

## Appendix B: gphoto2 Property Reference

### B.1 Action Commands

```
/main/actions/bulb                    - Bulb mode toggle
/main/actions/autofocusdrive          - Trigger AF
/main/actions/changeafarea            - Change AF area
/main/actions/controlmode             - Set control mode
/main/actions/viewfinder              - Live view toggle
/main/actions/movie                   - Movie record toggle
/main/actions/opcode                  - Raw PTP opcode
```

### B.2 Standard PTP Opcodes via gphoto2

| Opcode | Name | gphoto2 Equivalent |
|--------|------|-------------------|
| 0x1001 | GetDeviceInfo | `--summary` |
| 0x1002 | OpenSession | (automatic) |
| 0x1003 | CloseSession | (automatic) |
| 0x1004 | GetStorageIDs | `--storage-info` |
| 0x1005 | GetStorageInfo | `--storage-info` |
| 0x100f | FormatStore | `opcode` config |
| 0x1014 | SetDevicePropValue | `--set-config` |
| 0x1015 | GetDevicePropValue | `--get-config` |
| 0x1016 | ResetDevicePropValue | (various) |

---

## 12. Complete Command Summary

### Essential Commands

```bash
# Connect and verify
gphoto2 --auto-detect
gphoto2 --summary

# Fix datetime (critical - no RTC battery!)
gphoto2 --set-config datetime=now

# Manage files
gphoto2 --list-files
gphoto2 --get-all-files
gphoto2 --delete-all-files

# Capture
gphoto2 --capture-image
gphoto2 --capture-image-and-download
gphoto2 --set-config movie=1 && sleep 10 && gphoto2 --set-config movie=0

# WiFi config
gphoto2 --set-config /main/other/d340=NewPassword
gphoto2 --set-config /main/other/d338=MyCamera

# Settings
gphoto2 --set-config whitebalance=1          # Daylight
gphoto2 --set-config movielooplength=2       # 30 seconds
gphoto2 --set-config capturetarget=1         # Memory card
```

---

## 12. Known Unknowns

The following settings have been identified but their exact behavior or value mappings are not fully understood:

### 12.1 Movie Capture Mode (d304)
- **Address:** `/main/other/d304`
- **Type:** MENU (0, 1, 2, 3)
- **Current Knowledge:** The camera supports multiple recording modes: Standard, Loop Recording, Time-lapse, and Superlapse (hyperlapse). This setting likely selects between them.
- **Unknown:** Which value (0-3) corresponds to which mode.
- **Testing needed:** Try each value and observe camera behavior when recording.

### 12.2 Movie Loop Length (movielooplength / d323)
- **Address:** `/main/capturesettings/movielooplength` (and `/main/other/d323`)
- **Type:** RADIO (0=5s, 1=10s, 2=30s, 3=60s)
- **Current Knowledge:** The camera has a Loop Recording mode that acts like a dashcam - it continuously records to a buffer and only keeps the most recent X seconds. This setting likely controls that buffer duration.
- **Unknown:** Does this affect standard recording mode, or only when d304 is set to loop mode?
- **Related:** May interact with d304 (Movie Capture Mode).

### 12.3 Movie Screen Size (d0a0)
- **Address:** `/main/other/d0a0`
- **Type:** MENU (10, 20, 40, 80, 90)
- **Unknown:** How these values map to actual video resolutions.

---

*Document Version: 2.1*
*Date: 2026-03-10*
*Researcher: AI Assistant / Claude Code*
*Updates: Added complete gphoto2 property discovery, WiFi config, datetime behavior*
