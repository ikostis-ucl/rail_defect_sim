import io
import os
import sys
from contextlib import AbstractContextManager


class _OutputSilencer(AbstractContextManager["_OutputSilencer"]):
    """Temporarily redirect stdout/stderr to os.devnull."""

    def __init__(self) -> None:
        self._devnull = None
        self._saved_fds: list[tuple[int, int]] = []

    def __enter__(self) -> "_OutputSilencer":
        self._devnull = open(os.devnull, "w", encoding="utf-8")
        for stream in (sys.stdout, sys.stderr):
            try:
                fd = stream.fileno()
            except (AttributeError, OSError, ValueError, io.UnsupportedOperation):
                continue
            saved_fd = os.dup(fd)
            os.dup2(self._devnull.fileno(), fd)
            self._saved_fds.append((fd, saved_fd))
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        for fd, saved_fd in reversed(self._saved_fds):
            os.dup2(saved_fd, fd)
            os.close(saved_fd)
        self._saved_fds.clear()
        if self._devnull is not None:
            self._devnull.close()
            self._devnull = None
