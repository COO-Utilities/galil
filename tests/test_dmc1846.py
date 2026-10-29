import pytest

from conftest import FailingClient, RecordingClient
from galil import DMC1846, dmc1846


@pytest.fixture
def controller():
    ctrl = DMC1846(log=False)
    ctrl._client = RecordingClient()
    return ctrl


# Setter -> exact command sent


@pytest.mark.parametrize("axis", dmc1846.ANALOG_OUTPUTS)
def test_set_analog_output_sends_offset_command(controller, axis):
    assert controller.set_analog_output(axis, -3.25) is True
    assert controller._client.commands == [f"OF{axis}=-3.25"]


@pytest.mark.parametrize("bad_voltage", [10.0, -10.0, 9.9990, -9.9990])
def test_set_analog_output_rejects_out_of_range_voltage_and_sends_nothing(controller, bad_voltage):
    with pytest.raises(ValueError):
        controller.set_analog_output("A", bad_voltage)
    assert controller._client.commands == []


def test_set_analog_output_accepts_boundary_voltages(controller):
    controller.set_analog_output("A", dmc1846.VOLTAGE_MAX)
    controller.set_analog_output("B", dmc1846.VOLTAGE_MIN)
    assert controller._client.commands == ["OFA=9.9982", "OFB=-9.9982"]


@pytest.mark.parametrize("bad_channel", ["E", "a", 1])
def test_invalid_channel_raises_and_sends_nothing(controller, bad_channel):
    with pytest.raises(ValueError):
        controller.set_analog_output(bad_channel, 1.0)
    with pytest.raises(ValueError):
        controller.get_analog_output(bad_channel)
    assert controller._client.commands == []


def test_axes_not_in_analog_axes_are_rejected():
    ctrl = DMC1846(analog_axes=("A", "B"), log=False)
    ctrl._client = RecordingClient()
    with pytest.raises(ValueError):
        ctrl.set_analog_output("C", 1.0)
    assert ctrl._client.commands == []


def test_constructor_rejects_unknown_axis():
    with pytest.raises(ValueError):
        DMC1846(analog_axes=("A", "E"), log=False)


def test_set_analog_output_returns_false_when_command_fails(controller):
    controller._client = FailingClient()
    assert controller.set_analog_output("A", 1.0) is False


# Getter -> exact command sent + correct parsing


@pytest.mark.parametrize("axis", dmc1846.ANALOG_OUTPUTS)
def test_get_analog_output_queries_motor_command_and_parses_reply(controller, axis):
    controller._client.reply = " -1.1000"
    assert controller.get_analog_output(axis) == -1.1
    assert controller._client.commands == [f"MG_TT{axis}"]


def test_getter_returns_none_when_command_fails(controller):
    controller._client = FailingClient()
    assert controller.get_analog_output("A") is None


# Initialize


def test_initialize_configures_only_analog_axes_in_order():
    ctrl = DMC1846(analog_axes=("A", "C"), log=False)
    ctrl._client = RecordingClient()
    assert ctrl.initialize() is True
    assert ctrl._client.commands == [
        "MOA", "MTA=1", "KPA=0", "KIA=0", "KDA=0", "OFA=0", "TLA=9.9982", "SHA",
        "MOC", "MTC=1", "KPC=0", "KIC=0", "KDC=0", "OFC=0", "TLC=9.9982", "SHC",
    ]


def test_initialize_stops_at_first_failure(controller):
    controller._client = FailingClient()
    assert controller.initialize() is False
    assert controller._client.commands == ["MOA", "TC1"]


def test_connect_accepts_pci_address():
    ctrl = DMC1846(log=False)
    ctrl.connect("GALILPCI1")
    assert ctrl.is_connected()
    assert ctrl.address == "GALILPCI1"
