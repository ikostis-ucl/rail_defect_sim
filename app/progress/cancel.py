"""Stopping a run cleanly.

Cancel is cancel: there is no pause and no resume, and a cancelled run is
started again from the beginning. What matters is that stopping leaves nothing
behind that a later run would mistake for good data.

The mechanism is a flag rather than an exception thrown from a signal handler.
A signal can arrive anywhere, including inside a Blender call that must not be
unwound halfway; setting a flag lets the run notice at its next checkpoint and
stop somewhere it chooses.

Nothing here imports ``bpy``.
"""

from __future__ import annotations

import signal
from pathlib import Path


class Cancelled(Exception):
    """Raised at a checkpoint once cancellation has been requested."""


class CancellationToken:
    """Set from a signal, read at checkpoints."""

    def __init__(self) -> None:
        self._requested = False

    @property
    def requested(self) -> bool:
        return self._requested

    def request(self) -> None:
        self._requested = True

    def check(self) -> None:
        """Raise if cancellation has been requested. Call between units of work."""
        if self._requested:
            raise Cancelled()


class cancel_on_signal:
    """Context manager translating SIGINT and SIGTERM into a token request.

    Restores the previous handlers on exit, so importing this never changes the
    behaviour of a process that is not using it. A second signal is left to the
    default handler: someone pressing Ctrl-C twice means it.
    """

    SIGNALS = (signal.SIGINT, signal.SIGTERM)

    def __init__(self, token: CancellationToken) -> None:
        self.token = token
        self._previous: dict = {}

    def __enter__(self) -> CancellationToken:
        for sig in self.SIGNALS:
            try:
                self._previous[sig] = signal.getsignal(sig)
                signal.signal(sig, self._handle)
            except (ValueError, OSError):
                pass      # not the main thread, or unsupported platform
        return self.token

    @staticmethod
    def _restorable(handler):
        """Whether a handler can be given back to ``signal.signal``.

        ``getsignal`` returns ``None`` when the current handler was installed
        outside Python — which is exactly what Blender does — and ``None`` is
        not a value ``signal.signal`` accepts. Restoring the default is the
        closest honest approximation.
        """
        return handler if callable(handler) or handler in (signal.SIG_IGN, signal.SIG_DFL) \
            else signal.SIG_DFL

    def _handle(self, signum, _frame) -> None:
        self.token.request()
        # Hand the next one straight back: a second Ctrl-C should stop the
        # process even if a checkpoint is far away.
        try:
            signal.signal(signum, self._restorable(self._previous.get(signum)))
        except (ValueError, OSError, TypeError):
            pass

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        for sig, handler in self._previous.items():
            try:
                signal.signal(sig, self._restorable(handler))
            except (ValueError, OSError, TypeError):
                pass


def clear_partial_output(output_dir: Path) -> list[Path]:
    """Remove what a cancelled run left behind, returning what was removed.

    A cancelled run has no usable output, so its half-written frames and video
    are noise at best and misleading at worst — a stale file from an earlier run
    is easy to mistake for the result of this one.

    Only the run's own output directory is touched. The section cache is *not*
    cleared: cached prototypes are written atomically, so whatever completed
    there is valid and worth keeping for the next attempt.
    """
    removed: list[Path] = []
    if not output_dir.exists():
        return removed

    for path in sorted(output_dir.iterdir()):
        if path.is_file():
            try:
                path.unlink()
                removed.append(path)
            except OSError:
                pass
    try:
        output_dir.rmdir()
    except OSError:
        pass      # not empty, or already gone — either is fine
    return removed
