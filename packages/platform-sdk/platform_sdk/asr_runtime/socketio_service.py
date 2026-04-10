from __future__ import annotations

import importlib.util
import os

from flask import Flask, jsonify
from flask_socketio import SocketIO

from .base import SOCKET_NAMESPACE, get_dashscope_api_key
from .realtime_sessions import get_active_session_count
from .realtime_socketio import register_socketio_events


def resolve_socketio_async_mode() -> str:
    if importlib.util.find_spec('gevent') and importlib.util.find_spec('geventwebsocket'):
        return 'gevent'
    if importlib.util.find_spec('eventlet'):
        return 'eventlet'
    return 'threading'


def create_socketio_service(
    *,
    service_name: str,
    version: str,
    host_env: str = 'SPEECH_SERVICE_HOST',
    port_env: str = 'SPEECH_SERVICE_PORT',
) -> tuple[Flask, SocketIO, str, int]:
    host = os.environ.get(host_env, '0.0.0.0')
    port = int(os.environ.get(port_env, '5001'))
    async_mode = resolve_socketio_async_mode()

    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'speech-service-secret'

    socketio = SocketIO(
        app,
        cors_allowed_origins='*',
        async_mode=async_mode,
        ping_timeout=60,
        ping_interval=25,
        logger=False,
        engineio_logger=False,
    )
    register_socketio_events(socketio)

    @app.get('/health')
    def health_check():
        return jsonify({
            'status': 'ok',
            'service': service_name,
            'version': version,
            'port': port,
            'namespace': SOCKET_NAMESPACE,
            'transport': 'socketio',
            'active_sessions': get_active_session_count(),
        }), 200

    @app.get('/ready')
    def ready_check():
        api_configured = bool(get_dashscope_api_key())
        payload = {
            'status': 'ready' if api_configured else 'not_ready',
            'service': service_name,
            'version': version,
            'dependencies': {
                'dashscope_api_key': api_configured,
            },
        }
        status_code = 200 if api_configured else 503
        return jsonify(payload), status_code

    @app.get('/version')
    def version_check():
        return jsonify({
            'service': service_name,
            'version': version,
            'transport': 'socketio',
        }), 200

    return app, socketio, host, port


def print_socketio_banner(*, title: str, socketio: SocketIO, port: int) -> None:
    print('=' * 50)
    print(title)
    print('=' * 50)
    print(f'Server running at: http://localhost:{port}')
    print(f'Namespace: {SOCKET_NAMESPACE}')
    print(f'Async mode: {socketio.async_mode}')
    print('=' * 50)


def run_socketio_server(*, app: Flask, socketio: SocketIO, host: str, port: int) -> None:
    run_options = {
        'app': app,
        'host': host,
        'port': port,
        'debug': False,
    }
    if socketio.async_mode == 'threading':
        run_options['allow_unsafe_werkzeug'] = True

    socketio.run(**run_options)
