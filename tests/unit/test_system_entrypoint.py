"""Unit tests for consolidated local stack entrypoint module."""

from unittest.mock import MagicMock, patch

from scripts.system_entrypoint import start_stack_processes, write_scanner_pid


@patch("scripts.system_entrypoint.subprocess.Popen")
@patch("scripts.system_entrypoint.time.sleep")
@patch("scripts.system_entrypoint.write_scanner_pid")
def test_start_stack_processes_starts_api_scanner_and_web(
    mocked_write_pid,
    mocked_sleep,
    mocked_popen,
):
    """start_stack_processes must spawn the three official runtime processes."""
    api_proc = MagicMock(pid=101)
    scanner_proc = MagicMock(pid=202)
    web_proc = MagicMock(pid=303)
    mocked_popen.side_effect = [api_proc, scanner_proc, web_proc]

    processes = start_stack_processes("python-exe")

    assert processes == [api_proc, scanner_proc, web_proc]
    assert mocked_popen.call_count == 3
    mocked_write_pid.assert_called_once_with(202)
    mocked_sleep.assert_called_once_with(5)


@patch("builtins.open")
def test_write_scanner_pid_persists_pid(mocked_open):
    """write_scanner_pid must write scanner PID to pid file for web controls."""
    handle = MagicMock()
    mocked_open.return_value.__enter__.return_value = handle

    write_scanner_pid(555)

    handle.write.assert_called_once_with("555")
