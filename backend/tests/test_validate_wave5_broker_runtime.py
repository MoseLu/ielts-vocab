from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'validate_wave5_broker_runtime.py'
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location('validate_wave5_broker_runtime', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakeRedisClient:
    def ping(self):
        return True


class _FakeRabbitConnection:
    def close(self):
        return None


def test_validate_wave5_broker_runtime_reports_ready_when_clients_connect(tmp_path, monkeypatch):
    module = _load_script_module()
    env_file = tmp_path / 'microservices.env'
    env_file.write_text(
        '\n'.join([
            'REDIS_HOST=127.0.0.1',
            'REDIS_PORT=6379',
            'RABBITMQ_HOST=127.0.0.1',
            'RABBITMQ_PORT=5672',
            'RABBITMQ_USER=guest',
            'RABBITMQ_PASSWORD=guest',
        ]),
        encoding='utf-8',
    )
    monkeypatch.setattr(module, 'build_redis_client', lambda service_name=None: _FakeRedisClient())
    monkeypatch.setattr(module, 'build_blocking_connection', lambda service_name=None: _FakeRabbitConnection())

    env_values = module.load_env_values(env_file)
    service_names = ['notes-service', 'ai-execution-service']
    results = [
        *module.validate_redis_runtime(service_names, env_values),
        *module.validate_rabbitmq_runtime(service_names, env_values),
    ]

    assert all(result.ready for result in results)
    assert {result.broker_kind for result in results} == {'redis', 'rabbitmq'}


def test_validate_wave5_broker_runtime_flags_missing_urls(tmp_path):
    module = _load_script_module()
    env_file = tmp_path / 'microservices.env'
    env_file.write_text('', encoding='utf-8')

    env_values = module.load_env_values(env_file)
    results = [
        *module.validate_redis_runtime(['notes-service'], env_values),
        *module.validate_rabbitmq_runtime(['notes-service'], env_values),
    ]

    assert results[0].ready is False
    assert results[0].error == 'redis url is not configured'
    assert results[1].ready is False
    assert results[1].error == 'rabbitmq url is not configured'


def test_load_env_values_keeps_microservices_env_entries(tmp_path):
    module = _load_script_module()
    env_file = tmp_path / 'microservices.env'
    env_file.write_text(
        '\n'.join([
            'REDIS_HOST=10.0.0.5',
            'RABBITMQ_VHOST=/ielts',
        ]),
        encoding='utf-8',
    )

    env_values = module.load_env_values(env_file)

    assert env_values['REDIS_HOST'] == '10.0.0.5'
    assert env_values['RABBITMQ_VHOST'] == '/ielts'
