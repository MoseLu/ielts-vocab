from speech_service import app, resolve_socketio_async_mode, socketio


def test_speech_service_health_endpoint():
    client = app.test_client()
    response = client.get('/health')

    assert response.status_code == 200
    assert response.get_json()['service'] == 'speech'
    assert response.get_json()['namespace'] == '/speech'


def test_speech_service_uses_resolved_async_mode():
    assert socketio.async_mode == resolve_socketio_async_mode()


def test_speech_service_exposes_internal_session_snapshot(monkeypatch):
    client = app.test_client()

    monkeypatch.setattr(
        'platform_sdk.asr_runtime.socketio_service.get_live_session_snapshot',
        lambda session_id: {
            'ready': False,
            'closing': True,
            'enable_vad': False,
            'recognition_id': 9,
            'has_ws': False,
            'queue_length': 0,
            'bytes_since_commit': 0,
            'updated_at': 456,
            'last_event': 'session.finished',
            'partial_transcript': '',
            'final_transcript': 'compat transcript',
            'transcript_updated_at': 455,
        } if session_id == 'speech-compat' else None,
    )

    response = client.get('/internal/sessions/speech-compat')

    assert response.status_code == 200
    assert response.get_json()['snapshot']['final_transcript'] == 'compat transcript'
