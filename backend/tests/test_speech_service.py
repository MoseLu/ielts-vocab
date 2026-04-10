from speech_service import app, resolve_socketio_async_mode, socketio


def test_speech_service_health_endpoint():
    client = app.test_client()
    response = client.get('/health')

    assert response.status_code == 200
    assert response.get_json()['service'] == 'speech'
    assert response.get_json()['namespace'] == '/speech'


def test_speech_service_uses_resolved_async_mode():
    assert socketio.async_mode == resolve_socketio_async_mode()
