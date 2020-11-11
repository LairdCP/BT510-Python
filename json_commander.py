
"""
BT510 commands (serial or BLE).
This is a subset of the jtester commands used for verification.
"""

import time
import json
import random
import string
import logging
from jsonrpcclient.requests import Request


class jtester:
    def __init__(self, fname="config.json"):
        """ JSON tester that is independent of the transport """
        print("jtester init")
        self.protocol = None
        self.inter_message_delay = 0.01
        self.reset_delay = 10
        self.reset_after_write_delay = 2
        self.get_queue_timeout = 2.0
        self.ok = 0
        self.fail = 0
        self._LoadConfig(fname)
        self.logger = logging.getLogger('jtester')

    def _LoadConfig(self, fname: str) -> None:
        with open(fname, 'r') as f:
            c = json.load(f)
            if "inter_message_delay" in c:
                self.inter_message_delay = c["inter_message_delay"]
            if "reset_delay" in c:
                self.reset_delay = c["reset_delay"]

    def _send_json(self, text):
        if self.protocol is not None:
            self.logger.debug(text)
            self.protocol.send_json(text, self.inter_message_delay)
        else:
            self.logger.warning("Transport not available")

    def _get_json(self):
        if self.protocol is not None:
            result = self.protocol.get_json(self.get_queue_timeout)
            self.logger.debug(json.dumps(result))
            return result
        else:
            return None

    def set_protocol(self, protocol) -> None:
        self.protocol = protocol

    def IncrementOkCount(self) -> None:
        self.ok += 1

    def IncrementFailCount(self) -> None:
        self.fail += 1
        self.logger.error("Test Fail")

    def ExpectOk(self) -> None:
        response = self._get_json()
        if response is not None:
            if "result" in response:
                if response["result"] == "ok":
                    self.IncrementOkCount()
                    return
        self.IncrementFailCount()

    def ExpectError(self) -> None:
        response = self._get_json()
        if response is not None:
            if "error" in response:
                self.IncrementOkCount()
                return
        self.IncrementFailCount()

    def ExpectValue(self, name, value) -> None:
        response = self._get_json()
        if response is not None:
            if "result" in response:
                if response["result"] == "ok":
                    if value is None:
                        if name in response:
                            self.IncrementOkCount()
                            return
                    elif isinstance(value, str):
                        if response[name] == value.strip('\"'):
                            self.IncrementOkCount()
                            return
                    else:
                        if response[name] == value:
                            self.IncrementOkCount()
                            return
        self.IncrementFailCount()

    def ExpectValues(self, **pairs) -> None:
        responseFound = False
        error = 0
        response = self._get_json()
        if response is not None:
            if "result" in response:
                if response["result"] == "ok":
                    responseFound = True
                    for (name, value) in pairs.items():
                        if value is None:
                            if name not in response:
                                error += 1
                        elif isinstance(value, str):
                            if response[name] != value.strip('\"'):
                                error += 1
                        elif response[name] != value:
                            error += 1

        if not responseFound or error:
            self.IncrementFailCount()
        else:
            self.IncrementOkCount()

    def ExpectRange(self, name, imin, imax) -> None:
        response = self._get_json()
        if response is not None:
            if "result" in response:
                x = response["result"]
                if isinstance(x, int):
                    if x >= imin and x <= imax:
                        self.IncrementOkCount()
                        return
        self.IncrementFailCount()

    def ExpectInt(self) -> int:
        response = self._get_json()
        if response is not None:
            if "result" in response:
                value = response["result"]
                if isinstance(value, int):
                    self.IncrementOkCount()
                    return value
        self.IncrementFailCount()
        return -1

    def ExpectStr(self) -> str:
        response = self._get_json()
        if response is not None:
            if "result" in response:
                value = response["result"]
                if isinstance(value, str):
                    self.IncrementOkCount()
                    return value
        self.IncrementFailCount()
        return ""

    def ExpectLog(self) -> list:
        response = self._get_json()
        if response is not None:
            if "result" in response:
                value = response["result"]
                if isinstance(value, list):
                    self.IncrementOkCount()
                    return value
        self.IncrementFailCount()
        return [0, ""]

    def SendFactoryReset(self) -> None:
        time.sleep(self.reset_after_write_delay)
        self._send_json(str(Request("factoryReset")))
        self.ExpectOk()
        time.sleep(self.reset_delay)

    def SendReboot(self) -> None:
        time.sleep(self.reset_after_write_delay)
        self._send_json(str(Request("reboot")))
        self.ExpectOk()
        time.sleep(self.reset_delay)

    def SendEnterBootloader(self) -> None:
        time.sleep(self.reset_after_write_delay)
        self._send_json(str(Request("reboot", 1)))
        self.ExpectOk()
        time.sleep(self.reset_delay)

    def EpochTest(self, epoch: int) -> None:
        """Test epoch commands"""
        delay = 3
        self._send_json(str(Request(f"setEpoch", epoch)))
        self.ExpectOk()
        time.sleep(delay)
        self._send_json(str(Request("getEpoch")))
        self.ExpectRange("epoch", epoch + delay - 1, epoch + delay + 1)

    def LedTest(self) -> None:
        self._send_json(str(Request("ledTest", 1000)))
        self.ExpectOk()

    def Dump(self) -> None:
        """ Test dump command without any parameters """
        self._send_json(str(Request("dump")))
        response = self._get_json()
        ok = False
        if response is not None:
            if "result" in response:
                if response["result"] == "ok":
                    self.IncrementOkCount()
                else:
                    self.IncrementFailCount()

    def Unlock(self) -> None:
        kwargs = {"lock": 0}
        self._send_json(str(Request("set", **kwargs)))
        self.ExpectOk()

    def Lock(self) -> None:
        kwargs = {"lock": 1}
        self._send_json(str(Request("set", **kwargs)))
        self.ExpectOk()

    def GetAttribute(self, name: str):
        """Get an attribute by its name - Doesn't affect test ok count"""
        self._send_json(str(Request("get", name)))
        response = self._get_json()
        result = None
        if response is not None:
            if "result" in response:
                if response["result"] == "ok":
                    if name in response:
                        value = response[name]
                        if isinstance(value, str):
                            result = value.strip('\"')
                        else:
                            result = value
        self.logger.info(f'"{name}": {result}')
        return result

    def SetAttributes(self, **kwargs) -> None:
        self._send_json(str(Request("set", **kwargs)))
        self.ExpectOk()

    def SetEpoch(self, epoch: int) -> None:
        self._send_json(str(Request("setEpoch", epoch)))
        self.ExpectOk()

    def PrepareLog(self) -> int:
        self._send_json(str(Request("prepareLog", 0)))  # fifo mode
        return self.ExpectInt()

    def ReadLog(self, count: int) -> list:
        self._send_json(str(Request("readLog", count)))
        return self.ExpectLog()

    def AckLog(self, count: int) -> int:
        self._send_json(str(Request("ackLog", count)))
        result = self.ExpectInt()
        return result

    def LogResults(self):
        self.logger.info(f"Pass: {self.ok} Fail: {self.fail}")


if __name__ == "__main__":
    pass
