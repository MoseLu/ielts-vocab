from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient


GATEWAY_PATH = Path(__file__).resolve().parents[2] / 'apps' / 'gateway-bff' / 'main.py'


def _load_gateway_module():
    spec = importlib.util.spec_from_file_location('gateway_bff_ready_main', GATEWAY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gateway_ready_reports_downstream_dependency_status(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    service_status = {
        'identity-service': True,
        'learning-core-service': True,
        'catalog-content-service': True,
        'ai-execution-service': False,
        'notes-service': True,
        'admin-ops-service': True,
        'tts-media-service': True,
        'asr-service': True,
    }
    module.app.state.readiness_checks = {
        name: (lambda value=value: value)
        for name, value in service_status.items()
    }

    response = client.get('/ready')

    assert response.status_code == 503
    assert response.json()['dependencies']['ai-execution-service'] is False
