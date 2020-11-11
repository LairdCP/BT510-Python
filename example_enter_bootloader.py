
"""
Command a BT510 to enter bootloader.
Change name_to_look_for to match desired (prevent putting unintended device into bootloader)
LED will blink rapidly red while in bootloader (timeout is 2 minutes).
"""

import time
import serial
import serial.threaded
import logging
import log_wrapper
from dongle import BL65x
from json_config import JsonConfig
from sensor_config import sensor_config
from json_commander import jtester
from adv_parser import AdvParser

if __name__ == "__main__":
    log_wrapper.setup(__file__, console_level=logging.DEBUG)
    isBle = True
    jc = JsonConfig(isBle, "config.json")
    ser = serial.Serial(jc.get_port(), baudrate=jc.get_baudrate(),
                        timeout=1,  rtscts=True)
    with serial.threaded.ReaderThread(ser, BL65x) as bt_module:
        jt = jtester()
        jt.set_protocol(bt_module)
        bt_module.secondary_initialization()
        name_to_look_for = jc.get("name_to_look_for")
        number_of_devices_to_look_for = jc.get("number_of_devices_to_look_for")
        bt_module.scan(nameMatch=name_to_look_for)
        configured_devices = dict()
        while number_of_devices_to_look_for > 0:
            ad = bt_module.get_scan(timeout=None)
            ap = None
            try:
                junk, address, rssi, ad_rsp = ad.split(' ')
                logging.debug(f"{address} {rssi} {ad_rsp}")
                ap = AdvParser(ad_rsp.strip('"'))
            except:
                logging.debug("unable to process advertisement")

            if ap is not None:
                if ap.adv_valid:
                    # Use a dictionary of address and last events because the
                    # event handler doesn't handle events from different devices.
                    if ap.bd_addr not in configured_devices:
                        bt_module.cancel_scan()
                        logging.debug(
                            "Preparing to send enter bootloader command")
                        bt_module.allow_pairing()
                        bt_module.connect(ap.get_at_bd_addr(),
                                          bt_module.connection_timeout)
                        if bt_module.vspConnection:
                            jt.SendEnterBootloader()
                            bt_module.disconnect()
                            jt.LogResults()
                            configured_devices[ap.bd_addr] = True
                            number_of_devices_to_look_for -= 1
                        bt_module.scan(nameMatch=name_to_look_for)
                    else:
                        logging.debug("device already in database")

        bt_module.cancel_scan()
