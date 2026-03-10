# Complete gphoto2 Command Reference for Nikon KeyMission 360

This document contains every gphoto2 function available on the Nikon KeyMission 360 camera.

## Quick Reference

```bash
# Detect camera
gphoto2 --auto-detect

# Get all config values
gphoto2 --list-config

# Get specific config
gphoto2 --get-config=/main/settings/datetime

# Set config value
gphoto2 --set-config datetime=now

# Take photo
gphoto2 --capture-image

# Download all files
gphoto2 --get-all-files
```

---

## ACTIONS (Trigger Commands)

These are toggle/text commands that perform actions.

### /main/actions/bulb
**Bulb Mode** - Long exposure control
- Type: TOGGLE (RW)
- Current: 2
- Usage: `gphoto2 --set-config bulb=1` (on), `gphoto2 --set-config bulb=0` (off)

### /main/actions/autofocusdrive
**Drive Nikon DSLR Autofocus** - Trigger autofocus
- Type: TOGGLE (RW)
- Current: 0
- Usage: `gphoto2 --set-config autofocusdrive=1`

### /main/actions/changeafarea
**Set Nikon Autofocus area** - Change AF area
- Type: TEXT (RW)
- Current: 0x0
- Usage: `gphoto2 --set-config changeafarea=0x1`

### /main/actions/controlmode
**Set Nikon Control Mode** - Set control mode
- Type: TEXT (RW)
- Current: 0
- Usage: `gphoto2 --set-config controlmode=1`

### /main/actions/viewfinder
**Nikon Viewfinder** - Enable/disable live view
- Type: TOGGLE (RW)
- Current: 0
- Usage: `gphoto2 --set-config viewfinder=1` (enable)

### /main/actions/movie
**Movie Capture** - Start/stop video recording
- Type: TOGGLE (RW)
- Current: 2
- Usage: 
  ```bash
  gphoto2 --set-config movie=1  # Start recording
  gphoto2 --set-config movie=0  # Stop recording
  ```

### /main/actions/opcode
**PTP Opcode** - Send raw PTP commands
- Type: TEXT (RW)
- Current: `0x1001,0xparam1,0xparam2`
- Format: `opcode,param1,param2`
- Usage:
  ```bash
  # Format SD card (DANGEROUS!)
  gphoto2 --set-config opcode="0x100f,0x00010001,0x00000000"
  
  # Get device info
  gphoto2 --set-config opcode="0x1001,0x0,0x0"
  ```

---

## SETTINGS (Read/Write)

### Camera Settings

#### /main/settings/datetime
**Camera Date and Time**
- Type: DATE (RW)
- Current: Unix timestamp
- Help: Use 'now' as the current time when setting
- Usage:
  ```bash
  # Set to current time
  gphoto2 --set-config datetime=now
  
  # Set specific time (Unix timestamp)
  gphoto2 --set-config datetime=1773161349
  ```

#### /main/settings/thumbsize
**Thumbnail Size**
- Type: RADIO (RW)
- Current: (empty)
- Choices:
  - `0` = normal
  - `1` = large
- Usage: `gphoto2 --set-config thumbsize=1`

#### /main/settings/fastfs
**Fast Filesystem**
- Type: TOGGLE (RW)
- Current: 1
- Usage: `gphoto2 --set-config fastfs=1` (enable)

#### /main/settings/capturetarget
**Capture Target** - Where to save photos/videos
- Type: RADIO (RW)
- Current: Internal RAM
- Choices:
  - `0` = Internal RAM
  - `1` = Memory card
- Usage: `gphoto2 --set-config capturetarget=1`

#### /main/settings/autofocus
**Autofocus**
- Type: RADIO (RW)
- Current: On
- Choices:
  - `0` = On
  - `1` = Off
- Usage: `gphoto2 --set-config autofocus=0`

### Image Settings

#### /main/imgsettings/whitebalance
**White Balance**
- Type: RADIO (RW)
- Current: Automatic
- Choices:
  - `0` = Automatic
  - `1` = Daylight
  - `2` = Fluorescent
  - `3` = Tungsten
  - `4` = Unknown value 1001
- Usage: `gphoto2 --set-config whitebalance=1` (Daylight)

### Capture Settings

#### /main/capturesettings/movielooplength
**Movie Loop Length**
- Type: RADIO (RW)
- Current: 5
- Choices:
  - `0` = 5 seconds
  - `1` = 10 seconds
  - `2` = 30 seconds
  - `3` = 60 seconds
