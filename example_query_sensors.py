
"""
Print filtered events from a sensor to terminal.
The first time a sensor is seen its attributes are dumped.
Runs indefinitely.
"""

import logging
import log_wrapper
import serial
import serial.threaded
from dongle import BL65x
from json_commander import jtester
from json_config import JsonConfig
from sensor_event import SensorEvent
from adv_parser import AdvParser

if __name__ == "__main__":
    log_wrapper.setup(__file__, console_level=logging.INFO)
    isBle = True
    jc = JsonConfig(isBle, "config.json")
    ser = serial.Serial(jc.get_port(), baudrate=jc.get_baudrate(),
                        timeout=1,  rtscts=True)
    with serial.threaded.ReaderThread(ser, BL65x) as bt_module:
        jt = jtester()
        jt.set_protocol(bt_module)
        bt_module.secondary_initialization()

        name_to_look_for = jc.get("system_name_to_look_for")
        bt_module.scan(nameMatch=name_to_look_for)
        event_dict = dict()
        while True:
            ad = bt_module.get_scan(timeout=None)
            do_query = False
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
                    if ap.bd_addr not in event_dict:
                        logging.info(
                            f'Found new sensor "{ap.name}" with BDA: {ap.bd_addr}')
                        event_dict[ap.bd_addr] = SensorEvent()
                        do_query = True
                        if ap.rsp_valid:
                            logging.info(ap.rsp)

                    # Print new events
                    if event_dict[ap.bd_addr].update(ap):
                        logging.info(ap.name)
                        logging.info(event_dict[ap.bd_addr].__dict__)

            if do_query:
                bt_module.cancel_scan()
                bt_module.connect(ap.get_at_bd_addr(),
                                  bt_module.connection_timeout)
                if bt_module.vspConnection:
                    jt.Dump()
                    bt_module.disconnect()
                else:
                    logging.debug('Unable to connect')

                bt_module.scan(nameMatch=name_to_look_for)

        bt_module.cancel_scan()
