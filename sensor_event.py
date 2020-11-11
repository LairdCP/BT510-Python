
""" Converts advertisement data into sensor events """

import time
import logging
from ctypes import c_uint16, c_int16
from enum import IntEnum, unique
from adv_parser import AdvParser


@unique
class MagnetState(IntEnum):
    NEAR = 0
    FAR = 1


@unique
class SensorEventType(IntEnum):
    RESERVED = 0
    TEMPERATURE = 1
    MAGNET = 2  # or proximity
    MOVEMENT = 3
    ALARM_HIGH_TEMP_1 = 4
    ALARM_HIGH_TEMP_2 = 5
    ALARM_HIGH_TEMP_CLEAR = 6
    ALARM_LOW_TEMP_1 = 7
    ALARM_LOW_TEMP_2 = 8
    ALARM_LOW_TEMP_CLEAR = 9
    ALARM_DELTA_TEMP = 10
    ALARM_TEMPERATURE_RATE_OF_CHANGE = 11
    BATTERY_GOOD = 12
    ADV_ON_BUTTON = 13
    RESERVED_14 = 14
    IMPACT = 15
    BATTERY_BAD = 16
    RESET = 17


@unique
class ResetReason(IntEnum):
    POWER_UP = 0,
    RESETPIN = 1,
    DOG = 2,
    SREQ = 3,
    LOCKUP = 4,
    OFF = 5,
    LPCOMP = 6,
    DIF = 7,
    NFC = 8,
    VBUS = 9,
    UNKNOWN = 10,


class SensorEvent:
    def __init__(self, buf=None):
        self.epoch = 0
        self.type = SensorEventType.RESERVED
        self.number = 0
        self.magnet_state = MagnetState.FAR
        self.temperature = 0.0
        self.batteryVoltage = 0.0
        self.reset_reason = ResetReason.UNKNOWN
        if buf is not None:
            self.update(AdvParser(buf))
        self.logger = logging.getLogger('AD parser')

    def update(self, ap: AdvParser) -> bool:
        """
        Update the event 'state' based on the parsed advertisement
        """
        if not ap.adv_valid:
            self.logger.debug("Ad not valid")
            return False
        if self.number == ap.adv.record_number:
            self.logger.debug("Duplicate AD")
            return False
        else:
            self.number = ap.adv.record_number
            self.epoch = ap.adv.epoch
            try:
                self.type = SensorEventType(ap.adv.record_type)
                if (self.type == SensorEventType.RESERVED or
                        self.type == SensorEventType.RESERVED_14 or
                        self.type == SensorEventType.IMPACT or
                        self.type == SensorEventType.MOVEMENT):
                    pass
                elif (self.type == SensorEventType.TEMPERATURE or
                        self.type == SensorEventType.ALARM_HIGH_TEMP_1 or
                        self.type == SensorEventType.ALARM_HIGH_TEMP_2 or
                        self.type == SensorEventType.ALARM_HIGH_TEMP_CLEAR or
                        self.type == SensorEventType.ALARM_LOW_TEMP_1 or
                        self.type == SensorEventType.ALARM_LOW_TEMP_2 or
                        self.type == SensorEventType.ALARM_LOW_TEMP_CLEAR or
                        self.type == SensorEventType.ALARM_DELTA_TEMP or
                        self.type == SensorEventType.ALARM_TEMPERATURE_RATE_OF_CHANGE):
                    self.temperature = c_int16(ap.adv.payload).value / 100.0
                elif (self.type == SensorEventType.BATTERY_GOOD or
                        self.type == SensorEventType.BATTERY_BAD or
                        self.type == SensorEventType.ADV_ON_BUTTON):
                    self.batteryVoltage = c_uint16(
                        ap.adv.payload).value / 100.0
                elif self.type == SensorEventType.MAGNET:
                    try:
                        self.magnet_state = MagnetState(ap.adv.payload & 0x1)
                    except:
                        self.logger.debug("Magnet State invalid")
                elif self.type == SensorEventType.RESET:
                    try:
                        self.reset_reason = ResetReason(ap.adv.payload)
                    except:
                        self.reset_reason = ResetReason.UNKNOWN
                        self.logger.debug("Reset Reason Invalid")
            except:
                self.logger.debug("Sensor event type not valid")

            return True


if __name__ == "__main__":
    import log_wrapper
    log_wrapper.setup(__file__, console_level=logging.DEBUG)

    s = SensorEvent(
        "0201061BFF7700010000000000A218417E3AC10C5B004E4B9D5DB60A00000011077C16A55EBA11CB920C497FB801119A560C0853656E74726975732D4254")
    logging.info(s.__dict__)

    s = SensorEvent(
        "0201061BFF7700010000000000A218417E3AC10C5F004E579D5DEF0A00000011077C16A55EBA11CB920C497FB801119A560709466F622D6168")
    logging.info(s.__dict__)

    s = SensorEvent(
        "0201061BFF7700010000000280D432E0C54DC90C250038D1EE5D940B00005210FFE400030000000105330000000000000809546573742D3130")
    logging.info(s.__dict__)

    # old format - should give error
    s = SensorEvent(
        "0201061BFF77000100000000008E1F1D4335E20358001200000001000000000DFFE400010000000110000000000F0953656E7472697573204254353130")
    logging.info(s.__dict__)

    # temperature 01C9A84705C54A
    s = SensorEvent(
        "0201061BFF77000100000002804AC50547A8C9011C016BD5EE5DC20900000110FFE400030000000104140000000312000809546573742D3461")
    logging.info(s.__dict__)
