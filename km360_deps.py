#!/usr/bin/env python3
"""
KeyMission 360 - Dependency Manager
====================================

Smart dependency checking with optional auto-installation.

This module provides:
- Detection of missing dependencies
- Automatic installation prompts
- Package manager detection (apt, pacman, brew, pip)
- Graceful degradation with fallbacks

Author: KeyMission 360 Tools Project
License: MIT
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Callable


class Dependency:
    """Represents a single dependency"""

    def __init__(
        self,
        name: str,
        check_func: Callable,
        install_cmds: Dict[str, List[str]],
        optional: bool = False,
        description: str = "",
        fallback_msg: str = "",
    ):
        """
        Args:
            name: Human-readable name
            check_func: Function that returns True if dependency is available
            install_cmds: Dict mapping package manager to install commands
            optional: Whether this is optional (non-blocking)
            description: What this dependency is for
            fallback_msg: Message to show if dependency is missing
        """
        self.name = name
        self.check_func = check_func
        self.install_cmds = install_cmds
        self.optional = optional
        self.description = description
        self.fallback_msg = fallback_msg
        self._available = None

    def is_available(self) -> bool:
        """Check if dependency is available (cached)"""
        if self._available is None:
            try:
                self._available = self.check_func()
            except:
                self._available = False
        return self._available

    def get_install_command(self) -> Optional[List[str]]:
        """Get install command for current system"""
        pm = detect_package_manager()
        if pm in self.install_cmds:
            return self.install_cmds[pm]
        return None


def detect_package_manager() -> str:
    """Detect the system's package manager"""
    # Check for various package managers
    if shutil.which("pacman"):
        return "pacman"
    elif shutil.which("apt-get"):
        return "apt"
    elif shutil.which("brew"):
        return "brew"
    elif shutil.which("pip3"):
        return "pip"
    elif shutil.which("pip"):
        return "pip"
    return "unknown"


def detect_distro() -> str:
    """Detect Linux distribution family"""
    try:
        if Path("/etc/arch-release").exists():
            return "arch"
        elif Path("/etc/debian_version").exists():
            return "debian"
        elif Path("/etc/fedora-release").exists():
            return "fedora"
    except:
        pass
    return "unknown"


def check_python_module(module_name: str) -> bool:
    """Check if a Python module is installed"""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def check_system_command(command: str, args: List[str] = ["--version"]) -> bool:
    """Check if a system command is available"""
    try:
        result = subprocess.run([command] + args, capture_output=True, timeout=5)
        return result.returncode == 0
    except:
        return False


def check_usb_lib() -> bool:
    """Check for USB library (libusb1 or pyusb)"""
    return check_python_module("usb1") or check_python_module("usb.core")


def check_ffmpeg() -> bool:
    """Check for ffmpeg"""
    return check_system_command("ffmpeg", ["-version"])


def check_ffprobe() -> bool:
    """Check for ffprobe"""
    return check_system_command("ffprobe", ["-version"])


def check_exiftool() -> bool:
    """Check for exiftool"""
    return check_system_command("exiftool", ["-ver"])


def check_gphoto2() -> bool:
    """Check for gphoto2"""
    return check_system_command("gphoto2", ["--version"])


def check_tkinter() -> bool:
    """Check for tkinter"""
    return check_python_module("tkinter")


def check_numpy() -> bool:
    """Check for numpy"""
    return check_python_module("numpy")


def check_pillow() -> bool:
    """Check for PIL/Pillow"""
    return check_python_module("PIL")


def check_opencv() -> bool:
    """Check for OpenCV"""
    return check_python_module("cv2")


def check_usbreset() -> bool:
    """Check for usbreset utility"""
    return shutil.which("usbreset") is not None


