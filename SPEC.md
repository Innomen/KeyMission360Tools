# KeyMission 360 Linux Utility - Technical Specification

## Project Overview

A comprehensive Linux replacement for the Nikon KeyMission 360/170 Utility Windows application. Built using Python, gphoto2, and tkinter.

---

## 1. Hardware Analysis

### 1.1 Camera Specifications
| Property | Value |
|----------|-------|
| Model | Nikon KeyMission 360 |
| USB Vendor ID | 0x04B0 (Nikon Corp.) |
| USB Product ID | 0x019F |
| Firmware Version | KeyMission 360 Ver.1.3 |
| USB Class | PTP (Picture Transfer Protocol) |
| Video Resolution | 4K/24fps, 1080p/60fps, etc. |
| Photo Resolution | 7744 × 3872 (30 MP) |
| Lens Configuration | Dual 180° f/2.0 fisheye lenses |

### 1.2 USB Interface Layout
```
Configuration: 1
Interface: 0 (PTP)
  Bulk OUT Endpoint: 0x01
  Bulk IN Endpoint: 0x82
  Interrupt IN Endpoint: 0x83
```

### 1.3 Storage Architecture
| Storage ID | Description | Size |
|------------|-------------|------|
| 0x00000001 | Internal RAM | ~MB |
| 0x00010001 | SD Card (Removable) | 29.6 GB |

### 1.4 Critical Hardware Limitations
- **NO RTC Battery** - Loses date/time when battery removed
- **NO Live View over USB** - Live view blocked (error 0x00800000)
- **PTP Only** - No Mass Storage mode available

---

## 2. Protocol Documentation

### 2.1 PTP Container Structure
All multi-byte values are **little-endian**.

#### Command Container (16+ bytes)
```
Offset  Size  Description
------  ----  -----------
0       4     Container Length (bytes)
4       2     Container Type (0x0001 = Command)
6       2     Operation Code (Opcode)
8       4     Transaction ID
12      4     Parameter 1 (optional)
16      4     Parameter 2 (optional)
```

#### Standard PTP Opcodes Supported
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
| 0x1009 | GetObject | Returns object data (download) |
| 0x100A | GetThumb | Returns thumbnail |
| 0x100B | DeleteObject | Deletes an object |
| 0x100C | SendObjectInfo | Sends object metadata |
| 0x100D | SendObject | Sends object data (upload) |
| 0x100E | InitiateCapture | Triggers image capture |
| **0x100F** | **FormatStore** | **Formats a storage device** |
| 0x1014 | SetDevicePropValue | Set property value |
| 0x1015 | GetDevicePropValue | Get property value |

#### Response Codes
| Code | Name | Description |
|------|------|-------------|
| 0x2001 | OK | Success |
| 0x2006 | Parameter Not Supported | Wrong parameters |
| 0x2008 | Invalid Storage ID | Storage doesn't exist |
| 0x200A | Session Not Open | PTP session not established |
| 0x2019 | Device Busy | Camera busy |
| 0x201D | Invalid Parameter | Invalid parameter value |
| 0x201E | Session Already Open | Session already active |

### 2.2 FormatStore Command Analysis
**Command Structure (16 bytes):**
```
10 00 00 00 01 00 0F 10 03 00 00 00 01 00 01 00
```
- `10 00 00 00` - Length: 16 bytes
- `01 00` - Type: Command
- `0F 10` - Opcode: 0x100F (FormatStore)
- `03 00 00 00` - Transaction ID: 3
- `01 00 01 00` - Storage ID: 0x00010001 (SD Card)

**Critical Discovery**: The KeyMission 360's FormatStore command expects exactly **1 parameter** (the Storage ID).

---

## 3. gphoto2 Property Reference

