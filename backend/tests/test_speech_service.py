from speech_service import app, socketio


def test_speech_service_health_endpoint():
    client = app.test_client()
    response = client.get('/health')

    assert response.status_code == 200
    assert response.get_json()['service'] == 'speech'


def test_speech_service_uses_threading_mode():
    assert socketio.async_mode == 'threading'
