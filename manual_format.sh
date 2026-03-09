#!/bin/bash
#
# manual_format.sh - Format SD card for Nikon KeyMission 360 without camera
#
# This script formats an SD card with the optimal settings for the KeyMission 360.
# The camera expects FAT32 with specific cluster sizes for video recording.
#
# WARNING: This will erase ALL data on the selected device!
#          Double-check the device name before proceeding.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================================"
echo "KeyMission 360 SD Card Manual Formatter"
echo "============================================================"
echo ""
echo -e "${YELLOW}WARNING: This will ERASE ALL DATA on the selected device!${NC}"
echo ""

# Show available disks
echo "Available storage devices:"
echo "--------------------------"
lsblk -d -o NAME,SIZE,TYPE,MODEL | grep -E "disk|NAME"
echo ""

# Get device from user
read -p "Enter device name (e.g., sdc, mmcblk0): " DEVICE_NAME

# Validate input
if [ -z "$DEVICE_NAME" ]; then
    echo -e "${RED}Error: No device specified${NC}"
    exit 1
fi

# Full device path
if [[ "$DEVICE_NAME" == mmcblk* ]]; then
    DEVICE="/dev/${DEVICE_NAME}"
    PARTITION="${DEVICE}p1"
else
    DEVICE="/dev/${DEVICE_NAME}"
    PARTITION="${DEVICE}1"
fi

# Verify device exists
if [ ! -b "$DEVICE" ]; then
    echo -e "${RED}Error: Device $DEVICE does not exist${NC}"
    exit 1
fi

# Show device details
echo ""
echo "Device details:"
echo "---------------"
sudo fdisk -l "$DEVICE" 2>/dev/null | head -20
echo ""

# Final confirmation
echo -e "${RED}===============================================${NC}"
echo -e "${RED}DANGER: About to format:${NC} $DEVICE"
echo -e "${RED}This will DESTROY all data on this device!${NC}"
echo -e "${RED}===============================================${NC}"
echo ""
read -p "Type 'DESTROY' to proceed: " CONFIRM

if [ "$CONFIRM" != "DESTROY" ]; then
    echo -e "${GREEN}Aborted. No changes made.${NC}"
    exit 0
fi

echo ""
echo "[+] Starting format process..."
echo ""

# Unmount any mounted partitions
echo "[*] Unmounting partitions..."
sudo umount "${DEVICE}"* 2>/dev/null || true
sleep 1

# Create new partition table (MSDOS/MBR)
echo "[*] Creating new partition table..."
sudo parted -s "$DEVICE" mklabel msdos

# Create FAT32 partition using all available space
echo "[*] Creating FAT32 partition..."
sudo parted -s "$DEVICE" mkpart primary fat32 1MiB 100%
sleep 1

# Inform kernel of partition table changes
echo "[*] Refreshing partition table..."
sudo partprobe "$DEVICE"
sleep 2

# Verify partition exists
if [ ! -b "$PARTITION" ]; then
    echo -e "${RED}Error: Partition $PARTITION not created${NC}"
    exit 1
fi

# Format with FAT32
# -F 32 = FAT32
# -s 64 = 64 sectors per cluster (32KB clusters)
# -n "KM360" = Volume label
# -I = Ignore safety checks

echo "[*] Formatting with FAT32 (32KB clusters)..."
sudo mkfs.vfat -F 32 -s 64 -n "KM360" -I "$PARTITION"

# Verify format
echo ""
echo "[*] Verifying format..."
sudo fsck.vfat -n "$PARTITION" || true

# Show result
echo ""
echo "============================================================"
echo -e "${GREEN}[✓] Format completed successfully!${NC}"
echo "============================================================"
echo ""
echo "Device: $DEVICE"
echo "Partition: $PARTITION"
echo ""
echo "Disk info:"
sudo fdisk -l "$DEVICE" 2>/dev/null | grep -E "Disk|Device"
echo ""
echo "File system:"
df -h "$PARTITION" 2>/dev/null || true
echo ""
echo "You can now safely remove the SD card and insert it into the camera."
