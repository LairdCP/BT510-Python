
""" Send BT510 event data to AWS CloudWatch """


import logging
import log_wrapper
import serial
import serial.threaded
from dongle import BL65x
from json_commander import jtester
from json_config import JsonConfig
from sensor_event import SensorEvent
from adv_parser import AdvParser
import metrics
import boto3

NAMESPACE = "Client/Application"

if __name__ == "__main__":
    log_wrapper.setup(__file__, console_level=logging.INFO, file_mode='a')
    isBle = True
    jc = JsonConfig(isBle)
    ser = serial.Serial(jc.get_port(), baudrate=jc.get_baudrate(),
                        timeout=1,  rtscts=True)
    with serial.threaded.ReaderThread(ser, BL65x) as bt_module:
        cloudwatch = boto3.client('cloudwatch')
        jt = jtester()
        jt.set_protocol(bt_module)
        bt_module.secondary_initialization()
        name_to_look_for = jc.get("system_name_to_look_for")
        bt_module.scan(nameMatch=name_to_look_for)
        event_dict = dict()
        while True:
            ad = bt_module.get_scan(timeout=None)
            ap = None
            try:
                junk, address, rssi, ad_rsp = ad.split(' ')
                logging.debug(f"{address} {rssi} {ad_rsp}")
            except:
                logging.info("unable to split advertisement")

            try:
                ap = AdvParser(ad_rsp.strip('"'))
            except:
                logging.info("unable to parse")

            if ap is not None:
                if ap.adv_valid:
                    # Use a dictionary of address and last events because the
                    # event handler doesn't handle events from different devices.
                    if ap.bd_addr not in event_dict:
                        logging.info(
                            f'Found new sensor "{ap.name}" with BDA: {ap.bd_addr}')
                        event_dict[ap.bd_addr] = SensorEvent()
                        if ap.rsp_valid:
                            logging.info(ap.rsp)

                    if event_dict[ap.bd_addr].update(ap):
                        logging.info(ap.name)
                        logging.info(event_dict[ap.bd_addr].__dict__)
                        logging.info(f"reset count {ap.adv.reset_count}")
                        # logging.info(ap.flags_dict)
                        try:
                            cloudwatch.put_metric_data(
                                Namespace=NAMESPACE, MetricData=metrics.Generate(event_dict[ap.bd_addr], ap))
                        except:
                            logging.info("Unable to send metric to CloudWatch")
                else:
                    logging.info("ad not valid")
