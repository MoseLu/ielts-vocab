import threading

import pytest
import websocket

from services import asr_service
from speech_service import app, resolve_socketio_async_mode, socketio


def _namespace_sid(client):
    rooms = socketio.server.manager.rooms['/speech'][None]
    for sid, eio_sid in rooms.items():
        if eio_sid == client.eio_sid:
            return sid
    raise AssertionError('Socket.IO test client sid not found')


@pytest.fixture(autouse=True)
def clear_active_sessions():
    asr_service.active_sessions.clear()
    yield
    asr_service.active_sessions.clear()


def test_resolve_realtime_asr_model_falls_back_from_incompatible_model(monkeypatch):
    monkeypatch.setenv('REALTIME_ASR_MODEL', 'fun-asr-realtime-2025-09-15')

    assert (
        asr_service._resolve_realtime_asr_model()
        == asr_service.DEFAULT_REALTIME_ASR_MODEL
    )


def test_resolve_file_asr_model_falls_back_from_incompatible_model(monkeypatch):
    monkeypatch.setenv('ASR_MODEL', 'paraformer-realtime-v2')

    assert (
        asr_service.resolve_file_asr_model()
        == asr_service.DEFAULT_FILE_ASR_MODEL
    )


def test_resolve_socketio_async_mode_prefers_websocket_capable_runtimes(monkeypatch):
    def fake_find_spec(name):
        if name in {'gevent', 'geventwebsocket'}:
            return object()
        return None

    monkeypatch.setattr(
        'platform_sdk.asr_runtime.socketio_service.importlib.util.find_spec',
        fake_find_spec,
    )

    assert resolve_socketio_async_mode() == 'gevent'


def test_extract_partial_transcript_supports_string_stash():
    assert asr_service._extract_partial_transcript({
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
    asr_service.active_sessions[sid] = {
        'ws': ClosedWebSocket(),
        'ready': True,
        'closing': False,
        'enable_vad': True,
        'recognition_id': 3,
        'bytes_since_commit': 0,
        'audio_queue': [],
        'partial_transcript': '',
        'final_transcript': '',
        'transcript_updated_at': None,
        'updated_at': None,
        'last_event': '',
        'lock': threading.Lock(),
    }

    client.emit('stop_recognition', namespace='/speech')

    received = client.get_received('/speech')
    names = [event['name'] for event in received]
    stopped_event = next(event for event in received if event['name'] == 'recognition_stopped')

    assert 'recognition_stopped' in names
    assert 'recognition_error' not in names
    assert stopped_event['args'][0]['recognition_id'] == 3
    assert asr_service.active_sessions[sid]['ready'] is False
    assert asr_service.active_sessions[sid]['closing'] is True

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
    monkeypatch.setattr(
        'platform_sdk.asr_runtime.realtime_socketio.spawn_background',
        lambda target: spawn_calls.append(target),
    )
    monkeypatch.setenv('DASHSCOPE_API_KEY', 'test-key')

    client = socketio.test_client(app, namespace='/speech')
    client.get_received('/speech')
    sid = _namespace_sid(client)
    old_ws = ExistingWebSocket()
    asr_service.active_sessions[sid] = {
        'ws': old_ws,
        'ready': True,
        'closing': False,
        'enable_vad': True,
        'recognition_id': 2,
        'bytes_since_commit': 0,
        'audio_queue': [b'old-audio'],
        'partial_transcript': '',
        'final_transcript': '',
        'transcript_updated_at': None,
        'updated_at': None,
        'last_event': '',
        'lock': threading.Lock(),
    }

    client.emit('start_recognition', {
        'language': 'en',
        'enable_vad': False,
        'recognition_id': 7,
    }, namespace='/speech')

    created_ws[0].kwargs['on_message'](
        created_ws[0],
        '{"type":"session.created","session":{"id":"dashscope-1"}}',
    )
    created_ws[0].kwargs['on_message'](
        created_ws[0],
        '{"type":"conversation.item.input_audio_transcription.text","text":"partial hello"}',
    )
    created_ws[0].kwargs['on_message'](
        created_ws[0],
        '{"type":"conversation.item.input_audio_transcription.completed","transcript":"final hello world"}',
    )
    started_event = next(
        event for event in client.get_received('/speech')
        if event['name'] == 'recognition_started'
    )

    assert old_ws.close_calls == 1
    assert len(created_ws) == 1
    assert len(spawn_calls) == 1
    assert spawn_calls[0].__self__ is created_ws[0]
    assert asr_service.active_sessions[sid]['ws'] is created_ws[0]
    assert asr_service.active_sessions[sid]['enable_vad'] is False
    assert asr_service.active_sessions[sid]['recognition_id'] == 7
    assert asr_service.active_sessions[sid]['audio_queue'] == []
    assert asr_service.active_sessions[sid]['partial_transcript'] == ''
    assert asr_service.active_sessions[sid]['final_transcript'] == 'final hello world'
    assert started_event['args'][0]['recognition_id'] == 7

    client.disconnect(namespace='/speech')
