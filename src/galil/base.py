# pyright: reportImplicitOverride=false
"""Shared gclib connection and analog output logic for Galil motion controllers."""
from __future__ import annotations

from typing import Self, override

import gclib  # pyright: ignore[reportMissingImports]  # Linux and Windows only, requires Galil software
from hardware_device_base import HardwareDeviceBase

from .codes import AxisStatus, ErrorCode, StopCode

type Channel = int | str


class GalilBase(HardwareDeviceBase):
    """
    Controls a Galil controller over gclib.

    Subclasses describe their hardware by setting axes, analog_outputs, voltage_min and
    voltage_max and implementing _set_command, _get_command and _init_commands.
    """

    axes: tuple[str, ...] = ()
    analog_outputs: tuple[Channel, ...] = ()
    voltage_min: float = 0.0
    voltage_max: float = 0.0

    def __init__(self, log: bool = True, logfile: str | None = None) -> None:
        """
        :param bool log: If True, log to file, otherwise log to stdout.
        :param str logfile: filename to log to, defaults to the driver's module name
        """
        super().__init__(log, logfile or type(self).__module__.rsplit(".", 1)[-1])
        self._address: str | None = None
        self._client: gclib.Controller | None = None
        self._last_reply: str | None = None
        self.last_error: ErrorCode | int | None = None

    @override
    def connect(self, address: str, baud_rate: int | None = None) -> None:
        """
        Opens a gclib connection to the Galil.

        :param str address: gclib address of the Galil, e.g. an IP address for ethernet
            controllers or "GALILPCI1" (Windows) / "/dev/galilpci0" (Linux) for PCI cards
        :param int baud_rate: Baud rate of the Galil (only required for serial connection)
        """
        if self.is_connected():
            self.disconnect()

        self.report_info(f"Connecting to Galil at {address}...")
        try:
            self._client = (
                gclib.Controller(address, baud_rate)
                if baud_rate
                else gclib.Controller(address)
            )
        except gclib.Error as e:
            self.report_error(f"Could not connect to Galil at {address}: {e}")
            return

        self._address = address
        self._set_connected(True)
        self.report_info(f"Successfully connected to Galil at {address}")

    @override
    def disconnect(self) -> None:
        """Disconnects Controller from Galil"""
        if self._client is None:
            self.report_error("Controller not defined. Try to connect to a galil first")
            return

        try:
            self.report_info(f"Disconnecting Galil at {self._address}")
            self._client.close()
            self._set_connected(False)
            self.report_info("Closed connection")
        except gclib.Error as e:
            self.report_error(f"Failed to disconnect: {e}")

    def reconnect(self) -> bool:
        """Reconnects controller. Only works if used disconnect in the past"""
        if self._client is None:
            self.report_error("Controller not defined. Try to connect to a galil first")
            return False
        if self.is_connected():
            self.report_error("Controller is connected. Disconnect before trying to reconnect")
            return False

        try:
            self.report_info(f"Connecting to galil at {self._address}...")
            self._client.open()
            self._set_connected(True)
            self.report_info(f"Connected Controller at {self._address}")
            return True
        except gclib.Error as e:
            self.report_error(f"Failed to reconnect: {e}")

        return False

    @override
    def _send_command(self, command: str) -> bool:
        """
        Sends a command to Galil and return if command was successfully sent

        :param str command: command to send over
        """
        if self._client is None:
            self.report_error("Controller not defined. Try to connect to a galil first")
            return False

        try:
            self._last_reply = self._client.command(command)
            self.last_error = None
            self.report_info(f"Command: {command} successfully sent")
            return True
        except gclib.Error as e:
            self._last_reply = None
            code, message = self._query_error_code()
            self.last_error = code
            self.report_error(
                f"Command {command} failed: {message or e}", errno=-1 if code is None else code
            )

        return False

    def _query_error_code(self) -> tuple[ErrorCode | int | None, str | None]:
        """
        Returns the controller's code and message for why the last command was rejected.
        Reading TC clears the code on the controller.
        """
        if self._client is None:
            return None, None
        try:
            reply = self._client.command("TC1")
        except gclib.Error:
            return None, None

        number, _, message = reply.strip().partition(" ")
        try:
            code = int(number)
        except ValueError:
            return None, None
        if code == 0:
            return None, None
        try:
            return ErrorCode(code), message.strip()
        except ValueError:
            return code, message.strip()

    def _query_number(self, command: str) -> float | None:
        """Sends a query command and returns its reply as a number"""
        if not self._send_command(command):
            return None
        reply = self._read_reply()
        try:
            return float(reply) if reply is not None else None
        except ValueError:
            self.report_error(f"Unexpected reply to {command}: {reply!r}")
            return None

    @override
    def _read_reply(self) -> str | None:
        """Returns the last reply from the last command"""
        return self._last_reply

    def _set_command(self, channel: Channel, voltage: float) -> str:
        """Returns the command that sets an analog output to the given voltage"""
        raise NotImplementedError

    def _get_command(self, channel: Channel) -> str:
        """Returns the command that reports the voltage on an analog output"""
        raise NotImplementedError

    def _init_commands(self) -> tuple[str, ...]:
        """Returns the commands that configure the analog outputs for use"""
        raise NotImplementedError

    def _validate_axis(self, axis: str) -> None:
        if axis not in self.axes:
            raise ValueError(f"Axis {axis} does not exist, must be one of {self.axes}")

    def _validate_channel(self, channel: Channel) -> None:
        if channel not in self.analog_outputs:
            raise ValueError(
                f"Analog output {channel} does not exist, must be one of {self.analog_outputs}"
            )

    def _validate_voltage(self, voltage: float) -> None:
        if not (self.voltage_min <= voltage <= self.voltage_max):
            raise ValueError(
                f"Voltage {voltage} out of range [{self.voltage_min}, {self.voltage_max}]"
            )

    def set_analog_output(self, channel: Channel, voltage: float) -> bool:
        """
        Sets an analog output to the given voltage and returns if it was successfully sent

        :param channel: analog output, one of analog_outputs
        :param float voltage: voltage between voltage_min and voltage_max
        """
        self._validate_channel(channel)
        self._validate_voltage(voltage)
        success = self._send_command(self._set_command(channel, voltage))
        if success:
            self.report_info(f"Set analog output {channel} to {voltage} volts")
        else:
            self.report_error(f"Failed to set analog output {channel}")
        return success

    def get_analog_output(self, channel: Channel) -> float | None:
        """
        Returns the voltage currently output by the Galil on an analog output

        :param channel: analog output, one of analog_outputs
        """
        self._validate_channel(channel)
        return self._query_number(self._get_command(channel))

    def zero_outputs(self) -> bool:
        """Sets every analog output to 0V and returns if all were successfully sent"""
        results = [self.set_analog_output(channel, 0.0) for channel in self.analog_outputs]
        return all(results)

    def get_axis_status(self, axis: str) -> AxisStatus | None:
        """
        Returns the status bits of an axis. If MOTOR_OFF is set, the axis's motor
        command line is not being driven.

        :param str axis: axis letter, one of axes
        """
        self._validate_axis(axis)
        value = self._query_number(f"MG_TS{axis}")
        return AxisStatus(int(value)) if value is not None else None

    def get_stop_code(self, axis: str) -> StopCode | int | None:
        """
        Returns why an axis stopped, e.g. StopCode.STOPPED_BY_OFF_ON_ERROR

        :param str axis: axis letter, one of axes
        """
        self._validate_axis(axis)
        value = self._query_number(f"MG_SC{axis}")
        if value is None:
            return None
        try:
            return StopCode(int(value))
        except ValueError:
            return int(value)

    @override
    def initialize(self) -> bool:
        """Configures the controller so its analog outputs can be used"""
        # NOTE: This should eventually be fazed out and coded into the galil using #AUTO so it does this on startup
        if self._client is None:
            self.report_error("Client controller has not been defined")
            return False

        for command in self._init_commands():
            success = self._send_command(command)
            if not success:
                self.report_error(f"Initialization failed at command: {command}")
                return False

        self.report_info("Controller ready to operate")
        return True

    @property
    def address(self) -> str | None:
        """gclib address of the currently connected Galil, if any."""
        return self._address

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.disconnect()