### 3.1 Actions (Trigger Commands)
| Config Path | Name | Type | Description |
|-------------|------|------|-------------|
| `/main/actions/bulb` | Bulb Mode | TOGGLE | Long exposure control |
| `/main/actions/autofocusdrive` | Drive Nikon DSLR Autofocus | TOGGLE | Trigger autofocus |
| `/main/actions/changeafarea` | Set Nikon Autofocus area | TEXT | Change AF area |
| `/main/actions/controlmode` | Set Nikon Control Mode | TEXT | Set control mode |
| `/main/actions/viewfinder` | Nikon Viewfinder | TOGGLE | Enable/disable viewfinder (blocked on KM360) |
| `/main/actions/movie` | Movie Capture | TOGGLE | **Start/stop video recording** |
| `/main/actions/opcode` | PTP Opcode | TEXT | Send raw PTP commands |

### 3.2 Settings (Read/Write)
| Config Path | Name | Type | Current | Options |
|-------------|------|------|---------|---------|
| `/main/settings/datetime` | **Camera Date and Time** | DATE | Unix timestamp | Use 'now' |
| `/main/settings/thumbsize` | Thumbnail Size | RADIO | - | normal, large |
| `/main/settings/fastfs` | Fast Filesystem | TOGGLE | 1 | Enable/disable |
| `/main/settings/capturetarget` | **Capture Target** | RADIO | Internal RAM | Internal RAM, Memory card |
| `/main/settings/autofocus` | **Autofocus** | RADIO | On | On, Off |

### 3.3 Image Settings
| Config Path | Name | Type | Current | Options |
|-------------|------|------|---------|---------|
| `/main/imgsettings/whitebalance` | **White Balance** | RADIO | Automatic | Automatic, Daylight, Fluorescent, Tungsten |
| `/main/imgsettings/iso` | ISO Speed | RADIO | 0 | 100-25600 (read-only on KM360) |

### 3.4 Capture Settings
| Config Path | Name | Type | Current | Options |
|-------------|------|------|---------|---------|
| `/main/capturesettings/movielooplength` | **Movie Loop Length** | RADIO | 5 | 5, 10, 30, 60 seconds (for loop recording mode) |
| `/main/capturesettings/exposurecompensation` | Exposure Compensation | RADIO | 0 | -2 to +2 stops |
| `/main/capturesettings/expprogram` | Exposure Program | RADIO | 8201 | M, P, A, S, Auto |
| `/main/capturesettings/shutterspeed2` | Shutter Speed | RADIO | 1/32000 | 30s to 1/32000 |
| `/main/capturesettings/liveviewafmode` | **Live View AF Mode** | RADIO | Face-priority | Face-priority AF, Wide-area AF |

### 3.5 Nikon Vendor Extensions (Writable!)
| Property | Address | Type | Current | Description |
|----------|---------|------|---------|-------------|
| d304 | `/main/other/d304` | MENU | 0 | **Movie Capture Mode** (0-3) - likely Standard/Loop/Timelapse/Superlapse |
| d0a0 | `/main/other/d0a0` | MENU | 80 | **Movie Screen Size** (10,20,40,80,90) |
| d0aa | `/main/other/d0aa` | MENU | 0 | **Wind Noise Reduction** (0/1) |
| d320 | `/main/other/d320` | MENU | 2 | Unknown (0-3) |
| d323 | `/main/other/d323` | MENU | 50 | **Movie Loop Length** (50,100,300,600) |
| d338 | `/main/other/d338` | TEXT | KM360_xxx | **Camera Name/SSID** |
| **d340** | `/main/other/d340` | TEXT | NikonKeyMission | **WiFi Password** |
| d341 | `/main/other/d341` | MENU | 6 | **WiFi Channel** (1-11) |
| d342 | `/main/other/d342` | TEXT | 192.168.0.10 | **IP Address** |
| d343 | `/main/other/d343` | TEXT | 255.255.255.0 | **Subnet Mask** |
| 501f | `/main/other/501f` | TEXT | "" | **Copyright Info** |

---

## 4. Windows App Analysis (KeyMissionUtility.exe v1.1.0)

