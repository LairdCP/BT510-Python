
"""
Serial transport for communicating with BT510.
Used in test fixture and for bench testing.
"""

import time
import json
import serial
import serial.threaded
import queue
import logging
from json_commander import jtester

verbose = False


class JsonPacket(serial.threaded.Protocol):
    """
    The JSON packet isn't framed over the transport layer, but it does have { and }
    The class also keeps track of the transport.
    """

    def __init__(self):
        super().__init__()
        self.text = ""
        self.transport = None

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

    def data_received(self, data):
        self.text += data.decode('utf-8')
        if verbose:
            print(f"data received {self.text}")

        # Filter out everything but responses.
        # The terminal inserts newlines and also may have other debug text.
        # [Unexpectedly] A line feed may be returned if all of the data hasn't come from the serial thread.
        if self.text.rfind('\r\n') < 0 or self.text.find('{') < 0 or self.text.rfind('}') < 0:
            return

        start = self.text.find('{')
        end = self.text.rfind('}')
        if start >= 0 and end > start:
            if self.text.find("result") > 0 or self.text.find("error") > 0:
                self.handle_packet(str(self.text[start:end+1]))

        self.text = ""

    def handle_packet(self, packet):
        """Process packets - to be overridden by subclassing"""
        raise NotImplementedError(
            'please implement functionality in handle_packet')


class JsonSerialReader(jtester, JsonPacket):
    """
    Read and write (Unicode) from/to serial port.
    """

    def __init__(self):
        super().__init__()
        if verbose:
            print("json serial reader transport init")
        self.json_packets = queue.Queue()
        self.logger = logging.getLogger('JsonSerialReader')

    def handle_packet(self, packet):
        if verbose:
            self.logger.debug(f"response {packet}")
        try:
            jsonObject = json.loads(packet)
            self.json_packets.put(jsonObject)
        except ValueError:
            pass

    def send_json(self, text, delay):
        if verbose:
            self.logger.debug(text)
        # Sleep is to prevent lost characters on Uart without flow control.
        time.sleep(delay)
        self.transport.write(text.encode('utf-8'))

    def get_json(self, timeout):
        try:
            jsonObject = self.json_packets.get(timeout=timeout)
            return jsonObject
        except:
            return None

    def connect(self, addr, wait_for_user=False, timeout=1):
        """Not used for serial port"""
        pass

    def disconnect(self):
        """Not used for serial port"""
        pass

    def secondary_initialization(self, connection_interval_us=30000):
        """Not used for serial port"""
        pass


if __name__ == "__main__":
    pass
