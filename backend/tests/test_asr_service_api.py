from __future__ import annotations

import importlib.util
import io
from pathlib import Path

from fastapi.testclient import TestClient


SERVICE_PATH = Path(__file__).resolve().parents[2] / 'services' / 'asr-service' / 'main.py'


def _load_asr_service_module():
    spec = importlib.util.spec_from_file_location('asr_service_main', SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_asr_service_ready_uses_dashscope_configuration(monkeypatch):
    monkeypatch.setenv('DASHSCOPE_API_KEY', 'test-key')

    module = _load_asr_service_module()
    client = TestClient(module.app)

    response = client.get('/ready')

    assert response.status_code == 200
    assert response.json() == {
        'status': 'ready',
        'service': 'asr-service',
        'version': '0.1.0',
        'dependencies': {'dashscope_api_key': True},
    }


def test_asr_service_transcribe_returns_text(monkeypatch):
    module = _load_asr_service_module()
    client = TestClient(module.app)

    monkeypatch.setattr(module, 'transcribe_uploaded_audio', lambda audio_file: 'hello world')

    response = client.post(
        '/v1/speech/transcribe',
        files={'audio': ('sample.wav', io.BytesIO(b'RIFFtest'), 'audio/wav')},
    )

    assert response.status_code == 200
    assert response.json() == {'text': 'hello world'}


def test_asr_service_transcribe_returns_legacy_error_payload(monkeypatch):
    module = _load_asr_service_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module,
        'transcribe_uploaded_audio',
        lambda audio_file: (_ for _ in ()).throw(module.ASRServiceError('API密钥未配置', status_code=500)),
    )

    response = client.post(
        '/v1/speech/transcribe',
        files={'audio': ('sample.wav', io.BytesIO(b'RIFFtest'), 'audio/wav')},
    )

    assert response.status_code == 500
    assert response.json() == {'error': '识别失败: API密钥未配置'}
