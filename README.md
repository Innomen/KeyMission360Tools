# KeyMission 360 Tools

A local Linux control center and CLI for the Nikon KeyMission 360.

The desktop app handles the routine camera workflow: see connection state and camera media,
choose a destination, download with size and SHA-256 verification, clear the camera with an
explicit confirmation, synchronize its clock, and reach diagnostics and advanced tools.

The CLI exposes the full toolkit for scripting and repair work: camera information, storage
formatting, time sync, downloads, deletion, USB reset, 360 viewing, spherical metadata, lossless
video merging, Wi-Fi configuration, and camera settings.

## Safety model

- Downloads use a `.partial` file and become final only after the camera-reported size matches.
- Completed downloads receive a SHA-256 checksum.
- Delete-all is one camera-native operation, not a fragile loop over changing file numbers.
- A deletion is reported successful only after the camera is queried again and reports empty.
- Formatting and deletion require confirmation unless the CLI caller explicitly supplies `--force`.
- The application has no cloud service or telemetry. See [PRIVACY.md](PRIVACY.md).

## Install

```bash
# Arch / Garuda
sudo pacman -S gphoto2 ffmpeg perl-image-exiftool tk

python3 -m pip install -r requirements.txt
python3 km360_install_desktop.py --force
```

The desktop installer pins the exact Python interpreter used during installation. This matters
because application menus use a minimal environment and may otherwise select a different Python.

For non-root camera access, install the included udev rule described in [QUICKSTART.md](QUICKSTART.md).

## Desktop workflow

1. Connect and power on the camera.
2. Open **KeyMission 360** from the application menu.
3. Choose a download destination.
4. Select **Download all safely**.
5. Check the completion message, then use **Erase camera media** when desired.

The KeyMission 360 has no persistent real-time clock. Use **Sync camera clock** after a battery has
been removed or depleted.

## Sphere Viewer

Select **Open 360 photo or video** inside the control center. The viewer opens a local file directly
in the same application process.

- Drag to look around the sphere.
- Use the mouse wheel to zoom.
- Keep the horizon guide visible and adjust **Roll** until walls, poles, and other vertical features
  stand upright.
- Use the ±90° buttons when the camera was held sideways or upside down.
- Arrange the scene until it looks correct, then choose **Make current view level**. The viewer
  preserves that exact visible pose while resetting the navigation frame, so left/right/up/down are
  screen-relative again.
- **Export leveled copy** rotates the panorama on the sphere and preserves the equirectangular 2:1
  canvas. It never overwrites the original.

Do not rotate a stitched panorama in a flat photo editor. That rotates rectangular pixels rather
than the represented sphere, mangling the seam, poles, and horizon.

## CLI

```bash
./km360 check
./km360 info
./km360 time
./km360 list
./km360 download --all --output ~/Pictures/KeyMission360
./km360 delete --all
./km360 viewer photo.jpg
./km360 youtube --in-place video.mp4
./km360 merge --output joined.mp4 part1.mp4 part2.mp4
./km360 settings --show
./km360 wifi --ssid MyCamera --channel 6
```

Run `./km360 COMMAND --help` for command-specific options. The protocol findings behind the camera
support live in [RESEARCH.md](RESEARCH.md), with the gphoto property catalog in
[GPHOTO2_COMMANDS.md](GPHOTO2_COMMANDS.md).

## Development

```bash
python3 -m unittest discover -s tests -v
python3 test_suite.py
python3 -m py_compile km360 km360_*.py
ruff check km360_core.py km360_gui.py km360_install_desktop.py tests/
```

GUI checks must run on a virtual display so development never steals desktop focus:

```bash
xvfb-run -a python3 km360_gui.py
```

Hardware tests should use read-only camera commands unless a test explicitly covers a confirmed
download, deletion, time sync, or format operation.

## Project structure

| File | Purpose |
|---|---|
| `km360_core.py` | Shared camera operations and parsing |
| `km360_gui.py` | Desktop control center |
| `km360` | Full standalone CLI |
| `km360_config.py` | Local preferences and native dialogs |
| `km360_viewer.py` | Interactive 360 media viewer |
| `VIEWER_ARCHITECTURE.md` | Shared embedded/standalone viewer design and SphereView audit |
| `km360_merge.py` | Lossless split-video joining |
| `km360_youtube_export.py` | Spherical metadata handling |
| `km360_install_desktop.py` | KDE/GNOME application-menu integration |

MIT licensed.
