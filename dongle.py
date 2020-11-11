
"""
BLE transport for communicating with BT510 using Laird Connectivity's BL65x USB Dongle
"""

import json
import argparse
import threading
import serial.threaded
import serial
import logging
import sys
import time
sys.path.insert(0, '..')


try:
    import queue
except ImportError:
    import Queue as queue


class ATException(Exception):
    pass


verbose = True
verbose_bracket = False


def laird_dongle_verbose():
    global verbose
    verbose = True


def laird_dongle_quiet():
    global verbose
    verbose = False


class ATProtocol(serial.threaded.Protocol):

    def __init__(self):
        super().__init__()
        print("protocol init")
        self.text = ""
        self.transport = None
        self.alive = True
        self.responses = queue.Queue()
        self.events = queue.Queue()
        self.ads = queue.Queue()
        self._event_thread = threading.Thread(target=self._run_event)
        self._event_thread.daemon = True
        self._event_thread.name = 'at-event'
        self._event_thread.start()
        self.lock = threading.Lock()
        self.pairing_done = threading.Event()
        self.no_carrier = threading.Event()

    def connection_made(self, transport):
        """Store transport"""
        self.transport = transport
        self.text = ""
        self.transport.serial.reset_input_buffer()
        self.transport.serial.reset_output_buffer()

    def connection_lost(self, exc):
        """Forget transport"""
        super().connection_lost(exc)
        self.transport = None
        self.text = ""

    def stop(self):
        """
        Stop the event processing thread, abort pending commands, if any.
        """
        self.alive = False
        self.events.put(None)
        self.responses.put('<exit>')

    def _run_event(self):
        """
        Process events in a separate thread so that input thread is not
        blocked.
        """
        while self.alive:
            try:
                self.handle_event(self.events.get())
            except:
                logging.exception('_run_event')

    def data_received(self, data):
        """
        Parse the different types of responses from the BL65x and route them
        to the appropriate queue or handler.
        """
        if verbose:
            print(f"data received {data}")
        self.text += data.decode('utf-8', errors='ignore').strip('\n')

        if self.text == "":
            return

        start = self.text.find('{')
        end = self.text.rfind('}')
        open_count = self.text.count('{')
        close_count = self.text.count('}')
        if verbose_bracket:
            print(f"{start} {end} {open_count} {close_count}")
        if open_count > 0 and open_count == close_count:
            self.handle_packet(str(self.text[start:end+1]))
            self.text = ""
        elif start >= 0:
            self.text = self.text[start:]
        elif end >= 0:
            self.text = ""
        else:
            for line in self.text.split('\r'):
                line = line.replace('\r', '').replace('\n', '')
                if line != "":
                    if line.startswith("AD"):
                        self.ads.put(line)
                    elif line.startswith("NOCARRIER"):
                        self.events.put(line)
                        self.no_carrier.set()
                    elif line.startswith("passkey?"):
                        self.events.put(line)
                    elif line.startswith("encrypt"):
                        self.pairing_done.set()
                    elif line.startswith("discon"):
                        self.no_carrier.set()
                    else:
                        self.responses.put(line)
            self.text = ""

    def handle_packet(self, packet):
        raise NotImplementedError(
            'please implement functionality in handle_packet')

    def handle_event(self, event):
        raise NotImplementedError(
            'Spontaneous message received implement functionality in handle_event')

    def command(self, cmd, response='OK', timeout=1):
        """
        Set an AT command and wait for the response.
        """
        cmd = (cmd + '\r').encode('utf-8')
        with self.lock:  # ensure that just one thread is sending commands at once
            self.transport.write(cmd)
            lines = []
            while True:
                try:
                    line = self.responses.get(timeout=timeout)
                    # print(line)
                    lines.append(line)
                    if line.startswith(response):
                        return lines
                    elif line.startswith("ERROR"):
                        return lines
                except queue.Empty:
                    # print(lines)
                    raise ATException(f'AT command timeout for {cmd}')


