
"""
A simple test of serial communication with a BT510.
"""

import time
import serial
import serial.threaded
import logging
import log_wrapper
from json_serial_reader import JsonSerialReader
from json_config import JsonConfig

if __name__ == "__main__":
    log_wrapper.setup(__file__)
    isBle = False
    jc = JsonConfig(isBle)
    ser = serial.serial_for_url(
        url=jc.get_port(), baudrate=jc.get_baudrate(), timeout=1.0)
    with serial.threaded.ReaderThread(ser, JsonSerialReader) as reader_thread:
        rt = reader_thread
        rt.set_protocol(reader_thread)
        rt.Unlock()
        rt.GetAttribute("sensorName")
        rt.GetAttribute("location")
        rt.GetAttribute("firmwareVersion")
        rt.GetAttribute("hwVersion")
        rt.GetAttribute("bluetoothAddress")
        rt.LedTest()
        rt.EpochTest(int(time.time()))
        rt.LogResults()