### 4.1 Architecture
- **Framework**: .NET Framework 4.5 (WPF application)
- **UI Technology**: XAML with custom styles
- **Video Processing**: FFmpeg (bundled)
- **360° Projection**: Plate Carree (equirectangular)

### 4.2 Views/Windows Identified
```
KeyMissionUtility.View
├── CameraFolderTree          # File browser
├── CameraLinkView           # Connection status
├── ConnectSetting           # Connection settings
├── DateSetting              # Date/time settings
├── EditSave                 # Export/save dialog
├── HandleCopyFileProgress   # Download progress
├── LoadingView              # Loading/splash
├── SettingMessageView       # Settings dialogs
├── CameraSettingView        # Camera settings panel
└── AboutAppView             # About dialog
```

### 4.3 Features in Windows App

#### File Management
- Tree view of camera storage
- Thumbnail display
- Download with progress
- Delete files
- Save As (multiple formats)
- **Save for YouTube** (special export)

#### 360° Viewing
- Equirectangular image display
- Split-screen view
- Plate Carree projection
- Pan/zoom navigation
- Cross mark position guide

#### Video Playback
- MP4 playback with FFmpeg
- 4K/30p support (hardware dependent)
- Highlight tag support
- Resize handling

#### Camera Settings
- Movie Mode (Standard, Slow Motion, etc.)
- White Balance
- Exposure Compensation
- Date/Time sync
- WiFi Configuration

### 4.4 Export Formats
- Original format
- YouTube-optimized (re-encoded)
- Thumbnail extraction
- Frame extraction

---

## 5. Linux Implementation Plan

### 5.1 Completed Tools

#### km360_download.py (v1.6) - NEW
- **Purpose**: Reliable file download with resume, checksums, and retry
- **Features**:
  - SHA256 checksum verification
  - Automatic retry with exponential backoff (3 attempts)
  - Resume partial downloads
  - Progress reporting
  - Size verification
- **Usage**: `python3 km360_download.py 5 ~/Videos/file.mp4`

#### km360_usb_reset.py (v1.6) - NEW
- **Purpose**: Reset USB port when camera becomes unresponsive
- **Features**:
  - Auto-detect camera on USB bus
  - Multiple reset methods (pyusb, usbreset, sysfs)
  - No physical unplugging required
  - Command-line and GUI integration
- **Usage**: `python3 km360_usb_reset.py`

#### km360_gui.py (v1.7)
- **Purpose**: Main GUI application
- **Features**:
  - File browser with right-click context menu
  - Download manager with auto 360° metadata injection
  - Settings configuration
  - 360° Viewer integration
  - Native file dialogs (GTK/KDE) with Places sidebar
  - USB port memory for faster reset
  - Quick Actions tab
  - Camera info display
  - Add to Start Menu integration

#### km360_formatter.py
- **Purpose**: Format SD card via raw PTP
- **Method**: Direct USB/libusb1 communication
- **Features**:
  - Auto-detect camera
  - List storage devices
  - Format with confirmation
  - Force mode (no prompt)
  - Headless test mode

#### km360_info.py
- **Purpose**: Display camera information
- **Features**:
  - USB device info
  - PTP endpoints
  - Device capabilities
  - Storage IDs
  - Headless test mode

#### km360_set_time.py
- **Purpose**: Sync camera time to system time
- **Critical**: Addresses RTC battery issue
- **Features**:
  - Check current time
  - Sync to system time
  - Verify change
  - Headless test mode

#### km360_youtube_export.py (v1.5)
- **Purpose**: Inject 360° metadata for YouTube
- **Method**: ffmpeg or spatialmedia library
- **Features**:
  - No re-encoding (fast)
  - Batch processing
  - Auto fallback between methods
  - Headless test mode
- **Usage**: `python3 km360_youtube_export.py video.mp4`

#### km360_viewer.py (v1.5)
- **Purpose**: Interactive 360° photo/video viewer
- **Method**: Equirectangular to rectilinear projection
- **Features**:
  - Mouse drag to look around
  - Scroll to zoom
  - WASD/Arrow key navigation
  - Video playback (OpenCV)
  - Headless test mode
