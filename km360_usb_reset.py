#!/usr/bin/env python3
"""
Nikon KeyMission 360 USB Port Reset Tool
========================================

Resets the USB port that the KeyMission 360 camera is connected to.
Useful when the camera becomes unresponsive or times out.

Usage:
    python3 km360_usb_reset.py
    sudo python3 km360_usb_reset.py  # If permission errors occur

Author: KeyMission 360 Tools Project
License: MIT
"""

import sys
import subprocess
import argparse

try:
    import usb1
    USB1_AVAILABLE = True
except ImportError:
    USB1_AVAILABLE = False

try:
    import usb.core
    import usb.util
    PYUSB_AVAILABLE = True
except ImportError:
    PYUSB_AVAILABLE = False

USB_AVAILABLE = USB1_AVAILABLE or PYUSB_AVAILABLE
if not USB_AVAILABLE:
    print("Warning: pyusb/libusb1 not installed. Trying fallback methods...")


VENDOR_ID = 0x04b0  # Nikon
PRODUCT_ID = 0x019f  # KeyMission 360


def find_camera():
    """Find the KeyMission 360 on USB bus"""
    if not USB_AVAILABLE:
        return None, None
    
    # Try libusb1 first (preferred)
    if USB1_AVAILABLE:
        try:
            context = usb1.USBContext()
            for device in context.getDeviceIterator(skip_on_error=True):
                if device.getVendorID() == VENDOR_ID and device.getProductID() == PRODUCT_ID:
                    return device.getBusNumber(), device.getDeviceAddress()
                # Also check for other Nikon cameras
                elif device.getVendorID() == VENDOR_ID:
                    return device.getBusNumber(), device.getDeviceAddress()
        except Exception as e:
            print(f"libusb1 error finding camera: {e}")
    
    # Fallback to pyusb
    if PYUSB_AVAILABLE:
        try:
            dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
            if dev:
                # pyusb doesn't easily give bus/addr, return dummy values
                return 0, 0
            # Try any Nikon device
            dev = usb.core.find(idVendor=VENDOR_ID)
            if dev:
                return 0, 0
        except Exception as e:
            print(f"pyusb error finding camera: {e}")
    
    return None, None


def reset_with_pyusb():
    """Try to reset using pyusb"""
    if not PYUSB_AVAILABLE:
        return False
    
    try:
        dev = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if not dev:
            # Try any Nikon device
            dev = usb.core.find(idVendor=VENDOR_ID)
        
        if dev:
            dev.reset()
            print("✓ USB device reset successful (pyusb)")
            return True
    except Exception as e:
        print(f"pyusb reset failed: {e}")
    
    return False


def reset_with_usbreset(bus, addr):
    """Try to reset using usbreset command"""
    try:
        usbdev = f"/dev/bus/usb/{bus:03d}/{addr:03d}"
        result = subprocess.run(
            ["usbreset", usbdev],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"✓ USB device reset successful (usbreset {usbdev})")
            return True
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"usbreset failed: {e}")
    
    return False


def reset_with_auth_unbind(bus, addr):
    """Try to reset using authorized attribute"""
    try:
        # Find the device path in sysfs
        result = subprocess.run(
            ["find", "/sys/bus/usb/devices", "-name", f"*:{addr}"],
            capture_output=True, text=True, timeout=5
        )
        
        for path in result.stdout.strip().split('\n'):
            if path:
                auth_path = path + "/authorized"
                try:
                    with open(auth_path, 'w') as f:
                        f.write('0')
                    with open(auth_path, 'w') as f:
                        f.write('1')
                    print(f"✓ USB device reset successful (authorized toggle)")
                    return True
                except PermissionError:
                    print(f"Permission denied on {auth_path}, try with sudo")
                except Exception as e:
                    print(f"Error toggling authorized: {e}")
    except Exception as e:
        print(f"auth_unbind failed: {e}")
    
    return False


def list_usb_devices():
    """List all USB devices"""
    print("\nConnected USB devices:")
    print("-" * 50)
    try:
        result = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=5)
        for line in result.stdout.split('\n'):
            if 'Nikon' in line or '04b0' in line:
                print(f"  >>> {line}")
            elif line.strip():
                print(f"      {line}")
    except Exception as e:
        print(f"Could not list USB devices: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Reset USB port for KeyMission 360 camera"
    )
    parser.add_argument("--list", "-l", action="store_true", 
                       help="List USB devices and exit")
    parser.add_argument("--force", "-f", action="store_true",
                       help="Skip confirmation")
    
    args = parser.parse_args()
    
    if args.list:
        list_usb_devices()
        return
    
    print("=" * 50)
    print("KeyMission 360 USB Port Reset")
    print("=" * 50)
    
    bus, addr = find_camera()
    
    if bus is None:
        print("\n⚠ Camera not found on USB bus.")
        print("   Make sure the camera is connected and powered on.")
        list_usb_devices()
        return 1
    
    print(f"\nFound camera at Bus {bus}, Address {addr}")
    
    if not args.force:
        response = input("\nReset USB port? This will briefly disconnect the camera. [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            return 0
    
    print("\nAttempting USB reset...")
    
    # Try methods in order of preference
    # Prefer libusb1 if available, fallback to pyusb
    if PYUSB_AVAILABLE and reset_with_pyusb():
        print("\n✓ Reset successful!")
        print("  Wait a few seconds for the camera to reconnect.")
        return 0
    
    if bus and addr and reset_with_usbreset(bus, addr):
        print("\n✓ Reset successful!")
        print("  Wait a few seconds for the camera to reconnect.")
        return 0
    
    if bus and addr and reset_with_auth_unbind(bus, addr):
        print("\n✓ Reset successful!")
        print("  Wait a few seconds for the camera to reconnect.")
        return 0
    
    print("\n✗ Automatic reset failed.")
    print("\nManual reset options:")
    print("  1. Unplug and replug the USB cable")
    print(f"  2. Run: sudo usbreset /dev/bus/usb/{bus:03d}/{addr:03d}")
    print("  3. Run this script with sudo: sudo python3 km360_usb_reset.py")
    
    return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
