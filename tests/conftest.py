"""Stubs for gclib and hardware_device_base, installed before any driver is imported."""
import sys
import types

# Stub out external dependencies before importing the modules under test


def _install_fake_gclib() -> None:
    fake_gclib = types.ModuleType("gclib")

    class Error(Exception):
        pass

    class Controller:
        def __init__(self, ipaddr, baud_rate=None):
            self.ipaddr = ipaddr
            self.baud_rate = baud_rate

        def command(self, cmd):
            return ""

        def close(self):
            pass

        def open(self):
            pass

    fake_gclib.Error = Error
    fake_gclib.Controller = Controller
    sys.modules["gclib"] = fake_gclib


def _install_fake_hardware_base() -> None:
    fake_module = types.ModuleType("hardware_device_base")

    class HardwareDeviceBase:
        def __init__(self, log=True, logfile=""):
            self._log = log
            self._logfile = logfile
            self._connected = False

        def report_info(self, msg):
            pass

        def report_error(self, msg, errno=-1):
            self.errno = errno

        def _set_connected(self, value):
            self._connected = value

        def is_connected(self):
            return self._connected

    fake_module.HardwareDeviceBase = HardwareDeviceBase
    sys.modules["hardware_device_base"] = fake_module


_install_fake_gclib()
_install_fake_hardware_base()


# Helpers
class RecordingClient:
    """Fake gclib.Controller that records every command string it receives."""

    def __init__(self, reply: str = "1.2345"):
        self.commands: list[str] = []
        self.reply = reply

    def command(self, cmd: str) -> str:
        self.commands.append(cmd)
        return self.reply

    def close(self):
        pass

    def open(self):
        pass


class FailingClient(RecordingClient):
    """
    Fake client that rejects every command, to test failure paths. Like a real
    controller, it answers TC1 with the code for the rejected command.
    """

    def __init__(self, error_reply: str = "6 Number out of range\r\n"):
        super().__init__()
        self.error_reply = error_reply

    def command(self, cmd: str) -> str:
        self.commands.append(cmd)
        if cmd == "TC1":
            return self.error_reply
        raise sys.modules["gclib"].Error("simulated failure")