# Define all dependencies
DEPENDENCIES = {
    "gphoto2": Dependency(
        name="gphoto2",
        check_func=check_gphoto2,
        install_cmds={
            "pacman": ["sudo", "pacman", "-S", "--noconfirm", "gphoto2", "libgphoto2"],
            "apt": ["sudo", "apt-get", "install", "-y", "gphoto2", "libgphoto2-dev"],
            "brew": ["brew", "install", "gphoto2"],
        },
        optional=False,
        description="Camera communication (required for most operations)",
        fallback_msg="Camera operations will not work without gphoto2",
    ),
    "libusb1": Dependency(
        name="libusb1 (Python)",
        check_func=lambda: check_python_module("usb1"),
        install_cmds={
            "pip": [sys.executable, "-m", "pip", "install", "libusb1"],
        },
        optional=True,
        description="Raw USB/PTP communication (optional but recommended)",
        fallback_msg="Will use gphoto2 fallback for PTP commands",
    ),
    "ffmpeg": Dependency(
        name="ffmpeg",
        check_func=check_ffmpeg,
        install_cmds={
            "pacman": ["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"],
            "apt": ["sudo", "apt-get", "install", "-y", "ffmpeg"],
            "brew": ["brew", "install", "ffmpeg"],
        },
        optional=True,
        description="Video processing (YouTube export, merging, viewer)",
        fallback_msg="Video operations will be unavailable",
    ),
    "exiftool": Dependency(
        name="exiftool",
        check_func=check_exiftool,
        install_cmds={
            "pacman": ["sudo", "pacman", "-S", "--noconfirm", "perl-image-exiftool"],
            "apt": ["sudo", "apt-get", "install", "-y", "libimage-exiftool-perl"],
            "brew": ["brew", "install", "exiftool"],
        },
        optional=True,
        description="360° metadata injection (best quality)",
        fallback_msg="360° metadata injection may not work correctly",
    ),
    "tkinter": Dependency(
        name="tkinter",
        check_func=check_tkinter,
        install_cmds={
            "pacman": ["sudo", "pacman", "-S", "--noconfirm", "tk"],
            "apt": ["sudo", "apt-get", "install", "-y", "python3-tk"],
        },
        optional=True,
        description="GUI components",
        fallback_msg="GUI mode will not be available",
    ),
    "numpy": Dependency(
        name="numpy",
        check_func=check_numpy,
        install_cmds={
            "pip": [sys.executable, "-m", "pip", "install", "numpy"],
        },
        optional=True,
        description="360° viewer math operations",
        fallback_msg="360° viewer will not be available",
    ),
    "pillow": Dependency(
        name="Pillow (PIL)",
        check_func=check_pillow,
        install_cmds={
            "pip": [sys.executable, "-m", "pip", "install", "Pillow"],
        },
        optional=True,
        description="Image processing for viewer",
        fallback_msg="360° viewer will not be available",
    ),
    "opencv": Dependency(
        name="opencv-python",
        check_func=check_opencv,
        install_cmds={
            "pip": [sys.executable, "-m", "pip", "install", "opencv-python"],
        },
        optional=True,
        description="Video playback in 360° viewer",
        fallback_msg="360° video viewer will not be available",
    ),
    "usbreset": Dependency(
        name="usbreset",
        check_func=check_usbreset,
        install_cmds={
            "manual": [],  # Requires manual compilation
        },
        optional=True,
        description="USB port reset utility",
        fallback_msg="USB reset will use alternative methods",
    ),
}


def check_all_deps() -> Dict[str, Dependency]:
    """Check all dependencies and return status"""
    for dep in DEPENDENCIES.values():
        dep.is_available()  # Trigger check
    return DEPENDENCIES


def get_missing_deps(optional: bool = True) -> List[Dependency]:
    """Get list of missing dependencies"""
    missing = []
    for dep in DEPENDENCIES.values():
        if not dep.is_available():
            if not dep.optional or optional:
                missing.append(dep)
    return missing


