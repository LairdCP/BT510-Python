
""" Use JSON file for configuration of scripts """

import sys
import logging
import json


class JsonConfig:
    def __init__(self, isBle=False, fname="config.json"):
        self.logger = logging.getLogger(__file__)
        self.isBle = isBle
        try:
            with open(fname) as ifile:
                self.config = json.load(ifile)
        except IOError:
            self.logger.error(f"Expecting JSON config file '{fname}'")
            sys.exit(1)

    def get(self, key):
        """ Find key in JSON configuration file and return value """
        try:
            value = self.config[key]
            return value
        except KeyError as err:
            self.logger.error(
                f"Unable to find key '{key}' in JSON config file")
            sys.exit(3)

    def get_port(self):
        """ Returns serial communication port from JSON configuration """
        if self.isBle:
            key = "ble_dongle_comport"
        else:
            key = "comport"
        return self.get(key)

    def get_baudrate(self):
        """ Returns communication rate from JSON configuration """
        if self.isBle:
            key = "ble_dongle_baudrate"
        else:
            key = "baudrate"
        return self.get(key)


if __name__ == "__main__":
    isBle = True

    # Test for error when file is missing
    #jc = JsonConfig(isBle, "missing.json")

    jc = JsonConfig(isBle, "config.json")
    print(jc.get_baudrate())
    print(jc.get_port())
    # value not present
    print(jc.get("turbo"))
