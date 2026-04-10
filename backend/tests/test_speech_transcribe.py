import io

from routes import speech


def test_transcribe_returns_recognized_text(client, monkeypatch):
    monkeypatch.setattr(speech, 'transcribe_uploaded_audio', lambda audio_file: 'hello world')

    response = client.post(
        '/api/speech/transcribe',
        data={'audio': (io.BytesIO(b'RIFFtest'), 'sample.wav')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 200
    assert response.get_json() == {'text': 'hello world'}


def test_transcribe_returns_legacy_service_error_payload(client, monkeypatch):
    def raise_error(audio_file):
        raise speech.ASRServiceError('API密钥未配置', status_code=500)

    monkeypatch.setattr(speech, 'transcribe_uploaded_audio', raise_error)

    response = client.post(
        '/api/speech/transcribe',
        data={'audio': (io.BytesIO(b'RIFFtest'), 'sample.wav')},
        content_type='multipart/form-data',
    )

    assert response.status_code == 500
    assert response.get_json() == {'error': '识别失败: API密钥未配置'}
