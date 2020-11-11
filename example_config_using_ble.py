
"""
Connect to and Configure sensors using default_sensor_configuration.json.
Runs indefintely.
"""

import time
import serial
import serial.threaded
import logging
import log_wrapper
from json_config import JsonConfig
from sensor_config import sensor_config
from dongle import BL65x
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
        name_to_look_for = "BT510"
        bt_module.scan(nameMatch=name_to_look_for)
        configured_devices = dict()
        while True:
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
                        logging.debug("Preparing to configure new device")
                        bt_module.allow_pairing()
                        bt_module.connect(ap.get_at_bd_addr(),
                                          bt_module.connection_timeout)
                        if bt_module.vspConnection:
                            config = sensor_config()
                            config.ask_user_for_changes()
                            jt.Unlock()
                            jt.SetEpoch(int(time.time()))
                            jt.SetAttributes(**config.get_kwargs())
                            # Prior to version 4.1.0 certain attributes required a reset.
                            # For example, a reset was required after setting the name.
                            jt.SendReboot()
                            bt_module.disconnect()
                            jt.LogResults()
                            configured_devices[ap.bd_addr] = True
                        bt_module.scan(nameMatch=name_to_look_for)
                    else:
                        logging.debug("device already in database")

        bt_module.cancel_scan()