- **Controls**:
  - Mouse drag: Look around
  - Scroll: Zoom
  - WASD/Arrows: Navigate
  - Space: Play/Pause (video)
  - F: Fullscreen
  - R: Reset view
- **Usage**: `python3 km360_viewer.py photo.jpg`

#### manual_format.sh
- **Purpose**: Format SD card without camera
- **Method**: Standard Linux tools (parted, mkfs.vfat)

### 5.2 Planned GUI Application (km360_gui.py)

#### Window Structure
```
MainWindow (tkinter)
├── MenuBar
│   ├── File
│   ├── Camera
│   ├── Tools
│   └── Help
├── LeftPanel (30%)
│   ├── ConnectionStatus
│   ├── FileTreeView
│   └── PreviewPane
├── RightPanel (70%)
│   ├── TabbedInterface
│   │   ├── 📁 Files Tab
│   │   ├── ⚙️ Settings Tab
│   │   ├── 🎥 Video Tab
│   │   └── 📊 Info Tab
│   └── StatusBar
└── BottomBar
    ├── ProgressBar
    └── ActionButtons
```

#### Implemented Features (v1.0)
1. **Connection Management**
   - Auto-detect camera
   - Connection status indicator
   - Disconnect/reconnect

2. **File Browser** (v1.7)
   - Tree view of camera storage with hidden file number tracking
   - File list with metadata (size, date, type)
   - **Batch selection**: Ctrl+A (all), Ctrl+Click (multi), Shift+Click (range)
   - **Right-click context menu** (v1.7)
     * View in 360° Viewer (with download warning for videos)
     * Download (with options dialog)
     * Delete (now works with proper folder paths)
     * Copy Filename

3. **Download Manager** (v1.7)
   - Download selected/all files with **progress dialog**
   - **Options dialog** with "Remove from camera after download" checkbox
   - **Auto 360° metadata injection** for all videos (YouTube-ready)
   - **SHA256 checksum verification** for data integrity
   - **Resume support** for interrupted downloads
   - **Cancel button** during download
   - **Retry failed** button for failed transfers
   - Speed display and ETA estimation
   - Native file dialogs (GTK/KDE) with Places sidebar
   - Remembers last download directory

4. **USB Port Reset** (v1.7)
   - "🔄 Reset USB" button in file browser
   - **USB port memory** - remembers last port for faster reset
   - Resets USB port when camera times out
   - No physical unplugging required
   - Supports multiple reset methods (pyusb, usbreset, sysfs)

5. **Settings Panel** (v1.7)
   - Date/Time sync (with auto-sync option)
   - White Balance
   - Movie Mode
   - Loop Length
   - Capture Target
   - File dialog preference (Auto/GTK/KDE/Tk)

6. **Quick Actions**
   - Format SD card (with confirmation)
   - Set Copyright info
   - Configure WiFi
   - Camera info display

7. **Help Menu** (v1.7)
   - Add to Start Menu integration
   - Documentation viewer
   - About dialog

#### Implemented Features (v1.5-v1.6)
1. **360° Viewer** ✅ IMPLEMENTED (v1.5)
   - Equirectangular image viewer
   - **Mouse drag** to look around (change yaw/pitch)
   - **Scroll** to zoom (change FOV)
   - **WASD/Arrow keys** to navigate
   - Video playback with play/pause
   - Rectilinear projection (natural perspective)
   - **Download warning** - warns before downloading large videos
   - **Cancel option** during download
   - Standalone tool: `km360_viewer.py`

2. **YouTube Export** ✅ INTEGRATED (v1.7)
   - **Auto-injected on all video downloads** - no separate step needed
   - **No re-encoding** - fast metadata injection only
   - Injects Spatial Media metadata for 360° recognition
   - Standalone tool still available: `km360_youtube_export.py`