- Usage: `gphoto2 --set-config movielooplength=2` (30 sec)

#### /main/capturesettings/liveviewafmode
**Live View AF Mode**
- Type: RADIO (RW)
- Current: Face-priority AF
- Choices:
  - `0` = Face-priority AF
  - `1` = Wide-area AF
- Usage: `gphoto2 --set-config liveviewafmode=1`

---

## STATUS (Read-Only)

These provide information about the camera state.

| Config Path | Name | Example Value |
|-------------|------|---------------|
| `/main/status/serialnumber` | Serial Number | 000030037510 |
| `/main/status/manufacturer` | Manufacturer | Nikon Corporation |
| `/main/status/cameramodel` | Camera Model | KeyMission 360 |
| `/main/status/deviceversion` | Firmware | KeyMission 360 Ver.1.3 |
| `/main/status/vendorextension` | Vendor Extension | microsoft.com: 1.0 |
| `/main/status/batterylevel` | Battery Level | 100% |
| `/main/status/availableshots` | Available Shots | 2004 |
| `/main/status/liveviewprohibit` | Live View Prohibit | Live View prohibit conditions: unhandled bitmask 800000 |

---

## IMAGE SETTINGS (Read-Only on this camera)

These can be read but not changed on the KeyMission 360.

### /main/imgsettings/iso
**ISO Speed**
- Type: RADIO (RO)
- Current: 0
- Choices: 100, 125, 160, 200, 250, 320, 400, 500, 640, 800, 1000, 1250, 1600, 2000, 2500, 3200, 4000, 5000, 6400, 8000, 10000, 12800, 16000, 20000, 25600

### /main/capturesettings/exposurecompensation
**Exposure Compensation**
- Type: RADIO (RO)
- Current: 0
- Choices: -2, -1.666, -1.333, -1, -0.666, -0.333, 0, 0.333, 0.666, 1, 1.333, 1.666, 2

### /main/capturesettings/expprogram
**Exposure Program**
- Type: RADIO (RO)
- Current: Unknown value 8201
- Choices: M, P, A, S, Auto, Automatic (No Flash)

### /main/capturesettings/shutterspeed2
**Shutter Speed**
- Type: RADIO (RO)
- Current: 1/32000
- Choices: 30, 25, 20, 15, 13, 4, 3, 2, 1, 1/2, 1/3, 1/4, 1/5, 1/6, 1/8, 1/10, 1/13, 1/15, 1/20, 1/25, 1/30, 1/40, 1/50, 1/60, 1/80, 1/100, 1/125, 1/160, 1/200, 1/250, 1/320, 1/400, 1/500, 1/641, 1/800, 1/1000, 1/1250, 1/1600, 1/2000, 1/2500, 1/3200, 1/4000, 1/5000, 1/6400, 1/8000, 1/10000, 1/13000, 1/16000, 1/20000, 1/26000, 1/32000

---

## RAW PTP PROPERTIES (Nikon Vendor Extensions)

These are low-level Nikon-specific properties accessible via gphoto2.

### Writable Properties

#### /main/other/d304 - MovieCaptureMode
- Type: MENU (RW)
- Current: 0
- Choices: `0`, `1`, `2`, `3`
- Usage: `gphoto2 --set-config /main/other/d304=1`

#### /main/other/d0a0 - Movie Screen Size
- Type: MENU (RW)
- Current: 80
- Choices: `10`, `20`, `40`, `80`, `90`
- Usage: `gphoto2 --set-config /main/other/d0a0=80`

#### /main/other/d0aa - MovWindNoiseReduction
- Type: MENU (RW)
- Current: 0
- Choices:
  - `0` = Off
  - `1` = On
- Usage: `gphoto2 --set-config /main/other/d0aa=1` (enable)

#### /main/other/d05d - Live View AF Area
- Type: MENU (RW)
- Current: 0
- Choices: `0`, `1`
- Usage: `gphoto2 --set-config /main/other/d05d=1`

#### /main/other/d320 - PTP Property 0xd320
- Type: MENU (RW)
- Current: 2
- Choices: `0`, `1`, `2`, `3`
- Usage: `gphoto2 --set-config /main/other/d320=2`

#### /main/other/d321 - PTP Property 0xd321
- Type: MENU (RW)
- Current: 0
- Choices: `0`, `1`

#### /main/other/d322 - PTP Property 0xd322
- Type: MENU (RW)
- Current: 60
- Choices: `20`, `40`, `60`, `100`, `150`

