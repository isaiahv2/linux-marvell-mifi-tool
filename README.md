Linux MiFi Tool
Author: Isaiah

Status: Community project / work in progress
A Linux-native replacement for the supplied Marvell MifiTool V1.4.0.0.exe.

It is intended for anyone working with a compatible Marvell MiFi device.
What it does
The original Windows utility communicates with the MiFi through an AT command

interface at 115200 8N1. It does not require a proprietary Windows driver.

This Linux version supports both:
·	Direct USB communication through the MiFi's vendor interface 4
·	Serial devices such as /dev/ttyUSB0
·	A graphical interface for reading device information, checking lock status,

and sending an unlock code
·	A command-line interface for scripting and troubleshooting
The recovered information commands are:
*READVER
*MRD_IMEI?
+MIFIMAC?
*MRD_SN?
*MRD_SECOND_SN?

Quick start
1.	Connect the MiFi to the computer.
2.	Open a terminal in this folder.
3.	Start the graphical interface:
4.	python3 mifi_gui.py

5.	Click Read Info, Check Lock, or enter a code and click Unlock.
You can also start the GUI from a terminal:
python3 mifi_gui.py

Command-line usage
The tool automatically tries the supported Marvell USB interface when the MiFi

is connected:
python3 mifi_tool.py --usb
python3 mifi_tool.py --usb --status
python3 mifi_tool.py --usb --unlock YOUR_CODE
python3 mifi_tool.py --usb --raw '*READVER'

For a serial connection, specify the port explicitly:
python3 mifi_tool.py --port /dev/ttyUSB0
python3 mifi_tool.py --port /dev/ttyUSB0 --raw '*READVER'

Requirements
Python 3 with Tkinter, PySerial, and PyUSB is required. On Debian or Ubuntu,

the dependencies can usually be installed with:
sudo apt install python3 python3-tk python3-serial python3-usb

If Linux reports a USB-permission error, add the appropriate udev rule or

device-permission group for your distribution, then reconnect the MiFi or log

in again.
Important notes
·	Test the tool on your own device and keep a backup of important information.
·	Unlocking may be restricted by the carrier or device firmware.
·	The default unlock value used by the original Windows button is 123456.

Supply your own code with --unlock YOUR_CODE when required.
·	The USB identifiers currently supported are Marvell vendor 1286 and

product 4E31.
Files
·	start_mifi.sh — optional launcher script
·	mifi_gui.py — graphical interface
·	mifi_tool.py — command-line tool and USB/serial communication code
Feedback, testing results, and compatibility reports are welcome—especially

for additional MiFi models that use the same AT interface.
