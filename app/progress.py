from __future__ import annotations

import io
import os
import sys
from collections.abc import Iterable, Iterator
from contextlib import AbstractContextManager
from typing import TypeVar

T = TypeVar("T")

try:
    from tqdm import tqdm
except ModuleNotFoundError:  # pragma: no cover - optional dependency fallback
    tqdm = None


def progress_iter(
    iterable: Iterable[T],
    *,
    desc: str,
    total: int | None = None,
    unit: str = "item",
    leave: bool = False,
) -> Iterable[T] | Iterator[T]:
    """Wrap an iterable in a tqdm progress bar when tqdm is available."""
    if tqdm is None:
        return iterable

    return tqdm(
        iterable,
        desc=desc,
        total=total,
        unit=unit,
        dynamic_ncols=True,
        leave=leave,
    )


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


class BlenderRenderProgress(AbstractContextManager["BlenderRenderProgress"]):
    """Show a single tqdm bar for Blender animation renders."""

    def __init__(self, scene, *, desc: str = "Rendering frames...", leave: bool = False) -> None:
        self.scene = scene
        self.desc = desc
        self.leave = leave
        self.total = max(0, int(scene.frame_end) - int(scene.frame_start) + 1)
        self._progress_bar = None
        self._progress_stream = None
        self._should_close_stream = False
        self._silencer = _OutputSilencer()
        self._completed_frames: set[int] = set()
        self._handlers: list[tuple[list, object]] = []

    def __enter__(self) -> "BlenderRenderProgress":
        import bpy

        if tqdm is not None:
            self._progress_stream, self._should_close_stream = _open_progress_stream()
            self._progress_bar = tqdm(
                total=self.total,
                desc=self.desc,
                unit="frame",
                dynamic_ncols=True,
                leave=self.leave,
                file=self._progress_stream,
            )
        else:
            print(f"{self.desc}...")

        self._register_handler(bpy.app.handlers.render_init, self._on_render_init)
        self._register_handler(bpy.app.handlers.render_post, self._on_render_post)
        self._register_handler(bpy.app.handlers.render_complete, self._on_render_complete)
        self._register_handler(bpy.app.handlers.render_cancel, self._on_render_cancel)
        self._silencer.__enter__()
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self._silencer.__exit__(exc_type, exc, exc_tb)
        self._unregister_handlers()
        self._close_progress_bar()

    def _register_handler(self, handler_list: list, handler) -> None:
        handler_list.append(handler)
        self._handlers.append((handler_list, handler))

    def _unregister_handlers(self) -> None:
        for handler_list, handler in reversed(self._handlers):
            if handler in handler_list:
                handler_list.remove(handler)
        self._handlers.clear()

    def _on_render_init(self, scene, *_args) -> None:
        self._completed_frames.clear()
        if self._progress_bar is not None:
            self._progress_bar.n = 0
            self._progress_bar.refresh()

    def _on_render_post(self, scene, *_args) -> None:
        frame_number = int(scene.frame_current)
        if frame_number in self._completed_frames:
            return
        self._completed_frames.add(frame_number)
        if self._progress_bar is not None:
            self._progress_bar.update(1)

    def _on_render_complete(self, *_args) -> None:
        self._finish_progress_bar()

    def _on_render_cancel(self, *_args) -> None:
        self._finish_progress_bar()

    def _finish_progress_bar(self) -> None:
        if self._progress_bar is None:
            return
        remaining = self.total - self._progress_bar.n
        if remaining > 0:
            self._progress_bar.update(remaining)

    def _close_progress_bar(self) -> None:
        if self._progress_bar is not None:
            self._progress_bar.close()
            self._progress_bar = None
        if self._should_close_stream and self._progress_stream is not None:
            self._progress_stream.close()
        self._progress_stream = None
        self._should_close_stream = False


def render_progress(scene, *, desc: str = "Rendering frames...", leave: bool = False) -> BlenderRenderProgress:
    """Create a context manager that shows a single progress bar for animation rendering."""
    return BlenderRenderProgress(scene, desc=desc, leave=leave)


def _open_progress_stream():
    try:
        duplicated_fd = os.dup(sys.stderr.fileno())
    except (AttributeError, OSError, ValueError):
        return sys.stderr, False
    return os.fdopen(duplicated_fd, "w", buffering=1, encoding="utf-8", errors="replace"), True