#### /main/other/d323 - MovieLoopLength
- Type: MENU (RW)
- Current: 50
- Choices: `50`, `100`, `300`, `600`

#### /main/other/d324 - PTP Property 0xd324
- Type: MENU (RW)
- Current: 50
- Choices: `20`, `50`, `100`, `300`, `-1`

#### /main/other/d325 - PTP Property 0xd325
- Type: MENU (RW)
- Current: 0
- Choices: `0`, `1`

#### /main/other/d326 - PTP Property 0xd326
- Type: MENU (RW)
- Current: 20
- Choices: `10`, `20`

#### /main/other/d327 - PTP Property 0xd327
- Type: MENU (RW)
- Current: 0
- Choices: `0`, `1`

#### /main/other/d328 - PTP Property 0xd328
- Type: MENU (RW)
- Current: 0
- Choices: `0`, `1`, `2`

#### /main/other/d329 - PTP Property 0xd329
- Type: MENU (RW)
- Current: 1
- Choices: `0`, `1`

#### /main/other/d331 - PTP Property 0xd331
- Type: MENU (RW)
- Current: 300
- Choices: `20`, `50`, `300`, `600`, `3000`

#### /main/other/d332 - PTP Property 0xd332
- Type: MENU (RW)
- Current: 20
- Choices: `0`, `10`, `20`, `30`

#### /main/other/d333 - PTP Property 0xd333
- Type: MENU (RW)
- Current: 1
- Choices: `0`, `1`

#### /main/other/d334 - PTP Property 0xd334
- Type: MENU (RW)
- Current: 0
- Choices: `0`, `1`

#### /main/other/d335 - PTP Property 0xd335
- Type: MENU (RW)
- Current: 1
- Choices: `0`, `1`

#### /main/other/d338 - Camera Name/SSID
- Type: TEXT (RW)
- Current: KM360_30037510
- Usage: `gphoto2 --set-config /main/other/d338=MyCamera360`

#### /main/other/d339 - PTP Property 0xd339
- Type: MENU (RW)
- Current: 1
- Choices: `0`, `1`

#### /main/other/d340 - WiFi Password
- Type: TEXT (RW)
- Current: NikonKeyMission
- **⚠️ Changing this affects SnapBridge connection!**
- Usage: `gphoto2 --set-config /main/other/d340=MyNewPassword`

#### /main/other/d341 - WiFi Channel
- Type: MENU (RW)
- Current: 6
- Choices: `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`, `10`, `11`
- Usage: `gphoto2 --set-config /main/other/d341=6`

#### /main/other/d342 - IP Address
- Type: TEXT (RW)
- Current: 192.168.0.10
- Usage: `gphoto2 --set-config /main/other/d342=192.168.1.50`

#### /main/other/d343 - Subnet Mask
- Type: TEXT (RW)
- Current: 255.255.255.0
- Usage: `gphoto2 --set-config /main/other/d343=255.255.0.0`

#### /main/other/d344 - PTP Property 0xd344
- Type: MENU (RW)
- Current: 0
- Choices: `0`, `1`
- **Note: There are TWO d344 properties!**

#### /main/other/d345 - PTP Property 0xd345
- Type: MENU (RW)
- Current: 1
- Choices: `0`, `1`, `2`

#### /main/other/d347 - PTP Property 0xd347
- Type: MENU (RW)
- Current: 0
- Choices: `0`, `1`

#### /main/other/d349 - PTP Property 0xd349
- Type: MENU (RW)
- Current: 0
- Choices: `0`, `1`

#### /main/other/df52 - PTP Property 0xdf52
- Type: MENU (RW)
- Current: 0
- Choices: `0`, `1`

#### /main/other/df64 - PTP Property 0xdf64
- Type: TEXT (RW)
- Current: (empty)

#### /main/other/df53 - PTP Property 0xdf53
- Type: MENU (RW)
- Current: 0
- Choices: `0`, `1`

#### /main/other/df54 - PTP Property 0xdf54
- Type: TEXT (RW)
- Current: (empty)

#### /main/other/df63 - PTP Property 0xdf63
- Type: MENU (RW)
- Current: 0
- Choices: `1`, `2`, `3`

### Read-Only Properties

