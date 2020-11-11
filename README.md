# BT510 Python Examples

These examples communicate with the [BT510.](https://www.lairdconnect.com/iot-devices/iot-sensors/bt510-bluetooth-5-long-range-ip67-multi-sensor) Common operations are configuring a sensor, analyzing advertisements, and reading the event log.

JSON-RPC is used to communicate with the sensor. In normal operation, BLE is used as the transport. A UART/serial transfer mode is used by Laird Connectivity for development and test.

Scripts using a BLE transport utilize the [BL654 USB dongle running smartBASIC](https://www.lairdconnect.com/wireless-modules/bluetooth-modules/bluetooth-5-modules/bl654-series-bluetooth-module-nfc) and the [AT command interface](https://github.com/LairdCP/BL654-Applications).

## Usage

The scripts were tested using Python 3.9.0.  The packages required can be found in [requirements.txt.](./requirements.txt)

The sample scripts have the prefix "example" in the name. Script configuration is controlled by [config.json](./config.json).

For example, with Python and pip installed the read log example can be run by doing the following.
1. pip install -r requirements.txt
2. python example_read_logs.py

### Communication Port

The BLE comport must be set to match your system.

It is recommended to increase the baudrate to 1000000. However, this requires setting and saving the rate on the BL654 dongle. This can be done with UwTerminalX (or any terminal with local echo on) and the commands:

1. ATS 302=1000000
2. AT&W
3. ATZ

### Sensor Name

The address or name can be used to connect to sensors. Using the name is often easier.

The "name_to_look_for" key is used by scripts that often only talk to one device.
The "system_name_to_look_for" key is used by scripts that may communicate with multiple devices.

It is recommended to rename sensors in a system with a common prefix. Then they can easily be differentiated from un-configured sensors that have the name "BT510".

## Logs

Each script produces a transcript in the logs folder.  Samples can be found in [sample_logs](./sample_logs) folder. These can be used to view the commands and responses.

## Known Limitations

The scripts do not support Long Range (Coded PHY).
