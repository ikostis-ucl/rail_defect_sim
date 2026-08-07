"""Progress is reported once and rendered for two audiences.

A headless VM and a browser must be able to follow the same run. They can only
be trusted to agree if they read the same events, which is what these pin —
along with cancellation leaving nothing behind that a later run would trust.
"""

import io
import json
import signal
from pathlib import Path

import pytest

from app.progress import (
    Cancelled,
    CancellationToken,
    ConsoleReporter,
    EventKind,
    JsonReporter,
    MultiReporter,
    Phase,
    ProgressEvent,
    Reporter,
    build_reporter,
    cancel_on_signal,
    clear_partial_output,
)


# ── Events ────────────────────────────────────────────────────────────────────

def test_fraction_is_none_without_a_total():
    assert ProgressEvent(EventKind.PROGRESS, Phase.RENDER, done=5).fraction is None


def test_fraction_reports_completion():
    e = ProgressEvent(EventKind.PROGRESS, Phase.RENDER, done=5, total=20)
    assert e.fraction == pytest.approx(0.25)


def test_fraction_never_exceeds_one():
    e = ProgressEvent(EventKind.PROGRESS, Phase.RENDER, done=30, total=20)
    assert e.fraction == 1.0


def test_event_serialises():
    payload = ProgressEvent(EventKind.PROGRESS, Phase.TRACK, done=1, total=4).as_dict()
    assert payload["event"] == "progress"
    assert payload["phase"] == "track"
    assert payload["fraction"] == 0.25
    json.dumps(payload)


# ── Console reporter ──────────────────────────────────────────────────────────

def test_console_prints_phase_boundaries():
    out = io.StringIO()
    r = ConsoleReporter(out)
    r.phase_start(Phase.TRACK, total=100)
    r.phase_end(Phase.TRACK)
    text = out.getvalue()
    assert "[track] start (100)" in text
    assert "[track] done" in text


def test_console_throttles_progress_lines():
    """A line per frame would bury the log; the point is a readable account."""
    out = io.StringIO()
    r = ConsoleReporter(out)
    r.phase_start(Phase.RENDER, total=1000)
    for i in range(1, 1001):
        r.progress(Phase.RENDER, done=i, total=1000)
    lines = [l for l in out.getvalue().splitlines() if "%" in l]
    assert 5 <= len(lines) <= 15      # ~one per 10 %, not 1000


def test_console_always_reports_completion():
    out = io.StringIO()
    r = ConsoleReporter(out)
    r.phase_start(Phase.RENDER, total=10)
    r.progress(Phase.RENDER, done=10, total=10)
    assert "100%" in out.getvalue()


def test_console_reports_the_outcome():
    for call, expected in (("done", "Finished"), ("cancelled", "Cancelled")):
        out = io.StringIO()
        getattr(ConsoleReporter(out), call)()
        assert expected in out.getvalue()


# ── JSON reporter ─────────────────────────────────────────────────────────────

def test_json_writes_one_object_per_line(tmp_path):
    path = tmp_path / "progress.jsonl"
    r = JsonReporter(path)
    r.phase_start(Phase.RENDER, total=3)
    r.progress(Phase.RENDER, done=1, total=3)
    r.done("finished")
    r.close()

    events = [json.loads(line) for line in path.read_text().splitlines()]
    assert [e["event"] for e in events] == ["phase_start", "progress", "done"]
    assert events[1]["fraction"] == pytest.approx(1 / 3, abs=1e-3)


def test_json_flushes_so_a_watcher_sees_lines_immediately(tmp_path):
    """A UI tailing the file must not wait for the process to exit."""
    path = tmp_path / "progress.jsonl"
    r = JsonReporter(path)
    r.phase_start(Phase.CACHE)
    assert path.read_text().strip() != ""     # readable before close()
    r.close()


# ── Both at once ──────────────────────────────────────────────────────────────

def test_multi_reporter_feeds_every_audience(tmp_path):
    console = io.StringIO()
    path = tmp_path / "p.jsonl"
    r = MultiReporter(ConsoleReporter(console), JsonReporter(path))
    r.phase_start(Phase.TRACK, total=2)
    r.close()
    assert "[track] start" in console.getvalue()
    assert json.loads(path.read_text().splitlines()[0])["phase"] == "track"


def test_build_reporter_console_only_by_default():
    assert isinstance(build_reporter(), ConsoleReporter)


def test_build_reporter_adds_json_when_a_path_is_given(tmp_path):
    r = build_reporter(tmp_path / "p.jsonl")
    assert isinstance(r, MultiReporter)
    r.close()


def test_quiet_with_a_file_is_json_only(tmp_path):
    r = build_reporter(tmp_path / "p.jsonl", quiet=True)
    assert isinstance(r, JsonReporter)
    r.close()


def test_quiet_with_no_file_reports_nothing():
    assert type(build_reporter(quiet=True)) is Reporter


# ── Cancellation ──────────────────────────────────────────────────────────────

def test_token_raises_only_once_requested():
    token = CancellationToken()
    token.check()             # no-op
    token.request()
    with pytest.raises(Cancelled):
        token.check()


def test_signal_requests_cancellation_without_killing_the_process():
    """A flag, not an exception from the handler: a signal can land anywhere."""
    token = CancellationToken()
    with cancel_on_signal(token):
        signal.raise_signal(signal.SIGINT)
        assert token.requested
        with pytest.raises(Cancelled):
            token.check()


def test_handlers_are_restored_afterwards():
    original = signal.getsignal(signal.SIGINT)
    with cancel_on_signal(CancellationToken()):
        pass
    assert signal.getsignal(signal.SIGINT) is original


def test_clear_partial_output_removes_the_run_directory(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "frame0001.png").write_text("x")
    (run / "frame0002.png").write_text("x")

    removed = clear_partial_output(run)

    assert len(removed) == 2
    assert not run.exists()


def test_clear_partial_output_is_safe_when_nothing_is_there(tmp_path):
    assert clear_partial_output(tmp_path / "never") == []


def test_restoring_a_non_python_handler_does_not_explode():
    """Blender installs a C-level handler, which getsignal reports as None.

    Passing None back to signal.signal is a TypeError, which crashed a real
    render at the end of an otherwise successful run.
    """
    token = CancellationToken()
    manager = cancel_on_signal(token)
    manager._previous = {signal.SIGINT: None}
    manager.__exit__(None, None, None)          # must not raise
    assert callable(signal.getsignal(signal.SIGINT)) or \
        signal.getsignal(signal.SIGINT) in (signal.SIG_DFL, signal.SIG_IGN)


def test_clear_partial_output_leaves_no_frames_for_a_later_run(tmp_path):
    """Why a run clears its output directory before starting.

    ffmpeg assembles a PNG sequence by numbered pattern. A killed run leaves
    frames behind, so without this a later, shorter run of the same name would
    have the dead run's frames spliced onto the end of its video.
    """
    run = tmp_path / "run"
    run.mkdir()
    for i in range(1, 63):
        (run / f"clip{i:04d}.png").write_text("x")

    clear_partial_output(run)

    assert not run.exists()
