#!/usr/bin/env python3
"""
Nikon KeyMission 360 Camera Information Tool
============================================

Displays detailed information about the connected KeyMission 360 camera
without performing any destructive operations.
"""

import usb1
import struct
import sys

VENDOR_ID = 0x04b0
PRODUCT_ID = 0x019f

PTP_CONTAINER_COMMAND = 0x0001
PTP_CONTAINER_DATA = 0x0002
PTP_CONTAINER_RESPONSE = 0x0003
ENDPOINT_TYPE_BULK = 0x02
ENDPOINT_DIR_IN = 0x80


def get_string_descriptor(device, index):
    """Get USB string descriptor"""
    try:
        return device.getStringDescriptor(index, 0x0409)
    except:
        return "N/A"


def main():
    print("=" * 60)
    print("Nikon KeyMission 360 Camera Information")
    print("=" * 60)
    print()
    
    with usb1.USBContext() as context:
        # Find camera
        device = None
        for dev in context.getDeviceIterator(skip_on_error=True):
            if dev.getVendorID() == VENDOR_ID and dev.getProductID() == PRODUCT_ID:
                device = dev
                break
        
        if not device:
            print("[!] Camera not found!")
            print("    Make sure the KeyMission 360 is connected via USB.")
            sys.exit(1)
        
        # USB Device Information
        print("USB Device Information:")
        print("-" * 60)
        print(f"  Vendor ID:      0x{device.getVendorID():04X}")
        print(f"  Product ID:     0x{device.getProductID():04X}")
        print(f"  Bus:            {device.getBusNumber()}")
        print(f"  Device Address: {device.getDeviceAddress()}")
        print(f"  Speed:          {device.getDeviceSpeed()}")
        
        # Device descriptor info
        try:
            desc = device.device_descriptor
            print(f"  USB Version:    {desc.bcdUSB >> 8}.{(desc.bcdUSB >> 4) & 0x0F}{(desc.bcdUSB) & 0x0F}")
            print(f"  Device Class:   0x{desc.bDeviceClass:02X}")
            print(f"  Device Subclass: 0x{desc.bDeviceSubClass:02X}")
            print(f"  Device Protocol: 0x{desc.bDeviceProtocol:02X}")
            print(f"  Max Packet Size: {desc.bMaxPacketSize0}")
        except Exception as e:
            print(f"  Error reading descriptor: {e}")
        
        # String descriptors
        print()
        print("Device Strings:")
        print("-" * 60)
        try:
            print(f"  Manufacturer:   {get_string_descriptor(device, device.device_descriptor.iManufacturer)}")
            print(f"  Product:        {get_string_descriptor(device, device.device_descriptor.iProduct)}")
            print(f"  Serial Number:  {get_string_descriptor(device, device.device_descriptor.iSerialNumber)}")
        except Exception as e:
            print(f"  Error reading strings: {e}")
        
        # Open device for PTP communication
        print()
        print("PTP Communication:")
        print("-" * 60)
        
        handle = device.open()
        handle.setConfiguration(1)
        
        # Detach kernel drivers
        for i in range(4):
            try:
                if handle.kernelDriverActive(i):
                    handle.detachKernelDriver(i)
            except:
                pass
        
        # Get endpoints
        config = device[0]
        setting = next(config[0].iterSettings())
        interface_num = setting.getNumber()
        handle.claimInterface(interface_num)
        
        bulk_in = bulk_out = None
        for ep in setting.iterEndpoints():
            addr = ep.getAddress()
            attrs = ep.getAttributes()
            if (attrs & 0x03) == ENDPOINT_TYPE_BULK:
                if addr & ENDPOINT_DIR_IN:
                    bulk_in = addr
                else:
                    bulk_out = addr
        
        print(f"  Interface:      {interface_num}")
        print(f"  Bulk OUT:       0x{bulk_out:02X}")
        print(f"  Bulk IN:        0x{bulk_in:02X}")
        
        # Open PTP session and get device info
        trans_id = 1
        
        # Open session
        session = struct.pack('<IHHII', 16, PTP_CONTAINER_COMMAND, 0x1002, trans_id, 1)
        handle.bulkWrite(bulk_out, session, timeout=5000)
        resp = handle.bulkRead(bulk_in, 512, timeout=5000)
        
        # Get device info (opcode 0x1001)
        trans_id += 1
        devinfo_cmd = struct.pack('<IHHII', 16, PTP_CONTAINER_COMMAND, 0x1001, trans_id, 0)
        handle.bulkWrite(bulk_out, devinfo_cmd, timeout=5000)
        
        # Read data phase
        data = handle.bulkRead(bulk_in, 1024, timeout=5000)
        # Read response
        resp = handle.bulkRead(bulk_in, 512, timeout=5000)
        
        # Parse device info
        if len(data) > 12:
            print()
            print("Device Info:")
            print("-" * 60)
            
            # Parse PTP DeviceInfo structure
            offset = 12
            
            # Standard Version
            if offset + 2 <= len(data):
                std_version = struct.unpack('<H', bytes(data[offset:offset+2]))[0]
                print(f"  Standard Version: {std_version >> 8}.{(std_version >> 4) & 0x0F}{std_version & 0x0F}")
                offset += 2
            
            # Vendor Extension ID
            if offset + 4 <= len(data):
                vendor_ext_id = struct.unpack('<I', bytes(data[offset:offset+4]))[0]
                print(f"  Vendor Ext ID:    0x{vendor_ext_id:08X}")
                offset += 4
            
            # Vendor Extension Version
            if offset + 2 <= len(data):
                vendor_ext_ver = struct.unpack('<H', bytes(data[offset:offset+2]))[0]
                print(f"  Vendor Ext Ver:   {vendor_ext_ver}")
                offset += 2
            
            # Skip strings (each has length byte + UTF-16LE chars)
            # This is simplified parsing
            
        # Get storage IDs
        trans_id += 1
        storage_cmd = struct.pack('<IHHII', 16, PTP_CONTAINER_COMMAND, 0x1004, trans_id, 0)
        handle.bulkWrite(bulk_out, storage_cmd, timeout=5000)
        
        data = handle.bulkRead(bulk_in, 512, timeout=5000)
        resp = handle.bulkRead(bulk_in, 512, timeout=5000)
        
        print()
        print("Storage Devices:")
        print("-" * 60)
        
        if len(data) >= 12:
            count = struct.unpack('<I', bytes(data[8:12]))[0]
            print(f"  Count: {count}")
            
            for i in range(count):
                offset = 12 + (i * 4)
                if offset + 4 <= len(data):
                    storage_id = struct.unpack('<I', bytes(data[offset:offset+4]))[0]
                    print(f"  Storage {i+1}:       0x{storage_id:08X}", end="")
                    
                    if storage_id == 0x00000001:
                        print(" (Internal)")
                    elif storage_id == 0x00010001:
                        print(" (SD Card)")
                    else:
                        print()
        
        handle.releaseInterface(interface_num)
        
        print()
        print("=" * 60)
        print("Information gathering complete.")
        print("=" * 60)


if __name__ == "__main__":
    main()
