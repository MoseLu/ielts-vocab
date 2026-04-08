"""
Standalone speech recognition service.

Runs the /speech Socket.IO namespace on a dedicated process so the main Flask
API on port 5000 cannot be stalled by long-lived audio sessions.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_socketio import SocketIO

from services.asr_service import get_active_session_count, register_socketio_events


env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)


PORT = int(os.environ.get('SPEECH_SERVICE_PORT', '5001'))
HOST = os.environ.get('SPEECH_SERVICE_HOST', '0.0.0.0')


def resolve_socketio_async_mode() -> str:
    """Prefer websocket-capable runtimes; fall back to threading."""
    if importlib.util.find_spec('gevent') and importlib.util.find_spec('geventwebsocket'):
        return 'gevent'
    if importlib.util.find_spec('eventlet'):
        return 'eventlet'
    return 'threading'


SOCKETIO_ASYNC_MODE = resolve_socketio_async_mode()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'speech-service-secret'

socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    async_mode=SOCKETIO_ASYNC_MODE,
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
        'service': 'speech',
        'port': PORT,
        'active_sessions': get_active_session_count(),
    }), 200


def print_banner():
    print("=" * 50)
    print("Speech Recognition Service")
    print("=" * 50)
    print(f"Server running at: http://localhost:{PORT}")
    print(f"Namespace: /speech")
    print(f"Async mode: {socketio.async_mode}")
    print("=" * 50)


def run_server():
    run_options = {
        'app': app,
        'host': HOST,
        'port': PORT,
        'debug': False,
    }
    if socketio.async_mode == 'threading':
        run_options['allow_unsafe_werkzeug'] = True

    socketio.run(
        **run_options,
    )


if __name__ == '__main__':
    print_banner()
    run_server()
