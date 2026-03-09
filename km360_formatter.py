#!/usr/bin/env python3
"""
Nikon KeyMission 360 Memory Card Formatter
==========================================

A Python tool to format the SD card of a Nikon KeyMission 360 camera
using raw PTP commands over USB. This bypasses the need to use the
camera's buttons/menu system.

Author: Research & Development
License: MIT
"""

import usb1
import struct
import sys
import argparse
from typing import Optional, Tuple, List

# Nikon KeyMission 360 USB IDs
VENDOR_ID = 0x04b0
PRODUCT_ID = 0x019f

# PTP Container Types
PTP_CONTAINER_COMMAND = 0x0001
PTP_CONTAINER_DATA = 0x0002
PTP_CONTAINER_RESPONSE = 0x0003

# PTP Opcodes
PTP_OC_OPEN_SESSION = 0x1002
PTP_OC_GET_STORAGE_IDS = 0x1004
PTP_OC_FORMAT_STORE = 0x100F

# PTP Response Codes
PTP_RC_OK = 0x2001
PTP_RC_INVALID_STORAGE_ID = 0x2008
PTP_RC_INVALID_PARAMETER = 0x201D
PTP_RC_DEVICE_BUSY = 0x2019

# USB Constants
ENDPOINT_TYPE_BULK = 0x02
ENDPOINT_DIR_IN = 0x80


class PTPError(Exception):
    """PTP protocol error"""
    pass


class KeyMission360Formatter:
    """Interface for formatting Nikon KeyMission 360 memory cards via PTP"""
    
    def __init__(self):
        self.handle: Optional[usb1.USBDeviceHandle] = None
        self.device: Optional[usb1.USBDevice] = None
        self.bulk_in: Optional[int] = None
        self.bulk_out: Optional[int] = None
        self.interface_num: int = 0
        self.transaction_id: int = 0
        
    def find_camera(self) -> bool:
        """Find and open the KeyMission 360 camera"""
        context = usb1.USBContext()
        
        for device in context.getDeviceIterator(skip_on_error=True):
            if device.getVendorID() == VENDOR_ID and device.getProductID() == PRODUCT_ID:
                print(f"[✓] Found Nikon KeyMission 360 at Bus {device.getBusNumber()} Device {device.getDeviceAddress()}")
                self.device = device
                self.handle = device.open()
                return True
                
        return False
    
    def setup_usb(self) -> None:
        """Configure USB interface and endpoints"""
        if not self.handle:
            raise PTPError("Camera not opened")
        
        # Set configuration
        self.handle.setConfiguration(1)
        
        # Detach kernel drivers from all interfaces
        for i in range(4):
            try:
                if self.handle.kernelDriverActive(i):
                    print(f"[*] Detaching kernel driver from interface {i}")
                    self.handle.detachKernelDriver(i)
            except:
                pass
        
        # Get interface
        config = self.device[0]
        interface = config[0]
        setting = next(interface.iterSettings())
        self.interface_num = setting.getNumber()
        
        # Claim interface
        self.handle.claimInterface(self.interface_num)
        print(f"[*] Interface {self.interface_num} claimed")
        
        # Find bulk endpoints
        for ep in setting.iterEndpoints():
            addr = ep.getAddress()
            attrs = ep.getAttributes()
            if (attrs & 0x03) == ENDPOINT_TYPE_BULK:
                if addr & ENDPOINT_DIR_IN:
                    self.bulk_in = addr
                else:
                    self.bulk_out = addr
        
        if not self.bulk_in or not self.bulk_out:
            raise PTPError("Could not find bulk endpoints")
        
        print(f"[*] Bulk endpoints: OUT=0x{self.bulk_out:02x}, IN=0x{self.bulk_in:02x}")
    
    def send_ptp_command(self, opcode: int, params: Tuple[int, ...] = (), 
                         data_phase: bool = False) -> bytes:
        """Send a PTP command and return response"""
        self.transaction_id += 1
        
        # Build command packet
        # Length = 4 (len) + 2 (type) + 2 (opcode) + 4 (trans_id) + 4*len(params)
        length = 12 + (4 * len(params))
        
        packet = struct.pack('<IHH', length, PTP_CONTAINER_COMMAND, opcode)
        packet += struct.pack('<I', self.transaction_id)
        for param in params:
            packet += struct.pack('<I', param)
        
        # Send command
        self.handle.bulkWrite(self.bulk_out, packet, timeout=5000)
        
        if data_phase:
            # Read data phase first
            data = self.handle.bulkRead(self.bulk_in, 512, timeout=5000)
            # Then read response
            resp = self.handle.bulkRead(self.bulk_in, 512, timeout=5000)
            return data, resp
        else:
            # Read response directly
            resp = self.handle.bulkRead(self.bulk_in, 512, timeout=5000)
            return resp
    
    def parse_response(self, response: bytes) -> Tuple[int, int]:
        """Parse PTP response, returns (code, transaction_id)"""
        if len(response) < 8:
            raise PTPError(f"Response too short: {len(response)} bytes")
        
        resp_type = struct.unpack('<H', bytes(response[4:6]))[0]
        resp_code = struct.unpack('<H', bytes(response[6:8]))[0]
        resp_trans = struct.unpack('<I', bytes(response[8:12]))[0]
        
        return resp_code, resp_trans
    
    def open_session(self) -> bool:
        """Open PTP session"""
        print("\n[+] Opening PTP session...")
        
        resp = self.send_ptp_command(PTP_OC_OPEN_SESSION, (1,))
        code, _ = self.parse_response(resp)
        
        if code == PTP_RC_OK or code == 0x201E:  # Session already open
            print(f"[✓] Session opened (code: 0x{code:04x})")
            return True
        else:
            print(f"[!] Failed to open session: 0x{code:04x}")
            return False
    
    def get_storage_ids(self) -> List[int]:
        """Get list of available storage devices"""
        print("\n[+] Querying storage devices...")
        
        data, resp = self.send_ptp_command(PTP_OC_GET_STORAGE_IDS, data_phase=True)
        
        code, _ = self.parse_response(resp)
        if code != PTP_RC_OK:
            print(f"[!] Failed to get storage IDs: 0x{code:04x}")
            return []
        
        # Parse data phase
        if len(data) < 12:
            print("[!] Invalid data response")
            return []
        
        count = struct.unpack('<I', bytes(data[8:12]))[0]
        print(f"[*] Found {count} storage device(s)")
        
        storage_ids = []
        for i in range(count):
            offset = 12 + (i * 4)
            if offset + 4 <= len(data):
                storage_id = struct.unpack('<I', bytes(data[offset:offset+4]))[0]
                storage_ids.append(storage_id)
                print(f"    Storage {i+1}: 0x{storage_id:08x}")
        
        return storage_ids
    
    def format_storage(self, storage_id: int, force: bool = False) -> bool:
        """Format a storage device"""
        print(f"\n[+] Formatting storage 0x{storage_id:08x}...")
        
        if not force:
            print("[!] WARNING: This will erase ALL data on the memory card!")
            response = input("    Type 'YES' to proceed: ")
            if response != "YES":
                print("[x] Aborted")
                return False
        
        print("[*] Sending FormatStore command...")
        print("[*] This may take several seconds...")
        
        # Send FormatStore with storage ID as single parameter
        resp = self.send_ptp_command(PTP_OC_FORMAT_STORE, (storage_id,))
        code, _ = self.parse_response(resp)
        
        if code == PTP_RC_OK:
            print(f"[✓] Format completed successfully!")
            return True
        elif code == PTP_RC_INVALID_STORAGE_ID:
            print(f"[!] Invalid storage ID: 0x{storage_id:08x}")
        elif code == PTP_RC_INVALID_PARAMETER:
            print(f"[!] Invalid parameter")
        elif code == PTP_RC_DEVICE_BUSY:
            print(f"[!] Device is busy")
        else:
            print(f"[!] Format failed: 0x{code:04x}")
        
        return False
    
    def close(self) -> None:
        """Release resources"""
        if self.handle:
            try:
                self.handle.releaseInterface(self.interface_num)
                print("[*] Interface released")
            except:
                pass
    
    def run(self, storage_id: Optional[int] = None, force: bool = False) -> bool:
        """Main execution flow"""
        try:
            # Find camera
            if not self.find_camera():
                print("[!] Camera not found! Make sure it's connected via USB.")
                return False
            
            # Setup USB
            self.setup_usb()
            
            # Open PTP session
            if not self.open_session():
                return False
            
            # Get storage IDs if not specified
            if storage_id is None:
                storage_ids = self.get_storage_ids()
                
                if not storage_ids:
                    print("[!] No storage devices found")
                    return False
                
                # Use the memory card (0x00010001) if available, otherwise first storage
                if 0x00010001 in storage_ids:
                    storage_id = 0x00010001
                    print(f"[*] Auto-selected memory card: 0x{storage_id:08x}")
                else:
                    storage_id = storage_ids[0]
                    print(f"[*] Auto-selected storage: 0x{storage_id:08x}")
            
            # Format
            return self.format_storage(storage_id, force)
            
        except usb1.USBError as e:
            print(f"[!] USB Error: {e}")
            return False
        except PTPError as e:
            print(f"[!] PTP Error: {e}")
            return False
        finally:
            self.close()


