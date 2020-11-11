
import time
import logging
import struct
import bitstruct
from collections import namedtuple

FOB_ADV_FORMAT = '<BBBBBHHHH6sBHLLB'
FOB_RSP_FORMAT1 = '<BB16sBB'
FOB_RSP_FORMAT2 = '<BBHHHBBBBBBBBBBB'
FOB_ADV_FIELDS = "flags_length flags_adtype flags_data \
                  ms_length ms_adtype company_id protocol_id \
                  network_id flags bluetooth_address record_type record_number epoch payload reset_count"
FOB_RSP_FIELDS1 = "vsp_length vsp_uuid_type vsp_uuid name_length name_type"
FOB_RSP_FIELDS2 = "ms2_length ms2_type ms2_company_id protocol_id product_id \
                   firmware_major_version firmware_minor_version firmware_build_version \
                   firmware_type config_version bootloader_major_version bootloader_minor_version bootloader_build_version packed_hardware_version name_length name_type"

FOB_FLAGS_FORMAT = '<u1u1u1u1u2u2u1u4u1u1u1'
FOB_FLAGS_NAMES = ["magnet_state", "movement_alarm", "roc_alarm", "delta_temp_alarm", "low_temp_alarm",
                   "high_temp_alarm", "low_battery_alarm", "reserved", "any_alarm", "active_mode", "time_was_set"]

RSP_START_INDEX = 31
VSP_ADTYPE_LENGTH = 17
RSP_NAME_OFFSET = 3
VSP_UUID = b'\x7c\x16\xa5\x5e\xba\x11\xcb\x92\x0c\x49\x7f\xb8\x01\x11\x9a\x56'

verbose = False


class AdvParser:
    """ Parse BT510 advertisements """

    def __init__(self, buf):
        self.rx_epoch = int(time.time())
        self.logger = logging.getLogger(__file__)
        self.adv = tuple()
        self.rsp = tuple()
        self.flags_dict = dict()
        self.bd_addr = ""
        self.name = ""
        self.adv_valid = False
        self.rsp_valid = False
        self.rsp_has_versions = False
        if (len(buf) % 2) == 0:
            b = bytes.fromhex(buf)
        else:
            b = bytes()
        self.logger.debug(f"Advertisement Length {len(buf)} -> {len(b)}")
        try:
            self.adv = namedtuple("adv", FOB_ADV_FIELDS)._make(
                struct.unpack_from(FOB_ADV_FORMAT, b))
            self.adv_valid = self._validate_ad()
            h = self.adv.bluetooth_address.hex()
            self.bd_addr = h[10:12] + h[8:10] + \
                h[6:8] + h[4:6] + h[2:4] + h[0:2]
        except:
            self.logger.info("Error in parsing advertisement")

        if self.adv_valid:
            if verbose:
                self.logger.debug(self.adv.flags)
            try:
                x = struct.pack('>H', self.adv.flags)
                if verbose:
                    self.logger.debug(x)
                self.flags_dict = bitstruct.unpack_dict(
                    FOB_FLAGS_FORMAT, FOB_FLAGS_NAMES, (x))
                self.logger.debug(self.flags_dict)
            except:
                self.logger.debug("Unable to unpack flags in advertisement")

        #
        # Adv and Scan response are done individually for debug reasons
        #
        try:
            rsp_format = namedtuple("format_type", "type")._make(
                struct.unpack_from('<B', b, RSP_START_INDEX))
            if rsp_format.type == VSP_ADTYPE_LENGTH:
                self.rsp = namedtuple("rsp", FOB_RSP_FIELDS1)._make(
                    struct.unpack_from(FOB_RSP_FORMAT1, b, RSP_START_INDEX))
                self.rsp_valid = self._validate_rsp1()
            else:
                self.rsp = namedtuple("rsp", FOB_RSP_FIELDS2)._make(
                    struct.unpack_from(FOB_RSP_FORMAT2, b, RSP_START_INDEX))
                self.rsp_valid = self._validate_rsp2()
                self.rsp_has_versions = self.rsp_valid

            # The length of the name is variable
            length = self.rsp.name_length - 1
            self.name = namedtuple("name", "name")._make(struct.unpack_from(f'<{length}s', b,
                                                                            (RSP_START_INDEX + rsp_format.type + RSP_NAME_OFFSET))).name.decode('utf-8')
        except:
            self.logger.info("Error in parsing scan response")

    def get_at_bd_addr(self) -> str:
        return "01" + self.bd_addr

    def _validate_ad(self) -> bool:
        if (self.adv.flags_length == 2 and
                self.adv.flags_adtype == 0x01 and
            self.adv.flags_data == 0x06 and
            self.adv.ms_length == 0x1b and
            self.adv.ms_adtype == 0xff and
            self.adv.company_id == 0x0077 and
                self.adv.protocol_id == 0x0001):
            return True
        else:
            return False

    def _validate_rsp1(self) -> bool:
        if (self.rsp.vsp_length == 0x11 and
                self.rsp.vsp_uuid_type == 0x07 and
                self.rsp.vsp_uuid == VSP_UUID):
            return True
        else:
            return False

    def _validate_rsp2(self) -> bool:
        if (self.rsp.ms2_length == 0x10 and
                self.rsp.ms2_type == 0xff and
            self.rsp.ms2_company_id == 0x00E4 and
            self.rsp.protocol_id == 0x0003 and
                self.rsp.product_id == 0):
            return True
        else:
            return False

    def unpack_hardware_version(self) -> str:
        if self.rsp_has_versions:
            return str((self.rsp.packed_hardware_version >> 3) & 0x1F) + "." + str(self.rsp.packed_hardware_version & 0x7)
        else:
            return "0.0"


if __name__ == "__main__":
    import log_wrapper
    log_wrapper.setup(__file__, console_level=logging.DEBUG)
    buf = ""

    ap = AdvParser(buf)
    print(ap.adv)
    print(ap.rsp)
    print(ap.name)
    print(ap.bd_addr)
    print(ap.get_at_bd_addr())
    print(ap.adv_valid)
    print(ap.rsp_valid)
