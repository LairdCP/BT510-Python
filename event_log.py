
"""
Reads base64 encoded BT510 logs, decode them, and write them to a file.
"""

import time
import logging
import struct
from collections import namedtuple
import base64
from ctypes import c_int16
from sensor_event import SensorEventType
from sensor_event import MagnetState
from sensor_event import ResetReason

# Salt is used to keep order in the log for items that occur at the same time
FOB_EVENT_FORMAT = '<LHBB'
FOB_EVENT_FIELDS = "timestamp data type salt"
SIZE_OF_EVENT = 8
RECORD_DELIMITER = ';'


def get_number_of_events_in_list(event_list: list) -> int:
    # {"jsonrpc": "2.0", "id": 2, "result": [16, "kd7OXWsJAQCR3s5dwgsMAQ=="]}
    size = event_list[0]
    if (size % SIZE_OF_EVENT) != 0:
        return 0
    else:
        return int(size/SIZE_OF_EVENT)


class EventLog:
    def __init__(self, event_list=None):
        self.logger = logging.getLogger(__file__)
        self.events = list()
        if event_list is not None:
            self.parse(event_list)

    def parse(self, event_list):
        """
        Generate a list of dictionaries from a list of lists in
        the form of [size, base64 encoded data]
        """
        for (size, b64) in event_list:
            try:
                buf = base64.standard_b64decode(b64)
            except:
                self.logger.debug("Base64 decode error")
                return

            if (size % SIZE_OF_EVENT) != 0:
                self.logger.debug("Size isn't a multiple of event")
            elif (len(buf) != size):
                self.logger.debug("Base64 decode size invalid")
            else:
                self._unpack_event(size, buf)

    def _unpack_event(self, size, buf):
        try:
            for n in range(0, size, SIZE_OF_EVENT):
                t = namedtuple("event", FOB_EVENT_FIELDS)._make(
                    struct.unpack_from(FOB_EVENT_FORMAT, buf, n))
                self.events.append(dict(t._asdict()))
        except:
            self.logger.debug("Event log unpack error")

    def write(self, sensor_name: str, event_count: int) -> None:
        ofile = "logs/" + sensor_name + '_' + time.strftime('%d%b%y_%H%M%S', time.localtime(
            time.time())) + "_" + str(event_count) + ".sensor_events.log"
        last_timestamp = 0
        with open(ofile, 'w') as f:
            f.write(self._output_formatter("Index", "Epoch", "Salt",
                                           "Local time", "Data", "EventType", "Marker"))
            index = 1
            for n in self.events:
                try:
                    event_type = SensorEventType(n['type'])
                    event_string = str(event_type).replace(
                        'SensorEventType.', '')
                    data_string = self._get_data_string(event_type, n['data'])
                except:
                    data_string = "-"
                    event_string = "?"

                timestamp = n['timestamp']
                if timestamp < last_timestamp:
                    marker = "**"
                    self.logger.warning("Invalid timestamp sequence detected")
                else:
                    marker = ""
                last_timestamp = timestamp
                f.write(self._output_formatter(str(index), str(timestamp), str(n['salt']), time.strftime(
                    '%d %b %y %H:%M:%S', time.localtime(timestamp)), data_string, event_string, marker))
                index += 1

    def _output_formatter(self, index: str, epoch: str, salt: str, local_time: str, data: str, event_type: str, marker: str) -> str:
        return f"{index:>5}, {epoch:>10}, {salt:>4}, {local_time:>18}, {data:>8}, {event_type:>32}, {marker:>8} {RECORD_DELIMITER}\n"

    def _get_data_string(self, event_type: SensorEventType, data: int) -> str:
        if (event_type == SensorEventType.RESERVED or
                event_type == SensorEventType.RESERVED_14 or
                event_type == SensorEventType.IMPACT or
                event_type == SensorEventType.MOVEMENT):
            return "-"
        elif (event_type == SensorEventType.TEMPERATURE or
                event_type == SensorEventType.ALARM_HIGH_TEMP_1 or
                event_type == SensorEventType.ALARM_HIGH_TEMP_2 or
                event_type == SensorEventType.ALARM_HIGH_TEMP_CLEAR or
                event_type == SensorEventType.ALARM_LOW_TEMP_1 or
                event_type == SensorEventType.ALARM_LOW_TEMP_2 or
                event_type == SensorEventType.ALARM_LOW_TEMP_CLEAR or
                event_type == SensorEventType.ALARM_DELTA_TEMP or
                event_type == SensorEventType.ALARM_TEMPERATURE_RATE_OF_CHANGE):
            return str(c_int16(data).value/100.0)
        elif (event_type == SensorEventType.BATTERY_GOOD or
                event_type == SensorEventType.BATTERY_BAD or
                event_type == SensorEventType.ADV_ON_BUTTON):
            return str(data/1000.0)
        elif event_type == SensorEventType.MAGNET:
            try:
                ms = MagnetState(data & 0x1)
                return str(ms).replace('MagnetState.', '')
            except:
                return "?"
        elif event_type == SensorEventType.RESET:
            try:
                return str(ResetReason(data)).replace('ResetReason.', '')
            except:
                return "?"
        else:  # The type should already be qualified before getting here, but to be safe...
            return "?"


