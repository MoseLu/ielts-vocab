import importlib
import threading


def test_runtime_async_defaults_to_threading(monkeypatch):
    monkeypatch.delenv('SOCKETIO_ASYNC_MODE', raising=False)

    runtime_async = importlib.import_module('services.runtime_async')
    runtime_async = importlib.reload(runtime_async)

    completed = threading.Event()

    def mark_done():
        completed.set()

    worker = runtime_async.spawn_background(mark_done)

    assert runtime_async.SOCKETIO_ASYNC_MODE == 'threading'
    assert isinstance(worker, threading.Thread)
    assert completed.wait(1.0)
