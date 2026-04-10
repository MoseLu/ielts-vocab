from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager
from typing import Any, Callable, Iterator


DEFAULT_SOCKETIO_ASYNC_MODE = 'threading'
SUPPORTED_SOCKETIO_ASYNC_MODES = {'threading', 'eventlet'}


def _normalize_socketio_async_mode(raw_value: str | None) -> str:
    normalized = (raw_value or DEFAULT_SOCKETIO_ASYNC_MODE).strip().lower()
    if normalized in SUPPORTED_SOCKETIO_ASYNC_MODES:
        return normalized
    return DEFAULT_SOCKETIO_ASYNC_MODE


SOCKETIO_ASYNC_MODE = _normalize_socketio_async_mode(os.environ.get('SOCKETIO_ASYNC_MODE'))


def patch_standard_library() -> None:
    if SOCKETIO_ASYNC_MODE != 'eventlet':
        return

    import eventlet

    eventlet.monkey_patch()


def spawn_background(
    target: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
):
    if SOCKETIO_ASYNC_MODE == 'eventlet':
        import eventlet

        return eventlet.spawn(target, *args, **kwargs)

    thread = threading.Thread(
        target=target,
        args=args,
        kwargs=kwargs,
        daemon=True,
        name=f'bg-{getattr(target, "__name__", "task")}',
    )
    thread.start()
    return thread


def sleep(seconds: float) -> None:
    if SOCKETIO_ASYNC_MODE == 'eventlet':
        import eventlet

        eventlet.sleep(seconds)
        return

    time.sleep(seconds)


@contextmanager
def maybe_timeout(seconds: float, error: BaseException) -> Iterator[None]:
    if SOCKETIO_ASYNC_MODE == 'eventlet':
        import eventlet

        with eventlet.Timeout(seconds, error):
            yield
        return

    yield
