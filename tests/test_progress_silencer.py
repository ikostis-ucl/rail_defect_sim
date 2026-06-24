import io
import sys
from app.progress.silencer import _OutputSilencer


def test_context_manager_enters_and_exits():
    with _OutputSilencer() as s:
        assert s is not None


def test_stdout_restored_after_exit():
    original = sys.stdout
    with _OutputSilencer():
        pass
    assert sys.stdout is original


def test_stderr_restored_after_exit():
    original = sys.stderr
    with _OutputSilencer():
        pass
    assert sys.stderr is original


def test_exit_called_on_exception():
    original_stdout = sys.stdout
    try:
        with _OutputSilencer():
            raise ValueError("boom")
    except ValueError:
        pass
    assert sys.stdout is original_stdout


def test_multiple_context_uses_do_not_stack():
    with _OutputSilencer():
        pass
    with _OutputSilencer():
        pass
    # Both exited cleanly — no error means fds were properly restored