3. **Reliable Downloads** ✅ IMPLEMENTED (v1.6)
   - SHA256 checksum verification
   - Automatic retry (3 attempts)
   - Resume partial downloads
   - Progress dialog with cancel option
   - Detailed error messages
   - Standalone tool: `km360_download.py`

4. **USB Reset** ✅ IMPLEMENTED (v1.6)
   - Reset USB port without unplugging
   - Multiple reset methods
   - GUI button integration
   - Standalone tool: `km360_usb_reset.py`

#### File Browser Integration (v1.7)
- Right-click any file → "View in 360° Viewer"
  - Shows download warning dialog with file size
  - Special warning for video files (may take minutes)
  - Progress bar during download
  - **Cancel button** to abort download
  - Opens in viewer automatically
- Right-click delete now works correctly
  - Properly deletes from camera storage folders
  - Shows success/failure count
- Viewer tab has Quick Open dropdown
  - Lists all camera files
  - One-click open in viewer
- **Automatic 360° metadata injection** (v1.7)
  - All video downloads automatically get YouTube-ready metadata
  - Uses ffmpeg (fast, no re-encoding)
  - Status shown in download progress

#### Planned Features (v2.0+)
1. **Enhanced Video Player**
   - Highlight tag navigation
   - Trim/split functionality
   - Better timeline scrubbing

2. **Batch Operations**
   - Batch rename
   - Batch convert formats
   - Batch delete

3. **Advanced Settings**
   - All 80+ gphoto2 properties in GUI
   - Settings profiles
   - Backup/restore settings

4. **Tethered Shooting**
   - Remote capture
   - Intervalometer
   - Bulb mode control

---

## 6. Technical Implementation Details

### 6.1 Dependencies

#### Core Dependencies
```
Python 3.8+
├── gphoto2 (system package)
├── libgphoto2 (system package)
├── tkinter (built-in)
├── usb1 (for raw PTP)
└── python3-gi (optional, for native GTK dialogs)
```

#### GUI Application
```
├── tkinter (built-in)
├── subprocess (built-in)
├── threading (built-in)
├── pathlib (built-in)
└── gi (optional, for native file dialogs)
```

#### 360° Viewer
```
├── numpy (for projection math)
├── Pillow (PIL) (image handling)
└── opencv-python (optional, for video support)
```

#### YouTube Export
```
├── ffmpeg (system package)
└── spatialmedia (optional, pip install spatialmedia)
```

#### Installation Commands
```bash
# Core
sudo apt-get install gphoto2 libgphoto2-dev
pip install libusb1

# For 360° Viewer
pip install numpy Pillow opencv-python

# For YouTube Export (optional but recommended)
pip install spatialmedia
```

### 6.2 Communication Methods

#### Method 1: gphoto2 CLI (Preferred for GUI)
```python
subprocess.run(['gphoto2', '--list-files'], capture_output=True)
```
- Pros: Stable, well-tested, handles session management
- Cons: Process overhead, parsing required

#### Method 2: Raw PTP (km360_formatter.py)
```python
usb1.USBContext() → bulkWrite() → bulkRead()
```
- Pros: Direct control, no dependencies
- Cons: Complex, manual session handling

#### Method 3: python-gphoto2 (Future)
```python
import gphoto2 as gp
camera = gp.Camera()
```
- Pros: Native Python, clean API
- Cons: Additional dependency, may have issues

### 6.3 Error Handling
- Camera not connected
- USB permission denied
- Device busy
- Storage full
- Transfer interrupted

### 6.4 Threading Model
- Main thread: UI
- Worker thread: File operations
- Callbacks: Progress updates

---

## 7. File Formats

### 7.1 Camera Output
- **Photos**: JPEG (7744×3872, equirectangular)
- **Videos**: MP4 (H.264/MPEG-4 AVC, AAC stereo)
- **Thumbnails**: JPEG (embedded in EXIF)

### 7.2 360° Metadata
The camera embeds 360° metadata in:
- **Photos**: EXIF tags for spherical projection
- **Videos**: Spatial Media metadata (Google format)