def main():
    parser = argparse.ArgumentParser(
        description="Format Nikon KeyMission 360 memory card via USB/PTP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Auto-detect and format memory card
  %(prog)s --storage 0x00010001  # Format specific storage
  %(prog)s --force            # Skip confirmation prompt
  %(prog)s --list             # List storage devices only

Warning:
  This tool will ERASE ALL DATA on the memory card!
  Use at your own risk.
"""
    )
    
    parser.add_argument("--storage", "-s", type=lambda x: int(x, 0),
                       help="Specific storage ID to format (hex, e.g., 0x00010001)")
    parser.add_argument("--force", "-f", action="store_true",
                       help="Skip confirmation prompt (DANGEROUS)")
    parser.add_argument("--list", "-l", action="store_true",
                       help="List storage devices without formatting")
    parser.add_argument("--version", "-v", action="version", version="%(prog)s 1.0")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Nikon KeyMission 360 Memory Card Formatter")
    print("=" * 60)
    print()
    
    formatter = KeyMission360Formatter()
    
    if args.list:
        # Just list storage devices
        try:
            if not formatter.find_camera():
                print("[!] Camera not found!")
                sys.exit(1)
            
            formatter.setup_usb()
            formatter.open_session()
            formatter.get_storage_ids()
            formatter.close()
            
        except Exception as e:
            print(f"[!] Error: {e}")
            sys.exit(1)
    else:
        # Format
        success = formatter.run(storage_id=args.storage, force=args.force)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
