from __future__ import annotations

import platform_sdk.rabbitmq_runtime as rabbitmq_runtime



def _clear_rabbitmq_env(monkeypatch):
    for name in (
        'CURRENT_SERVICE_NAME',
        'RABBITMQ_URL',
        'RABBITMQ_HOST',
        'RABBITMQ_PORT',
        'RABBITMQ_USER',
        'RABBITMQ_PASSWORD',
        'RABBITMQ_VHOST',
        'RABBITMQ_SSL',
        'RABBITMQ_DOMAIN_EXCHANGE',
        'LEARNING_CORE_SERVICE_RABBITMQ_URL',
        'LEARNING_CORE_SERVICE_RABBITMQ_HOST',
        'LEARNING_CORE_SERVICE_RABBITMQ_PORT',
        'LEARNING_CORE_SERVICE_RABBITMQ_USER',
        'LEARNING_CORE_SERVICE_RABBITMQ_PASSWORD',
        'LEARNING_CORE_SERVICE_RABBITMQ_VHOST',
        'LEARNING_CORE_SERVICE_RABBITMQ_SSL',
    ):
        monkeypatch.delenv(name, raising=False)



def test_resolve_rabbitmq_url_prefers_service_specific_url(monkeypatch):
    _clear_rabbitmq_env(monkeypatch)
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'learning-core-service')
    monkeypatch.setenv('RABBITMQ_URL', 'amqp://guest:guest@127.0.0.1:5672/%2F')
    monkeypatch.setenv('LEARNING_CORE_SERVICE_RABBITMQ_URL', 'amqp://svc:secret@127.0.0.1:5679/%2F')

    assert rabbitmq_runtime.resolve_rabbitmq_url() == 'amqp://svc:secret@127.0.0.1:5679/%2F'



def test_resolve_rabbitmq_url_builds_from_parts(monkeypatch):
    _clear_rabbitmq_env(monkeypatch)
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'learning-core-service')
    monkeypatch.setenv('RABBITMQ_HOST', '127.0.0.1')
    monkeypatch.setenv('LEARNING_CORE_SERVICE_RABBITMQ_PORT', '5679')
    monkeypatch.setenv('LEARNING_CORE_SERVICE_RABBITMQ_USER', 'svc user')
    monkeypatch.setenv('LEARNING_CORE_SERVICE_RABBITMQ_PASSWORD', 'p@ss word')
    monkeypatch.setenv('LEARNING_CORE_SERVICE_RABBITMQ_VHOST', '/wave5')
    monkeypatch.setenv('LEARNING_CORE_SERVICE_RABBITMQ_SSL', 'true')

    assert rabbitmq_runtime.resolve_rabbitmq_url() == 'amqps://svc%20user:p%40ss%20word@127.0.0.1:5679/%2Fwave5'



def test_make_rabbitmq_readiness_check_is_noop_when_not_required(monkeypatch):
    _clear_rabbitmq_env(monkeypatch)

    check = rabbitmq_runtime.make_rabbitmq_readiness_check(require_config=False)

    assert check() is True



def test_make_rabbitmq_readiness_check_uses_blocking_connection(monkeypatch):
    captured: dict[str, object] = {}

    class FakeConnection:
        def close(self):
            captured['closed'] = True

    class FakeParameters:
        def __init__(self, url):
            self.url = url
            self.socket_timeout = None
            self.blocked_connection_timeout = None

    class FakePika:
        URLParameters = FakeParameters

        @staticmethod
        def BlockingConnection(parameters):
            captured['url'] = parameters.url
            captured['socket_timeout'] = parameters.socket_timeout
            captured['blocked_timeout'] = parameters.blocked_connection_timeout
            return FakeConnection()

    monkeypatch.setattr(rabbitmq_runtime, 'pika', FakePika)

    check = rabbitmq_runtime.make_rabbitmq_readiness_check(rabbitmq_url='amqp://guest:guest@127.0.0.1:5679/%2F', require_config=True)

    assert check() is True
    assert captured['url'] == 'amqp://guest:guest@127.0.0.1:5679/%2F'
    assert captured['socket_timeout'] == 1.5
    assert captured['blocked_timeout'] == 1.5
    assert captured['closed'] is True
