"""Behaviour shared by all drivers through GalilBase, mostly exercised via DMC1846."""
import pytest

from conftest import FailingClient, RecordingClient
from galil import DMC1846, DMC30000, AxisStatus, ErrorCode, StopCode


@pytest.fixture
def controller():
    ctrl = DMC1846(analog_axes=("A", "B"), log=False)
    ctrl._client = RecordingClient()
    return ctrl


# Error codes from TC


def test_failed_command_records_error_code_from_controller(controller):
    controller._client = FailingClient("6 Number out of range\r\n")
    assert controller._send_command("OFA=1") is False
    assert controller._client.commands == ["OFA=1", "TC1"]
    assert controller.last_error is ErrorCode.NUMBER_OUT_OF_RANGE
    assert controller.errno == ErrorCode.NUMBER_OUT_OF_RANGE


def test_unknown_error_code_is_kept_as_int(controller):
    controller._client = FailingClient("250 Some new error\r\n")
    controller._send_command("OFA=1")
    assert controller.last_error == 250
    assert not isinstance(controller.last_error, ErrorCode)


@pytest.mark.parametrize("reply", ["0", "garbage", ""])
def test_unusable_tc_reply_leaves_no_error_code(controller, reply):
    controller._client = FailingClient(reply)
    controller._send_command("OFA=1")
    assert controller.last_error is None
    assert controller.errno == -1


def test_successful_command_clears_last_error(controller):
    controller.last_error = ErrorCode.OPERAND_ERROR
    assert controller._send_command("OFA=1") is True
    assert controller.last_error is None


# Axis status from TS and stop code from SC


def test_get_axis_status_parses_bits(controller):
    controller._client.reply = " 44.0000"  # motor off, both limits inactive
    status = controller.get_axis_status("B")
    assert controller._client.commands == ["MG_TSB"]
    assert status == (
        AxisStatus.MOTOR_OFF | AxisStatus.FORWARD_LIMIT_INACTIVE | AxisStatus.REVERSE_LIMIT_INACTIVE
    )
    assert AxisStatus.IN_MOTION not in status


def test_get_stop_code_parses_known_code(controller):
    controller._client.reply = " 8.0000"
    assert controller.get_stop_code("A") is StopCode.STOPPED_BY_OFF_ON_ERROR
    assert controller._client.commands == ["MG_SCA"]


def test_get_stop_code_keeps_unknown_code_as_int(controller):
    controller._client.reply = "250.0000"
    assert controller.get_stop_code("A") == 250


def test_status_queries_return_none_when_command_fails(controller):
    controller._client = FailingClient()
    assert controller.get_axis_status("A") is None
    assert controller.get_stop_code("A") is None


@pytest.mark.parametrize("bad_axis", ["E", "a", ""])
def test_status_queries_reject_unknown_axis(controller, bad_axis):
    with pytest.raises(ValueError):
        controller.get_axis_status(bad_axis)
    with pytest.raises(ValueError):
        controller.get_stop_code(bad_axis)
    assert controller._client.commands == []


# zero_outputs


def test_zero_outputs_sets_every_analog_output_to_zero(controller):
    assert controller.zero_outputs() is True
    assert controller._client.commands == ["OFA=0.0", "OFB=0.0"]


def test_zero_outputs_tries_every_output_and_reports_failure(controller):
    controller._client = FailingClient()
    assert controller.zero_outputs() is False
    assert controller._client.commands == ["OFA=0.0", "TC1", "OFB=0.0", "TC1"]


# Logging


def test_default_logfile_is_the_driver_module_name():
    assert DMC1846(log=False)._logfile == "dmc1846"
    assert DMC30000(log=False)._logfile == "dmc30000"
    assert DMC30000(log=False, logfile="fsm")._logfile == "fsm"
