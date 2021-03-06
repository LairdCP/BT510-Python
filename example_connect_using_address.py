
""" Connect to a sensor using its Bluetooth address """

import time
import serial
import serial.threaded
import logging
import log_wrapper
from json_config import JsonConfig
from dongle import BL65x
from json_commander import jtester

if __name__ == "__main__":
    log_wrapper.setup(__file__, console_level=logging.DEBUG)
    isBle = True
    jc = JsonConfig(isBle)
    ser = serial.serial_for_url(
        url=jc.get_port(), baudrate=jc.get_baudrate(), timeout=1,  rtscts=True)
    with serial.threaded.ReaderThread(ser, BL65x) as bt_module:
        jt = jtester()
        jt.set_protocol(bt_module)
        bt_module.secondary_initialization()
        input("Press sensor button (advertise) and then press enter...")
        bt_module.connect(bt_module.current_addr, bt_module.connection_timeout)
        if bt_module.vspConnection:
            jt.Unlock()
            jt.GetAttribute("sensorName")
            jt.GetAttribute("location")
        bt_module.disconnect()
        jt.LogResults()
