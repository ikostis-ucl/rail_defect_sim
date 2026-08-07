"""Where progress events go.

A run emits events once; reporters decide what to do with them. That is the
whole point of the split: a headless VM and a browser see the same run, because
they are reading the same events rendered two ways rather than two independent
implementations that can drift.

``ConsoleReporter`` is what a person watching a terminal gets — one short line
per phase, deliberately quiet, because the alternative is Blender's own output
firehose. ``JsonReporter`` writes one JSON object per line for a program.
``MultiReporter`` runs both, which is the normal case for a UI-launched run on a
machine someone may also be watching.

Nothing here imports ``bpy``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TextIO

from app.progress.events import EventKind, Phase, ProgressEvent


class Reporter:
    """Receives events. The default does nothing, which is a valid choice."""

    def emit(self, event: ProgressEvent) -> None:
        """Handle one event."""

    def close(self) -> None:
        """Release anything held open."""

    # ── Convenience, so callers never build events by hand ────────────────────

    def phase_start(self, phase: Phase, total: int | None = None, message: str = "") -> None:
        self.emit(ProgressEvent(EventKind.PHASE_START, phase, total=total, message=message))

    def progress(self, phase: Phase, done: int, total: int | None = None) -> None:
        self.emit(ProgressEvent(EventKind.PROGRESS, phase, done=done, total=total))

    def phase_end(self, phase: Phase, message: str = "") -> None:
        self.emit(ProgressEvent(EventKind.PHASE_END, phase, message=message))

    def done(self, message: str = "", **detail) -> None:
        self.emit(ProgressEvent(EventKind.DONE, message=message, detail=detail))

    def cancelled(self, message: str = "", **detail) -> None:
        self.emit(ProgressEvent(EventKind.CANCELLED, message=message, detail=detail))

    def failed(self, message: str, **detail) -> None:
        self.emit(ProgressEvent(EventKind.FAILED, message=message, detail=detail))


class ConsoleReporter(Reporter):
    """A short, readable account for a person, including over SSH.

    Deliberately terse. The reason this exists rather than simply letting
    Blender print is that Blender's own output is voluminous and mostly
    irrelevant to someone waiting for a video: the useful signal is which phase
    is running and how far along it is.
    """

    #: How often to reprint progress within a phase, as a fraction.
    STEP = 0.1

    def __init__(self, stream: TextIO | None = None) -> None:
        self.stream = stream if stream is not None else sys.stdout
        self._last_fraction: dict[Phase, float] = {}

    def emit(self, event: ProgressEvent) -> None:
        line = self._render(event)
        if line:
            print(line, file=self.stream, flush=True)

    def _render(self, event: ProgressEvent) -> str:
        if event.kind is EventKind.PHASE_START:
            total = f" ({event.total})" if event.total else ""
            self._last_fraction.pop(event.phase, None)
            return f"[{event.phase}] start{total}"

        if event.kind is EventKind.PROGRESS:
            fraction = event.fraction
            if fraction is None:
                return ""
            last = self._last_fraction.get(event.phase, -1.0)
            if fraction < 1.0 and fraction - last < self.STEP:
                return ""      # too soon since the last line
            self._last_fraction[event.phase] = fraction
            return f"[{event.phase}] {fraction:>4.0%}  {event.done}/{event.total}"

        if event.kind is EventKind.PHASE_END:
            return f"[{event.phase}] done{'  ' + event.message if event.message else ''}"

        if event.kind is EventKind.DONE:
            return event.message or "Finished."
        if event.kind is EventKind.CANCELLED:
            return event.message or "Cancelled."
        if event.kind is EventKind.FAILED:
            return f"Failed: {event.message}"
        return ""


class JsonReporter(Reporter):
    """One JSON object per line, for a program.

    Writes to a **file** rather than stdout by default. Blender writes copiously
    to stdout and a consumer cannot filter a stream it does not control, so
    mixing the two would put the burden of separating them on every caller.
    """

    def __init__(self, path: str | Path | None = None, stream: TextIO | None = None) -> None:
        if stream is not None:
            self._stream, self._owns = stream, False
        else:
            self._stream = open(Path(path), "w", encoding="utf-8")
            self._owns = True

    def emit(self, event: ProgressEvent) -> None:
        self._stream.write(json.dumps(event.as_dict()) + "\n")
        self._stream.flush()   # a tail-ing consumer needs each line immediately

    def close(self) -> None:
        if self._owns:
            self._stream.close()


class MultiReporter(Reporter):
    """Fan one run out to several reporters."""

    def __init__(self, *reporters: Reporter) -> None:
        self.reporters = [r for r in reporters if r is not None]

    def emit(self, event: ProgressEvent) -> None:
        for reporter in self.reporters:
            reporter.emit(event)

    def close(self) -> None:
        for reporter in self.reporters:
            reporter.close()


def build_reporter(progress_file: str | Path | None = None, quiet: bool = False) -> Reporter:
    """The reporter a run should use, from its settings.

    Console output stays on unless silenced: a headless run still wants a human
    account in the log. A machine stream is added when a path is given.
    """
    reporters: list[Reporter] = []
    if not quiet:
        reporters.append(ConsoleReporter())
    if progress_file:
        reporters.append(JsonReporter(progress_file))
    if not reporters:
        return Reporter()
    return reporters[0] if len(reporters) == 1 else MultiReporter(*reporters)
