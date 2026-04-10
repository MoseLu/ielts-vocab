from __future__ import annotations

import os
import re
from urllib.parse import quote

try:
    import pika
except ImportError:  # pragma: no cover - exercised through dependency install in runtime.
    pika = None


DEFAULT_RABBITMQ_HOST = '127.0.0.1'
DEFAULT_RABBITMQ_PORT = '5679'
DEFAULT_RABBITMQ_USER = 'guest'
DEFAULT_RABBITMQ_PASSWORD = 'guest'
DEFAULT_RABBITMQ_VHOST = '/'
DEFAULT_DOMAIN_EXCHANGE = 'ielts-vocab.domain'



def _service_env_prefix(service_name: str | None = None) -> str:
    raw_name = (service_name or os.environ.get('CURRENT_SERVICE_NAME') or '').strip()
    if not raw_name:
        return ''
    return re.sub(r'[^A-Za-z0-9]+', '_', raw_name).strip('_').upper()



def _getenv(name: str, default: str = '', *, service_name: str | None = None) -> str:
    service_prefix = _service_env_prefix(service_name)
    if service_prefix:
        service_value = (os.environ.get(f'{service_prefix}_{name}') or '').strip()
        if service_value:
            return service_value
    return (os.environ.get(name) or default).strip()



def resolve_rabbitmq_url(*, service_name: str | None = None) -> str:
    explicit_url = _getenv('RABBITMQ_URL', service_name=service_name)
    if explicit_url:
        return explicit_url

    host = _getenv('RABBITMQ_HOST', service_name=service_name)
    if not host:
        return ''

    port = _getenv('RABBITMQ_PORT', DEFAULT_RABBITMQ_PORT, service_name=service_name) or DEFAULT_RABBITMQ_PORT
    user = _getenv('RABBITMQ_USER', DEFAULT_RABBITMQ_USER, service_name=service_name) or DEFAULT_RABBITMQ_USER
    password = _getenv('RABBITMQ_PASSWORD', DEFAULT_RABBITMQ_PASSWORD, service_name=service_name) or DEFAULT_RABBITMQ_PASSWORD
    vhost = _getenv('RABBITMQ_VHOST', DEFAULT_RABBITMQ_VHOST, service_name=service_name) or DEFAULT_RABBITMQ_VHOST
    ssl_enabled = _getenv('RABBITMQ_SSL', 'false', service_name=service_name).lower() in {
        '1',
        'true',
        'yes',
        'on',
    }
    scheme = 'amqps' if ssl_enabled else 'amqp'
    auth = f'{quote(user, safe="")}:{quote(password, safe="")}@'
    vhost_path = quote(vhost, safe='')
    return f'{scheme}://{auth}{host}:{port}/{vhost_path}'



def resolve_domain_exchange_name(*, service_name: str | None = None) -> str:
    return _getenv('RABBITMQ_DOMAIN_EXCHANGE', DEFAULT_DOMAIN_EXCHANGE, service_name=service_name)



def rabbitmq_is_configured(*, service_name: str | None = None) -> bool:
    return bool(resolve_rabbitmq_url(service_name=service_name))



def build_blocking_connection(*, service_name: str | None = None, rabbitmq_url: str | None = None):
    if pika is None:
        raise RuntimeError('pika package is not installed')

    resolved_url = (rabbitmq_url or resolve_rabbitmq_url(service_name=service_name)).strip()
    if not resolved_url:
        raise ValueError('RabbitMQ URL is not configured')

    parameters = pika.URLParameters(resolved_url)
    parameters.socket_timeout = 1.5
    parameters.blocked_connection_timeout = 1.5
    return pika.BlockingConnection(parameters)



def make_rabbitmq_readiness_check(*, service_name: str | None = None, rabbitmq_url: str | None = None, require_config: bool = False):
    def check() -> bool:
        resolved_url = (rabbitmq_url or resolve_rabbitmq_url(service_name=service_name)).strip()
        if not resolved_url:
            return not require_config

        try:
            connection = build_blocking_connection(service_name=service_name, rabbitmq_url=resolved_url)
        except Exception:
            return False

        try:
            connection.close()
            return True
        except Exception:
            return False

    return check
