#!/usr/bin/env python3
"""Linux-native tool for Marvell MiFi/PXA modem serial interfaces.

The original MIFITOOL.exe opens a 115200-baud COM port and exchanges
CRLF-terminated AT-style commands.  This clone supports the original read
operations and the original carrier-unlock action.
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass

import serial
from serial.tools import list_ports
import usb.core
import usb.util


READ_COMMANDS = {
    "version": "*READVER",
    "imei": "*MRD_IMEI?",
    "mac": "+MIFIMAC?",
    "serial": "*MRD_SN?",
    "pcba_serial": "*MRD_SECOND_SN?",
}


@dataclass
class Response:
    command: str
    raw: bytes

    @property
    def text(self) -> str:
        return self.raw.decode("ascii", errors="replace").replace("\x00", "")


def ports() -> list[str]:
    return [p.device for p in list_ports.comports()]


def read_response(port: serial.Serial, command: str, timeout: float) -> Response:
    port.reset_input_buffer()
    port.write(b"AT" + command.encode("ascii") + b"\r\n")
    port.flush()

    deadline = time.monotonic() + timeout
    data = bytearray()
    while time.monotonic() < deadline:
        chunk = port.read(port.in_waiting or 1)
        if chunk:
            data.extend(chunk)
            text = data.decode("ascii", errors="ignore")
            if "\nOK" in text or text.rstrip().endswith("OK"):
                break
            if "ERROR" in text or "+CME ERROR" in text:
                break
        else:
            time.sleep(0.01)
    return Response(command, bytes(data))


class UsbAt:
    """Direct libusb backend for the Marvell Mobile AT Interface."""

    def __init__(self, timeout_ms: int = 250):
        self.device = usb.core.find(idVendor=0x1286, idProduct=0x4E31)
        if self.device is None:
            raise RuntimeError("Marvell MiFi USB device 1286:4e31 not found")
        self.interface = 4
        configuration = self.device.get_active_configuration()
        self.intf = usb.util.find_descriptor(configuration, bInterfaceNumber=self.interface)
        if self.intf is None:
            raise RuntimeError("Marvell Mobile AT Interface (USB interface 4) not found")
        if self.device.is_kernel_driver_active(self.interface):
            self.device.detach_kernel_driver(self.interface)
        usb.util.claim_interface(self.device, self.interface)
        self.out_ep = usb.util.find_descriptor(self.intf, bEndpointAddress=0x02)
        self.in_ep = usb.util.find_descriptor(self.intf, bEndpointAddress=0x83)
        if self.out_ep is None or self.in_ep is None:
            self.close()
            raise RuntimeError("AT interface endpoints were not found")
        self.timeout_ms = timeout_ms

    def query(self, command: str, timeout: float) -> Response:
        self.out_ep.write(b"AT" + command.encode("ascii") + b"\r\n", timeout=2000)
        data = bytearray()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                data.extend(bytes(self.in_ep.read(512, timeout=self.timeout_ms)))
                if b"\nOK" in data or b"ERROR" in data:
                    break
            except usb.core.USBTimeoutError:
                pass
        return Response(command, bytes(data))

    def close(self) -> None:
        try:
            usb.util.release_interface(self.device, self.interface)
            usb.util.dispose_resources(self.device)
        except usb.core.USBError:
            pass


def clean_response(response: Response) -> str:
    lines = []
    for line in response.text.replace("\r", "").split("\n"):
        line = line.strip()
        if not line or line in {response.command, "AT" + response.command, "OK"}:
            continue
        lines.append(line)
    return "\n".join(lines) if lines else "(no response)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Linux Marvell MiFi tool (read-only protocol probe)")
    parser.add_argument("--port", help="serial device, e.g. /dev/ttyUSB0")
    parser.add_argument("--usb", action="store_true", help="use the Marvell USB AT interface directly")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--raw", metavar="COMMAND", help="send one raw read/probe command")
    parser.add_argument("--status", action="store_true", help="query the PN/network-lock status")
    parser.add_argument("--unlock", nargs="?", const="123456", metavar="CODE", help="disable the PN/network lock; defaults to the bundled button code")
    args = parser.parse_args()

    if args.usb or (not args.port and usb.core.find(idVendor=0x1286, idProduct=0x4E31) is not None):
        try:
            device = UsbAt()
            if args.raw:
                commands = {"raw": args.raw}
            elif args.unlock:
                commands = {"unlock": f"+CLCK=PN,0,{args.unlock}"}
            elif args.status:
                commands = {"status": "+CLCK=PN,2"}
            else:
                commands = READ_COMMANDS
            for label, command in commands.items():
                response = device.query(command, args.timeout)
                print(f"[{label}] {command}")
                print(clean_response(response))
                print()
            device.close()
            return 0
        except (RuntimeError, usb.core.USBError) as exc:
            print(f"Could not use the MiFi USB AT interface: {exc}", file=sys.stderr)
            return 1

    if not args.port:
        found = ports()
        if not found:
            print("No serial ports detected. Connect the MiFi and retry with --port /dev/ttyUSB0.", file=sys.stderr)
            return 2
        print("Detected serial ports:")
        for device in found:
            print(f"  {device}")
        print("Select one with --port.", file=sys.stderr)
        return 2

    try:
        with serial.Serial(
            args.port,
            baudrate=args.baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.1,
            write_timeout=2,
        ) as port:
            if args.raw:
                commands = {"raw": args.raw}
            elif args.unlock:
                commands = {"unlock": f"+CLCK=PN,0,{args.unlock}"}
            elif args.status:
                commands = {"status": "+CLCK=PN,2"}
            else:
                commands = READ_COMMANDS
            for label, command in commands.items():
                response = read_response(port, command, args.timeout)
                print(f"[{label}] {command}")
                print(clean_response(response))
                print()
    except serial.SerialException as exc:
        print(f"Could not open or use {args.port}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