### 7.3 Projection Types
- **Equirectangular** (Plate Carree): Native camera output
- **Cubemap**: For some players
- **Dual Fisheye**: Raw lens output

---

## 8. WiFi Configuration

### 8.1 Camera as AP
- SSID: KM360_<serial> (stored in d338)
- Password: NikonKeyMission (stored in d340)
- Default IP: 192.168.0.10 (d342)
- Subnet: 255.255.255.0 (d343)
- Channel: 6 (d341)

### 8.2 Protocol
The camera uses:
- **Bluetooth**: For pairing/initiation
- **WiFi**: For data transfer (SnapBridge)
- **PTP/IP**: PTP over IP (WiFi)

Note: WiFi features not accessible via USB gphoto2 - requires separate implementation.

---

## 9. Known Issues & Limitations

### 9.1 Hardware
- No live view over USB
- USB charging supported when camera is on but idle (may require "Charge By Computer" setting)
- USB charging likely NOT supported during active video recording (unverified)
- HDMI output + charging behavior unknown (unverified)
- Battery level readable via gphoto2 (`/main/status/batterylevel`)
- Charging status NOT available via USB/PTP protocol (check camera LED - blinking = charging)
- Battery life: ~1h 10min recording
- Gets warm during 4K recording

### 9.2 Software
- Date/time resets on battery removal
- Some settings read-only via USB
- Live view error 0x00800000 (intentionally blocked)
- gphoto2 movie toggle may not work reliably

### 9.3 Windows App Issues
- Slow thumbnail loading for large files
- 4K playback requires good GPU
- 4GB file limit on FAT32 destinations

---

## 10. Future Research

### 10.1 Investigation Needed
1. **PTP/IP over WiFi** - Can we connect via WiFi and use PTP?
2. **Movie Mode values (d304)** - The camera supports Standard, Loop, Timelapse, and Superlapse modes. What do values 0-3 correspond to?
3. **Movie Loop Length interaction** - Does movielooplength only affect Loop Recording mode, or all recording?
4. **Movie Screen Size values (d0a0)** - How do values 10/20/40/80/90 map to resolutions?
5. **Full format vs Quick format** - Is there a difference?
6. **Progress events** - Can we get format progress?

### 10.2 Potential Enhancements
1. **HDR/DNG support** - Does camera support raw capture?
2. **GPS data** - How is location data embedded?
3. **Firmware updates** - Can we trigger/update via USB?
4. **Remote control** - Full remote shooting capability

---

## 11. References

