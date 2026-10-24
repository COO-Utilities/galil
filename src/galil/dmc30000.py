# pyright: reportImplicitOverride=false
"""Driver for the Galil DMC-30000 series (single-axis) motion controller."""
from __future__ import annotations

from typing import override

from .base import GalilBase

# AO1 and AO2 are +/-10V, 16-bit DACs. Clamp to the largest value the DAC can represent.
VOLTAGE_MAX = 9.9998
VOLTAGE_MIN = -9.9998

# AO1 is the axis A motor command line; it only works as a general analog output
# after initialize(), and only on models with an internal sine drive (e.g. DMC-30012,
# DMC-30014, DMC-30017). AO2 is always a general analog output.
ANALOG_OUTPUTS = (1, 2)
AXES = ("A",)


class DMC30000(GalilBase):
    """Controls a Galil DMC-30000 series controller over gclib"""

    axes = AXES
    analog_outputs = ANALOG_OUTPUTS
    voltage_min = VOLTAGE_MIN
    voltage_max = VOLTAGE_MAX

    @override
    def _set_command(self, channel: int, voltage: float) -> str:
        return f"AO {channel},{voltage}"

    @override
    def _get_command(self, channel: int) -> str:
        return f"MG@AO[{channel}]"

    @override
    def _init_commands(self) -> tuple[str, ...]:
        # MT can only be changed with the motor off (MO). For AO1 to act as a general
        # analog output MT must be 1 or -1, BR 0, and BA set for axis A.
        return ("MO A", "MT 1", "BR 0", "BA A")

    @property
    def ipaddr(self) -> str | None:
        """IP address of the currently connected Galil, if any."""
        return self._address