class BL65x(ATProtocol):
    """
    For communication with BL65x module in VSP and non-VSP mode (pairing only).
    """
    vspConnection = False
    inputJSON = ""

    def __init__(self, fname="config.json"):
        super().__init__()
        print("transport init")
        self.json_packets = queue.Queue()
        self.allow_non_vsp = True
        self.bd_addrs = []
        self.connection_interval_ms = 7500
        self.bd_addr_index = 0
        self.disconnect_timeout = 10.0
        self.connection_timeout = 10.0
        self.passkey = 123456
        self._bleConfig(fname)
        self.current_addr = self.bd_addrs[self.bd_addr_index]
        self.logger = logging.getLogger('LairdDongle')

    def _bleConfig(self, fname: str) -> None:
        with open(fname, 'r') as f:
            c = json.load(f)
            if "bd_addrs" in c:
                self.bd_addrs = c["bd_addrs"]
            if "bd_addr_index" in c:
                self.bd_addr_index = c["bd_addr_index"]
            if "ble_connection_interval_us" in c:
                self.connection_interval_us = c["ble_connection_interval_us"]
            if "disconnect_timeout" in c:
                self.disconnect_timeout = c["disconnect_timeout"]
            if "connection_timeout" in c:
                self.connection_timeout = c["connection_timeout"]
            if "passkey" in c:
                self.passkey = c["passkey"]

    def handle_packet(self, packet):
        #self.logger.debug(f"response {packet}")
        try:
            jsonObject = json.loads(packet)
            self.json_packets.put(jsonObject)
        except ValueError:
            pass

    def handle_event(self, event):
        if event.startswith("NOCARRIER"):
            self.vspConnection = False
            self.logger.info("Disconnected")
        elif event.startswith("passkey?"):
            try:
                self.command(f"AT+PRSP 1,{self.passkey}",
                             response='OK', timeout=2)
            except:
                self.logger.info("Failed to Encrypt")
        else:
            self.logger.warning(f'unhandled event: {expr(event)}')

    # - - - example commands

    def reset(self):
        self.command("ATZ")      # SW-Reset BT module

    def save_sregs(self):
        self.command("AT&W")

    def get_mac_address(self):
        return self.ati(4)

    def ati(self, index=0):
        return self.command(f"ATI {index}")

    def get_attribute(self, attribute):
        return self.command(f"ATS {attribute}?")

    def set_attribute(self, attribute, value):
        return self.command(f"ATS {attribute}={value}")

    def scan(self, scanDuration=0, nameMatch="", rssiThreshold=-128):
        logging.debug(f"Starting Scan for {nameMatch}")
        return self.command(f'AT+LSCN {scanDuration},"{nameMatch}",{rssiThreshold}', timeout=2)

    def cancel_scan(self):
        logging.debug(f"Stopping Scan")
        return self.command('AT+LSCNX', timeout=2)

    def allow_pairing(self):
        """
        When connecting to multiple devices this must be set to
        true to allow pairing/bonding for each device.
        """
        self.allow_non_vsp = True

    def connect(self, addr, timeout=1):
        """
        First try to connect in VSP mode.
        VSP mode previously only allowed just works pairing.
        Otherwise, connect in non-VSP mode so that we can pair.
        If that is successful, then we can connect in VSP mode.
        """
        if self.vspConnection == False:
            with self.json_packets.mutex:
                self.json_packets.queue.clear()
            with self.responses.mutex:
                self.responses.queue.clear()
            with self.events.mutex:
                self.events.queue.clear()
            try:
                self.logger.info(f"Attempting to connect to {addr}")
                self.command(
                    f"ATD {addr}", response='CONNECT', timeout=timeout)
                self.vspConnection = True
                self.logger.info("Connected in VSP mode")
            except:
                if self.allow_non_vsp:
                    self.allow_non_vsp = False
                    step_time = 2
                    try:
                        self.logger.info("Attempting non-VSP connection")
                        self.command(
                            f"AT+LCON {addr}", response='connect', timeout=step_time)
                        self.logger.info("Connected in non-VSP mode")
                        try:
                            self.pairing_done.clear()
                            self.command(
                                "AT+PAIR 1", response='OK', timeout=step_time)
                            self.pairing_done.wait(timeout=step_time)
                            # Without this delay encrypt will come back as 1 when it fails on the sensor.
                            # because the connection is being closed too quickly.
                            time.sleep(step_time)
                            self.logger.info("Encrypted in non-VSP mode")
                            self.no_carrier.clear()
                            # Disconnect must use this command when not in VSP mode
                            self.command(
                                "AT+LDSC 1", response='OK', timeout=step_time)
                            self.no_carrier.wait(
                                timeout=self.disconnect_timeout)
                            self.logger.info("Closed non-VSP connection")
                            self.logger.info(
                                "Now that we have paired in non-VSP mode we can try a VSP connection")
                            # This delay is required in order for the next connection to be successful.
                            time.sleep(step_time)
                            self.connect(addr, timeout)
                        except:
                            self.logger.info("Unable to pair")
                    except:
                        self.logger.info("Unable to connect in non-VSP mode")
                else:
                    self.logger.info(
                        "Already tried to connect in non-VSP mode")

    def disconnect(self):
        self.no_carrier.clear()
        if self.vspConnection == True:
            with self.lock:
                self.logger.debug("Requesting Disconnect")
                self.transport.write(b'^')
                time.sleep(0.300)
                self.transport.write(b'^')
                time.sleep(0.300)
                self.transport.write(b'^')
                time.sleep(0.300)
                self.transport.write(b'^')
            self.no_carrier.wait(timeout=self.disconnect_timeout)

    def send_json(self, data, delay):
        if self.vspConnection:
            # The delay is for the serial port version because the UART doesn't have
            # flow control.  It shouldn't be necessary for the BLE version.
            # time.sleep(delay)
            with self.lock:
                self.transport.write(data.encode('utf-8'))
        else:
            self.logger.warning(
                "Attempt to send VSP data without a connection")

    def get_json(self, timeout=1):
        try:
            jsonObject = self.json_packets.get(timeout=timeout)
            return jsonObject
        except:
            self.logger.warning("Get JSON timeout")
            return None

    def get_scan(self, timeout=10):
        try:
            return self.ads.get(timeout=timeout)
        except:
            return None

    def secondary_initialization(self, connection_interval_us=30000):
        """
        After the serial port is open - initialize the BLE dongle.
        """
        # Bug 17747
        # The soft reset will only work if the radio isn't in a
        # connection. Since the FTDI DCD line is connected to the
        # radio reset (nReset) it would be better to us pylibftdi
        # to put the FTDI chip into BitBang mode and do a hard
        # reset of the radio on start-up.
        #
        # Workaround - Unplug dongle and then plug it back in.
        self.reset()
        self.logger.debug("Radio Reset")
        self.logger.debug(f"Dongle BD Address: {self.get_mac_address()}")

        self.logger.debug("Initializing radio")
        # enable max bi-directional throughput and DLE (bits 3 and 4 set)
        self.set_attribute(attribute=100, value=24)
        # enable disconnect via ^^^^
        self.set_attribute(attribute=109, value=-1)
        # use 4 '^' to disconnect
        self.set_attribute(attribute=111, value=4)
        # ms delay between '^' to disconnect
        self.set_attribute(attribute=210, value=250)
        # us minimum connection interval
        self.set_attribute(attribute=300, value=connection_interval_us)
        # us maximum connection interval
        self.set_attribute(attribute=301, value=connection_interval_us)
        # Pairing mode cannot be set on-the-fly
        if self.get_attribute(attribute=107) != '4':
            # PairingIoCapability (0=JustWorks, 1=Disp with Y/N, 2=Kboard only, 3=Disp Only 4=Kboard+Disp)
            self.set_attribute(attribute=107, value=4)
            self.save_sregs()
            self.reset()
        # Return advertisement data when scanning
        self.command("AT+SFMT 1", response='OK')
        self.logger.info("Radio initialized")

        pass


if __name__ == "__main__":
    pass
