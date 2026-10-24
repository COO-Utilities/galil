# pyright: reportImplicitOverride=false
"""Driver for the Galil DMC-1846 (4-axis PCI) motion controller."""
from __future__ import annotations

from collections.abc import Sequence
from typing import override

from .base import GalilBase

# The DMC-1846 has no general purpose analog outputs, so each axis's +/-10V motor
# command line is used instead. With the servo on and KP, KI and KD all zero, the
# motor command is just the offset (OF), so OF sets the output voltage directly.
# See the DMC-1806 Firmware Command Reference, which covers the DMC-18x6 family.
ANALOG_OUTPUTS = ("A", "B", "C", "D")

# Range of OF, TL and TT
VOLTAGE_MAX = 9.9982
VOLTAGE_MIN = -9.9982


class DMC1846(GalilBase):
    """Controls a Galil DMC-1846 controller over gclib"""

    axes = ANALOG_OUTPUTS
    voltage_min = VOLTAGE_MIN
    voltage_max = VOLTAGE_MAX

    def __init__(
        self,
        analog_axes: Sequence[str] = ANALOG_OUTPUTS,
        log: bool = True,
        logfile: str | None = None,
    ) -> None:
        """
        :param analog_axes: axes whose motor command lines are used as analog outputs.
            initialize() zeroes the gains on these axes, so leave out any axis driving a motor.
        """
        super().__init__(log, logfile)
        for axis in analog_axes:
            if axis not in ANALOG_OUTPUTS:
                raise ValueError(f"Axis {axis} does not exist, must be one of {ANALOG_OUTPUTS}")
        self.analog_outputs = tuple(analog_axes)

    @override
    def _set_command(self, channel: str, voltage: float) -> str:
        return f"OF{channel}={voltage}"

    @override
    def _get_command(self, channel: str) -> str:
        # TT reports the motor command voltage actually being output
        return f"MG_TT{channel}"

    @override
    def _init_commands(self) -> tuple[str, ...]:
        # MT can only be changed with the motor off (MO). Zero the gains and offset
        # before turning the servo back on (SH) so the output starts at 0V, and raise
        # the torque limit (TL), which clamps the output, to its max.
        return tuple(
            command
            for axis in self.analog_outputs
            for command in (
                f"MO{axis}",
                f"MT{axis}=1",
                f"KP{axis}=0",
                f"KI{axis}=0",
                f"KD{axis}=0",
                f"OF{axis}=0",
                f"TL{axis}={VOLTAGE_MAX}",
                f"SH{axis}",
            )
        )
