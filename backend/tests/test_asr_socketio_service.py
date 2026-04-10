from __future__ import annotations

import importlib.util
from pathlib import Path


SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'asr-service'
    / 'socketio_main.py'
)


def _load_asr_socketio_module():
    spec = importlib.util.spec_from_file_location('asr_socketio_main', SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_asr_socketio_service_health_endpoint():
    module = _load_asr_socketio_module()
    client = module.app.test_client()

    response = client.get('/health')

    assert response.status_code == 200
    assert response.get_json()['service'] == 'asr-service'
    assert response.get_json()['transport'] == 'socketio'


def test_asr_socketio_service_ready_uses_dashscope_configuration(monkeypatch):
    monkeypatch.setenv('DASHSCOPE_API_KEY', 'test-key')

    module = _load_asr_socketio_module()
    client = module.app.test_client()

    response = client.get('/ready')

    assert response.status_code == 200
    assert response.get_json() == {
        'status': 'ready',
        'service': 'asr-service',
        'version': '0.1.0',
        'dependencies': {'dashscope_api_key': True},
    }
