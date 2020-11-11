
""" Scan for advertisements and generate report of BT510s """

import time
import serial
import serial.threaded
import logging
import log_wrapper
from dongle import BL65x
from json_commander import jtester
from json_config import JsonConfig
from adv_parser import AdvParser


def append_report(ofile: str, s: str) -> None:
    with open(ofile, 'a') as f:
        f.write(s)


def build_version_string(major: int, minor: int, build: int) -> str:
    return str(major) + "." + str(minor) + "." + str(build)


COLUMN_LIST = "                   Name,        BD Addr,          Timestamp,  FW Version, BootVersion,   HW,  Reset Count, Config Version, Network ID\n"


def report_generator(ap: AdvParser) -> str:
    s = ""
    local_time = time.strftime(
        '%d %b %y %H:%M:%S', time.localtime(time.time()))
    s += f"{ap.name:>23}, 0x{ap.bd_addr}, {local_time:>18}, "
    s += f"{build_version_string(ap.rsp.firmware_major_version, ap.rsp.firmware_minor_version, ap.rsp.firmware_build_version):>11}, "
    s += f"{build_version_string(ap.rsp.bootloader_major_version, ap.rsp.bootloader_minor_version, ap.rsp.bootloader_build_version):>11}, "
    s += f"{ap.unpack_hardware_version():>4}, "  # 12.4
    s += f"{ap.adv.reset_count:>12}, "
    s += f"{ap.rsp.config_version:>14}, "
    s += f"{ap.adv.network_id:>10}"
    s += '\n'
    return s


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
        ofile = "logs/" + name_to_look_for + ".system_report.log"
        append_report(ofile, COLUMN_LIST)
        bt_module.scan(nameMatch=name_to_look_for)
        device_list = list()
        stop_time = time.time() + jc.get("system_report_scan_duration_seconds")
        while time.time() < stop_time:
            ad = bt_module.get_scan(timeout=None)
            ap = None
            try:
                junk, address, rssi, ad_rsp = ad.split(' ')
                logging.debug(f"{address} {rssi} {ad_rsp}")
                ap = AdvParser(ad_rsp.strip('"'))
            except:
                logging.debug("unable to process advertisement")

            if ap is not None:
                if ap.adv_valid and ap.rsp_valid and ap.rsp_has_versions:
                    if ap.bd_addr not in device_list:
                        logging.info(
                            f'Found new sensor "{ap.name}" with BDA: {ap.bd_addr}')
                        device_list.append(ap.bd_addr)
                        s = report_generator(ap)
                        logging.info(s)
                        append_report(ofile, s)

        bt_module.cancel_scan()
        logging.info("System Report Script Complete")
