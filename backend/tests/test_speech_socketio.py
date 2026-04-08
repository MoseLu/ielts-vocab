import threading

import pytest
import websocket

from routes import speech_socketio
from speech_service import app, socketio


def _namespace_sid(client):
    rooms = socketio.server.manager.rooms['/speech'][None]
    for sid, eio_sid in rooms.items():
        if eio_sid == client.eio_sid:
            return sid
    raise AssertionError('Socket.IO test client sid not found')


@pytest.fixture(autouse=True)
def clear_active_sessions():
    speech_socketio.active_sessions.clear()
    yield
    speech_socketio.active_sessions.clear()


def test_resolve_realtime_asr_model_falls_back_from_incompatible_model(monkeypatch):
    monkeypatch.setenv('REALTIME_ASR_MODEL', 'fun-asr-realtime-2025-09-15')

    assert (
        speech_socketio._resolve_realtime_asr_model()
        == speech_socketio.DEFAULT_REALTIME_ASR_MODEL
    )


def test_extract_partial_transcript_supports_string_stash():
    assert speech_socketio._extract_partial_transcript({
        'text': '',
        'stash': 'The widespread adoption',
    }) == 'The widespread adoption'


def test_stop_recognition_ignores_closed_connection_errors():
    class ClosedWebSocket:
        def close(self):
            return None

        def send(self, _payload):
            raise RuntimeError('Connection is already closed.')

    client = socketio.test_client(app, namespace='/speech')
    client.get_received('/speech')
    sid = _namespace_sid(client)
    speech_socketio.active_sessions[sid] = {
        'ws': ClosedWebSocket(),
        'ready': True,
        'closing': False,
        'enable_vad': True,
        'audio_queue': [],
        'lock': threading.Lock(),
    }

    client.emit('stop_recognition', namespace='/speech')

    received = client.get_received('/speech')
    names = [event['name'] for event in received]

    assert 'recognition_stopped' in names
    assert 'recognition_error' not in names
    assert speech_socketio.active_sessions[sid]['ready'] is False
    assert speech_socketio.active_sessions[sid]['closing'] is True

    client.disconnect(namespace='/speech')


def test_start_recognition_replaces_existing_session(monkeypatch):
    class ExistingWebSocket:
        def __init__(self):
            self.close_calls = 0

        def close(self):
            self.close_calls += 1

    class FakeWebSocketApp:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.close_calls = 0

        def close(self):
            self.close_calls += 1

        def run_forever(self):
            return None

    created_ws = []
    spawn_calls = []

    def fake_websocket_app(*args, **kwargs):
        ws = FakeWebSocketApp(*args, **kwargs)
        created_ws.append(ws)
        return ws

    monkeypatch.setattr(websocket, 'WebSocketApp', fake_websocket_app)
    monkeypatch.setattr(speech_socketio, 'spawn_background', lambda target: spawn_calls.append(target))
    monkeypatch.setattr(speech_socketio, 'API_KEY', 'test-key')

    client = socketio.test_client(app, namespace='/speech')
    client.get_received('/speech')
    sid = _namespace_sid(client)
    old_ws = ExistingWebSocket()
    speech_socketio.active_sessions[sid] = {
        'ws': old_ws,
        'ready': True,
        'closing': False,
        'enable_vad': True,
        'audio_queue': [b'old-audio'],
        'lock': threading.Lock(),
    }

    client.emit('start_recognition', {
        'language': 'en',
        'enable_vad': False,
    }, namespace='/speech')

    assert old_ws.close_calls == 1
    assert len(created_ws) == 1
    assert len(spawn_calls) == 1
    assert spawn_calls[0].__self__ is created_ws[0]
    assert speech_socketio.active_sessions[sid]['ws'] is created_ws[0]
    assert speech_socketio.active_sessions[sid]['enable_vad'] is False
    assert speech_socketio.active_sessions[sid]['audio_queue'] == []

    client.disconnect(namespace='/speech')