| Config Path | Name | Current |
|-------------|------|---------|
| `/main/other/5001` | Battery Level | 100 |
| `/main/other/5005` | White Balance | 2 |
| `/main/other/500e` | Exposure Program Mode | 33281 |
| `/main/other/500f` | Exposure Index (ISO) | 0 |
| `/main/other/5010` | Exposure Bias Compensation | 0 |
| `/main/other/5011` | Date & Time | 20260310T114912 |
| `/main/other/501f` | **Copyright Info** | (empty - writable!) |
| `/main/other/d100` | Nikon Exposure Time | 97536 |
| `/main/other/d1a2` | Live View Status | 0 |
| `/main/other/d1a4` | Live View Prohibit Condition | 8388608 |
| `/main/other/d1f1` | ExposureRemaining | 2004 |
| `/main/other/d407` | PTP Property 0xd407 | 1 |
| `/main/other/d303` | UseDeviceStageFlag | 1 |

---

## FILE OPERATIONS

### List Files
```bash
# List all files
gphoto2 --list-files

# List files with details
gphoto2 --list-files --verbose
```

### Download Files
```bash
# Download specific file
gphoto2 --get-file=1

# Download range of files
gphoto2 --get-file=1-10

# Download all files
gphoto2 --get-all-files

# Download to specific directory
gphoto2 --get-all-files --folder=/path/to/photos
```

### Delete Files
```bash
# Delete specific file
gphoto2 --delete-file=1

# Delete range
gphoto2 --delete-file=1-10

# Delete all files (DANGEROUS!)
gphoto2 --delete-all-files
```

### Upload Files
```bash
# Upload file to camera
gphoto2 --upload-file=/path/to/local/file.jpg
```

---

## CAPTURE OPERATIONS

### Take Photos
```bash
# Capture image
gphoto2 --capture-image

# Capture and download
gphoto2 --capture-image-and-download

# Capture to file
gphoto2 --capture-image --filename=photo_%04n.jpg
```

### Record Video
```bash
# Start recording
gphoto2 --set-config movie=1

# Stop recording
gphoto2 --set-config movie=0

# Or use capture-movie (with duration)
gphoto2 --capture-movie=10s  # Record 10 seconds
```

---

## CAMERA INFORMATION

### Summary
```bash
gphoto2 --summary
```

### Abilities
```bash
gphoto2 --abilities
```

### Storage Information
```bash
gphoto2 --storage-info
```

---

## PRACTICAL SCRIPTS

### Set Current Date/Time
```bash
gphoto2 --set-config datetime=now
echo "Camera time synchronized"
```

### Configure WiFi
```bash
# Change WiFi password
gphoto2 --set-config /main/other/d340=MySecurePassword123

# Change SSID (camera name)
gphoto2 --set-config /main/other/d338=My360Camera

# Set static IP
gphoto2 --set-config /main/other/d342=192.168.1.100
gphoto2 --set-config /main/other/d343=255.255.0.0
```

### Optimize for Video
```bash
# Enable wind noise reduction
gphoto2 --set-config /main/other/d0aa=1

# Set large thumbnail size
gphoto2 --set-config thumbsize=1

# Enable fast filesystem
gphoto2 --set-config fastfs=1
```

### Backup All Photos
```bash
#!/bin/bash
DEST="/backup/km360/$(date +%Y%m%d)"
mkdir -p "$DEST"
gphoto2 --get-all-files --folder="$DEST"
echo "Photos backed up to $DEST"
```

### Record 30-Second Clip
```bash
#!/bin/bash
gphoto2 --set-config movie=1
sleep 30
gphoto2 --set-config movie=0
echo "Recording complete"
```

---

## STORAGE IDS

The camera exposes two storage devices:

| Storage ID | Description |
|------------|-------------|
| `0x00000001` | Internal RAM |
| `0x00010001` | SD Card (29.6 GB free) |

To format via raw PTP:
```bash
# Format SD card (DANGEROUS!)
gphoto2 --set-config opcode="0x100f,0x00010001,0x0"
```

---

## TROUBLESHOOTING

### Command Failed
- Ensure camera is connected: `gphoto2 --auto-detect`
- Check permissions: `ls -la /dev/bus/usb/XXX/YYY`
- Try with sudo: `sudo gphoto2 ...`

### Camera Busy
- Wait a few seconds and retry
- Check if another process is using it: `lsof | grep usb`

### Changes Don't Persist
- Some settings reset when camera powers off
- The camera has no RTC battery - datetime resets

---

*Generated from gphoto2 output on KeyMission 360 Firmware Ver.1.3*