if __name__ == "__main__":
    import log_wrapper
    log_wrapper.setup(__file__, console_level=logging.DEBUG)
    event_list = [[16, 'ZwLJXRIIAQDLAsldEAgBAA=='],
                  [16, 'LwPJXQkIAQCTA8ldCAgBAA==']]
    test = EventLog(event_list)

    bad_size = [[8, 'ZwLJXRIIAQDLAsldEAgBAA==']]
    test.parse(bad_size)

    wrong_size = [[16, 'ZwLJXRIIAQDLA']]
    test.parse(wrong_size)

    # This 'error' isn't detected because
    # the base64 decoder drops all bytes after the pad bytes.
    wrong_size2 = [[16, 'ZwLJXRIIAQDLAsldEAgBAA==LwPJXQkIAQCTA8ldCAgBAA==']]
    test.parse(wrong_size2)

    test.write("foo-00", 1)

    lst = list()
    lst.append([1024, "JgAAAAMAEQAmAAAAAQACATQAAAAAAAIAOQAAAAEAAgA8AAAAAAARADwAAAABAAIBRQAAAOYMDQBFAAAAwQkBAUUAAACZDAwCRwAAAAAAEQBHAAAAAQACAUcAAAAYCQECRwAAAP4LDANJAAAAAAARAEkAAAABAAIBSQAAAHMJAQJJAAAAQQwMA+olAABoDAwA6yUAAGQMDAAqJgAAZAwMACsmAABoDAwAbiYAAGgMDABxJgAAaAwMAHImAABkDAwA20oAAGgMDQB/TAAAZAwNAGRNAABhDA0Agk0AAF0MDQA8TwAAYQwNAFxPAABZDA0Ae08AAF0MDAB8TwAAXQwMAORNAQBZDA0ALk4BAFYMDQBdTgEATwwNAIBVAQBWDA0AAFYBAFkMDQAeVgEATwwNAJlWAQBSDA0AsVYBAEsMDQDNVgEASwwNAPBWAQBLDA0ADlcBAEgMDQAzVwEASAwNAFdXAQBEDA0A11gBAEsMDQBhWQEASAwNAIVZAQBIDA0AslkBAEQMDQDSWQEAQQwNAO9ZAQBEDA0ADloBAEEMDQB+WgEAQQwNAGdyAQBEDA0Ae3sBAEgMDAC0ewEASAwMALd7AQBIDAwAuXsBAEEMDAC7ewEARAwMALx7AQBEDAwAwHsBAEQMDADEewEARAwMAMx7AQAvDAwA0nsBAEEMDADUewEARAwMANd7AQBIDAwA2HsBAEQMDADaewEARAwMAN17AQBBDAwA3nsBAEEMDADgewEAPQwMAOh7AQBBDAwA6XsBAEEMDADrewEAQQwMAPB7AQBBDAwA8nsBAEEMDAD8ewEAQQwMAP17AQBBDAwAAXwBAEEMDAACfAEAPQwMAAR8AQBBDAwABnwBAEEMDAAJfAEAQQwMAAp8AQBBDAwAC3wBAD0MDAANfAEAPQwMAA58AQBBDAwAFXwBAEEMDAAXfAEAQQwMABl8AQBBDAwAG3wBAD0MDAAcfAEAQQwMAB58AQA9DAwAH3wBAD0MDAAhfAEAPQwMACJ8AQBBDAwAK3wBAEEMDABNfAEARAwMAFR8AQBEDAwAVXwBAD0MDABffAEAQQwMAGJ8AQBEDAwAZ3wBAEEMDABofAEARAwMAGl8AQBBDAwAa3wBAD0MDABsfAEAPQwMAG18AQA9DAwAb3wBAD0MDAByfAEAQQwMAHR8AQA9DAwAdnwBAD0MDAB4fAEAQQwMAIF8AQBBDAwAg3wBAD0MDACLfAEAQQwMAI98AQBBDAwAkXwBAD0MDACbfAEAPQwMAJx8AQBBDAwAnnwBAD0MDACifAEAPQwMAKl8AQBBDAwAs3wBAEEMDAC0fAEAPQwMALV8AQA9DAwAtnwBAD0MDAC3fAEAOgwMAA=="])
    lst.append([1024, "SJUCAEEMDQDelQIAQQwNACeWAgA6DA0AVpYCADoMDQCwlgIANgwNACWXAgA9DA0AbZcCACgMDQC6mwIAMwwNAACcAgAvDA0AVZwCAC8MDQDSnAIALwwNAK+dAgAsDA0A250CAC8MDQA5ngIALwwNAGueAgAvDA0AtJ4CACwMDQDx1QIAAAACAPXVAgABAAIAUdcCAAAAAgBZ1wIAAQACAGnXAgAAAAIAcdcCAAEAAgCB1wIAAAACAJDXAgABAAIAaNwCAAAAAgAn5QIAAQACADHlAgAAAAIAQfoCAAEAAgBH+gIAAAACANHxAwABAAIA0vEDAAAAAgDT8QMAAQACANPxAwAAAAIB1fEDAAEAAgDV8QMAAAACAWUeBAABAAIAZR4EAAAAAgERuQUAAQACABO5BQAAAAIAoaMOAAEAAgChow4AAAACAQFcDwABAAIAAlwPAAAAAgACXA8AAQACAQJcDwAAAAICAlwPAAEAAgMEXA8AAAACADlcDwABAAIAPlwPAAAAAgBBXA8AAQACAEFcDwAAAAIBSVwPAAEAAgBRXA8AAAACAFJcDwABAAIAUlwPAAAAAgGJXA8AAQACAJlcDwAAAAIAMV0PAAEAAgA1XQ8AAAACACFeDwABAAIAJF4PAAAAAgAkXg8AAQACAQFnDwAAAAIAEWcPAAEAAgASZw8AAAACAHFnDwABAAIAqWcPAAAAAgCxZw8AAQACALRnDwAAABEAtGcPAAEAAgG0Zw8A9ggBArRnDwC7CwwDtGkPAAAAAgC1aQ8AAQACALhpDwAAAAIAuGkPAAEAAgG4aQ8AAAACAoxqDwABAAIAkGoPAAAAAgCQag8AAQACAexsDwAAAAIA7WwPAAEAAgDubA8AAAACAPBsDwABAAIA8GwPAAAAAgHxbA8AAQACAPFsDwAAAAIBDG4PAAEAAgAPbg8AAAARAA9uDwABAAIBD24PAKAIAQIPbg8AuAsMA+ByDwC7CwwA8HIPALsLDQB9cw8AuAsNAGB0DwC4CwwAYnQPAAAAEQBidA8AAQACAWJ0DwDvCAECYnQPABMMDANFdQ8AFwwNAKV3DwATDA0A/nkPABcMDQBpeg8AFwwNAJR6DwAMDA0A2HoPABMMDQCpru5dNwkBAKmu7l0MDAwBra7uXQMAEQCtru5dAQACAa2u7l06CQECra7uXQwMDAPLru5dNgkBAOmu7l03CQEAB6/uXTIJAQAlr+5dNQkBAEOv7l0wCQEAYa/uXS4JAQB/r+5dLAkBAJ2v7l0sCQEAu6/uXScJAQDZr+5dIQkBAPev7l0SCQEAFbDuXQEJAQAzsO5d8AgBAFGw7l3dCAEAb7DuXcQIAQCNsO5dowgBAA=="])
    lst.append([744, "q7DuXX0IAQDJsO5dTwgBAOew7l0bCAEABbHuXdoHAQAjse5dlgcBAEGx7l1FBwEAX7HuXfQGAQB9se5dngYBAJux7l1DBgEAubHuXeAFAQDXse5dfQUBAPWx7l0cBQEAE7LuXbYEAQAxsu5dUwQBAE+y7l3qAwEAbbLuXYEDAQCLsu5dGAMBAKmy7l2uAgEAx7LuXUICAQDlsu5d2gEBAAOz7l1xAQEAIbPuXQgBAQA/s+5doAABAF2z7l05AAEAe7PuXc//AQCZs+5dZf8BALez7l3+/gEA1bPuXZf+AQDzs+5dMf4BABG07l3J/QEAL7TuXWH9AQBNtO5d+vwBAGu07l2U/AEAibTuXS78AQCntO5dyvsBAMW07l1q+wEA47TuXQ77AQABte5dtPoBAB+17l1c+gEAPbXuXQr6AQBbte5duvkBAHm17l1x+QEAl7XuXSn5AQC1te5d6fgBANO17l2r+AEA8bXuXXT4AQAPtu5dQPgBAC227l0P+AEAS7buXd33AQBptu5dsvcBAIe27l2I9wEApbbuXWH3AQDDtu5dPvcBAOG27l0a9wEA/7buXfz2AQAdt+5d3PYBADu37l2/9gEAWbfuXaL2AQB3t+5djfYBAJW37l109gEAs7fuXV72AQDRt+5dR/YBAO+37l0w9gEADbjuXSD2AQAruO5dDfYBAEm47l3+9QEAZ7juXe31AQCFuO5d3/UBAKO47l3T9QEAwbjuXcP1AQDfuO5dufUBAP247l2u9QEAG7nuXaH1AQA5ue5dmfUBAFe57l2M9QEAdbnuXYP1AQCTue5devUBALG57l1y9QEAz7nuXWz1AQDtue5dZPUBAAu67l1c9QEAKbruXVX1AQBIuu5dTvUBAGa67l1K9QEAhLruXUP1AQCiuu5dPfUBAMC67l059QEA3rruXTP1AQD8uu5dMfUBABq77l0r9QEAOLvuXSb1AQBWu+5dIvUBAHS77l0h9QEA"])
    negative_numbers = EventLog(lst)
    negative_numbers.write("negative_numbers", 128 + 128 + 93)
    pass