def install_dependency(dep: Dependency, dry_run: bool = False) -> bool:
    """
    Attempt to install a dependency.

    Args:
        dep: Dependency to install
        dry_run: If True, only print what would be done

    Returns:
        True if successful or dry_run, False otherwise
    """
    cmd = dep.get_install_command()

    if not cmd:
        print(f"  ⚠ No automatic install available for {dep.name}")
        if dep.name == "usbreset":
            print("  Manual install for usbreset:")
            print("    sudo apt-get install usbutils  # Ubuntu/Debian")
            print("    # or compile from: https://github.com/ralight/usbreset")
        return False

    print(f"  Installing {dep.name}...")
    print(f"  Command: {' '.join(cmd)}")

    if dry_run:
        return True

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"  ✓ {dep.name} installed successfully")
            # Invalidate cache
            dep._available = None
            return True
        else:
            print(f"  ✗ Installation failed: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print("  ✗ Installation timed out")
        return False
    except Exception as e:
        print(f"  ✗ Installation error: {e}")
        return False


def check_and_install_interactive(
    auto_install: bool = False, check_usb_reset: bool = False
) -> bool:
    """
    Check dependencies and optionally install missing ones.

    Args:
        auto_install: If True, install without prompting
        check_usb_reset: Also check USB reset capabilities

    Returns:
        True if all critical dependencies are available
    """
    print("=" * 60)
    print("KeyMission 360 - Dependency Check")
    print("=" * 60)
    print()

    # Check all dependencies
    deps = check_all_deps()

    # Categorize
    missing_required = []
    missing_optional = []

    for dep in deps.values():
        if not dep.is_available():
            if dep.optional:
                missing_optional.append(dep)
            else:
                missing_required.append(dep)

    # Show status
    if not missing_required and not missing_optional:
        print("✓ All dependencies satisfied!")
        if check_usb_reset:
            print()
            check_usb_reset_capabilities()
        return True

    # Show missing required
    if missing_required:
        print("✗ Missing REQUIRED dependencies:")
        for dep in missing_required:
            print(f"  • {dep.name}: {dep.description}")
            print(f"    {dep.fallback_msg}")
        print()

    # Show missing optional
    if missing_optional:
        print("⚠ Missing OPTIONAL dependencies:")
        for dep in missing_optional:
            print(f"  • {dep.name}: {dep.description}")
        print()

    # Check USB reset if requested
    if check_usb_reset:
        check_usb_reset_capabilities()
        print()

    # Can't proceed without required deps
    if missing_required:
        if auto_install:
            print("Auto-installing required dependencies...")
            for dep in missing_required:
                install_dependency(dep)

            # Re-check
            still_missing = [d for d in missing_required if not d.is_available()]
            if still_missing:
                print("\n✗ Some required dependencies could not be installed.")
                return False
            return True
        else:
            response = input("Install missing dependencies? [Y/n]: ")
            if response.lower() not in ["n", "no"]:
                for dep in missing_required:
                    install_dependency(dep)

                # Re-check
                still_missing = [d for d in missing_required if not d.is_available()]
                if still_missing:
                    print("\n✗ Some required dependencies could not be installed.")
                    return False
                return True
            else:
                print("\n✗ Cannot proceed without required dependencies.")
                return False

    # Optional deps only
    if missing_optional and not auto_install:
        response = input("Install optional dependencies? [y/N]: ")
        if response.lower() in ["y", "yes"]:
            for dep in missing_optional:
                install_dependency(dep)

    return True


def check_usb_reset_capabilities():
    """Check USB reset methods and their availability"""
    print("USB Reset Capabilities:")

    methods = []

    # Check pyusb/libusb1
    if check_python_module("usb.core") or check_python_module("usb1"):
        methods.append(("USB library (pyusb/libusb1)", True, "Preferred method"))
    else:
        methods.append(
            ("USB library (pyusb/libusb1)", False, "Install: pip install libusb1")
        )

    # Check usbreset
    if check_usbreset():
        methods.append(("usbreset utility", True, "Fast and reliable"))
    else:
        methods.append(
            ("usbreset utility", False, "Package: usbutils or compile manually")
        )

    # Check sysfs access
    sysfs_available = os.access("/sys", os.W_OK) if os.path.exists("/sys") else False
    if sysfs_available:
        methods.append(
            ("sysfs authorized toggle", True, "Requires root without udev rules")
        )
    else:
        methods.append(("sysfs authorized toggle", True, "May require sudo"))

    for name, available, note in methods:
        status = "✓" if available else "✗"
        print(f"  [{status}] {name}: {note}")

    # Recommend udev rules
    udev_path = Path("/etc/udev/rules.d/99-keymission360.rules")
    if not udev_path.exists():
        print()
        print("Tip: Install udev rules for non-root USB access:")
        print("  km360 install --udev")


def get_dependency_status() -> Dict[str, any]:
    """Get a dict with all dependency status info"""
    return {
        "package_manager": detect_package_manager(),
        "distro": detect_distro(),
        "dependencies": {
            name: {
                "available": dep.is_available(),
                "optional": dep.optional,
                "install_cmd": dep.get_install_command(),
            }
            for name, dep in DEPENDENCIES.items()
        },
    }


def print_dependency_report():
    """Print a full dependency report"""
    status = get_dependency_status()

    print("=" * 60)
    print("KeyMission 360 - Dependency Report")
    print("=" * 60)
    print()
    print(f"Package Manager: {status['package_manager']}")
    print(f"Distribution: {status['distro']}")
    print()

    print("Dependencies:")
    for name, info in status["dependencies"].items():
        symbol = "✓" if info["available"] else "✗"
        optional = "(optional)" if info["optional"] else "(REQUIRED)"
        print(f"  [{symbol}] {name} {optional}")

    print()
    print("To install missing dependencies:")
    print("  km360 deps --install        # Interactive install")
    print("  km360 deps --install-all    # Install all missing")
    print("  km360 check                 # Check with USB reset info")


def ensure_dependencies(command: str, auto_install: bool = False) -> bool:
    """
    Ensure dependencies needed for a specific command are available.

    Args:
        command: Command name (info, format, download, youtube, merge, reset, etc.)
        auto_install: Auto-install missing dependencies

    Returns:
        True if dependencies are satisfied
    """
    # Define required deps per command
    command_deps = {
        "info": ["gphoto2"],
        "format": ["gphoto2", "libusb1"],
        "time": ["gphoto2"],
        "list": ["gphoto2"],
        "download": ["gphoto2", "ffmpeg"],
        "youtube": ["ffmpeg"],
        "merge": ["ffmpeg", "exiftool"],
        "reset": ["libusb1"],  # Can work without, but better with
        "viewer": ["tkinter", "numpy", "pillow"],
        "wifi": ["gphoto2"],
        "settings": ["gphoto2"],
        "gui": ["gphoto2", "tkinter", "numpy", "pillow"],
    }

    needed = command_deps.get(command, [])
    if not needed:
        return True

    missing = []
    for dep_name in needed:
        if dep_name in DEPENDENCIES:
            dep = DEPENDENCIES[dep_name]
            if not dep.is_available():
                missing.append(dep)

    if not missing:
        return True

    print(f"[{command}] Missing dependencies:")
    for dep in missing:
        print(f"  • {dep.name}: {dep.description}")

    if auto_install:
        print("\nAuto-installing...")
        for dep in missing:
            install_dependency(dep)

        # Re-check
        still_missing = [d for d in missing if not d.is_available()]
        return len(still_missing) == 0
    else:
        response = input("\nInstall missing dependencies? [Y/n]: ")
        if response.lower() not in ["n", "no"]:
            for dep in missing:
                install_dependency(dep)
            still_missing = [d for d in missing if not d.is_available()]
            return len(still_missing) == 0

    return len(missing) == 0 or all(d.optional for d in missing)


if __name__ == "__main__":
    # Allow running standalone for dependency checks
    import argparse

    parser = argparse.ArgumentParser(description="KeyMission 360 Dependency Manager")
    parser.add_argument(
        "--check", "-c", action="store_true", help="Check all dependencies"
    )
    parser.add_argument(
        "--install", "-i", action="store_true", help="Interactive install"
    )
    parser.add_argument(
        "--install-all", "-a", action="store_true", help="Install all missing"
    )
    parser.add_argument("--for", dest="command", help="Check deps for specific command")
    parser.add_argument(
        "--usb-reset", "-u", action="store_true", help="Check USB reset capabilities"
    )

    args = parser.parse_args()

    if args.command:
        ok = ensure_dependencies(args.command, auto_install=args.install_all)
        sys.exit(0 if ok else 1)
    elif args.install or args.install_all:
        ok = check_and_install_interactive(
            auto_install=args.install_all, check_usb_reset=args.usb_reset
        )
        sys.exit(0 if ok else 1)
    elif args.check or args.usb_reset:
        check_and_install_interactive(
            auto_install=False, check_usb_reset=args.usb_reset
        )
    else:
        print_dependency_report()