### 11.1 Documentation
- [PTP Specification](http://www.ntfs.com/img/15740-3.pdf) - PIMA 15740:2000
- [gphoto2 Manual](http://www.gphoto.org/doc/manual/)
- [libgphoto2 Source](https://github.com/gphoto/libgphoto2)

### 11.2 Tools Used
- `gphoto2` - Camera control
- `libusb1` / `pyusb` - Raw USB
- `ffmpeg` - Video processing
- `strings` - Binary analysis
- `7z` - Archive extraction

### 11.3 Reverse Engineering
- Windows App: KeyMissionUtility.exe v1.1.0
- Analysis Method: String extraction, DLL inspection
- Findings: 80+ gphoto2 properties, 360° projection algorithms

---

## 12. Community

### 12.1 KeyMission 360 Resources
- [360rumors.com](https://360rumors.com/nikon-keymission-360-preliminary-review/) - Reviews and comparisons
- [Nikon Support](https://www.nikonusa.com/p/keymission-360/26513/overview) - Official specs (archive)

### 12.2 Places to Share This Project
- [r/360Cameras](https://reddit.com/r/360Cameras) - 360° camera community
- [r/Nikon](https://reddit.com/r/Nikon) - Nikon users
- [r/ActionCameras](https://reddit.com/r/ActionCameras) - Action cam enthusiasts
- [r/DataHoarder](https://reddit.com/r/DataHoarder) - For recovery/restoration projects

### 12.3 Target Audience
This project is especially valuable for:
- Users who can no longer install the official SnapBridge app (discontinued)
- Linux users who never had official support
- Users wanting batch operations or automation
- Technical users wanting low-level camera control

---

## Changelog

### v1.8 (2026-03-12)
- **Bug Fixes**:
  - **Fixed download not working**: Removed undefined `youtube_mode` reference
  - **Fixed hidden buttons**: Increased dialog sizes and added `minsize` constraints
  - **Fixed black popup after file dialog**: Added tkinter window refresh after GTK dialogs
  - **Fixed individual file progress bar**: Uses stdout streaming (`--stdout`) to track bytes in real-time
  - **Fixed app not closing**: Removed `grab_set()` from dialogs, added proper `WM_DELETE_WINDOW` handlers
  - **Fixed connection hang**: Connection attempts now run in threads with shorter timeouts
  - **Improved partial file handling**: Firefox-style `.part` files kept in target location for resume
  - **Real progress tracking**: Progress bar updates every 0.2s based on actual bytes received
  - **File browser filtering**: Only shows image and video files, hides system files
  - **Debug output**: Shows temp file location in status bar and console

### v1.7 (2026-03-11)
- **NEW**: Configuration Module (`km360_config.py`)
  - Native GTK/KDE file dialogs with Places sidebar
  - Remembers last download directory
  - Settings persistence in `~/.config/km360/`
- **NEW**: Desktop Installer (`km360_install_desktop.py`)
  - Add to GNOME/KDE/XFCE Start Menu
  - Generates application icon automatically
- **GUI Enhancements**:
  - **Removed separate YouTube Export tab** - metadata now auto-injected for all videos
  - **Download options dialog** with "Remove from camera" checkbox
  - **USB port memory** - remembers last port for faster reset
  - **Fixed right-click delete** - now works with proper camera folder paths
  - File browser stores actual gphoto2 file numbers for accuracy
- **YouTube Integration**:
  - All video downloads automatically get 360° metadata injected
  - Uses ffmpeg (fast, no re-encoding)
  - Videos are YouTube-ready immediately after download

### v1.6 (2026-03-10)
- **NEW**: Reliable Download Tool (`km360_download.py`)
  - SHA256 checksum verification
  - Resume support for partial downloads
  - Automatic retry with exponential backoff
  - Command-line interface
- **NEW**: USB Reset Tool (`km360_usb_reset.py`)
  - Reset USB port without unplugging camera
  - Multiple reset methods
  - GUI integration with "🔄 Reset USB" button
- **GUI Enhancements**:
  - Download Manager with progress bars and cancel buttons
  - Batch file selection (Ctrl+A, Ctrl+Click, Shift+Click)
  - File integrity verification (checksums)
  - Download warning dialog for 360° Viewer (shows file size)
  - YouTube Export ignores non-video files when batch selecting
  - Retry failed downloads button
- **Improved Error Handling**:
  - Detailed error messages for failed downloads
  - Size mismatch detection
  - Corrupt file detection via checksums

### v1.5 (2026-03-10)
- **NEW**: 360° Image/Video Viewer (`km360_viewer.py`)
  - Interactive equirectangular viewer
  - Mouse/keyboard controls
  - Video playback support
- **NEW**: YouTube Export Tool (`km360_youtube_export.py`)
  - Metadata injection (no re-encode)
  - Batch processing
- **GUI Updates**:
  - Right-click context menus on file browser
  - Viewer/Exporter integration
  - Quick Open dropdown in Viewer tab
- All tools now support `--headless` test mode

### v1.0 (2026-03-10)
- Initial release
- km360_gui.py: Main GUI application
- km360_formatter.py: SD card formatter
- km360_set_time.py: Time synchronization
- km360_info.py: Camera information
- Complete gphoto2 property documentation

---

*Document Version: 1.8*
*Date: 2026-03-12*
*Authors: AI Assistant / Claude Code*
