"""
Standalone speech recognition service.

Runs the /speech Socket.IO namespace on a dedicated process so the main Flask
API on port 5000 cannot be stalled by long-lived audio sessions.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_socketio import SocketIO

from routes.speech_socketio import active_sessions, register_socketio_events


env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)


PORT = int(os.environ.get('SPEECH_SERVICE_PORT', '5001'))
HOST = os.environ.get('SPEECH_SERVICE_HOST', '0.0.0.0')


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'speech-service-secret'

socketio = SocketIO(
    app,
    cors_allowed_origins='*',
    async_mode='threading',
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
        'active_sessions': len(active_sessions),
    }), 200


def print_banner():
    print("=" * 50)
    print("Speech Recognition Service")
    print("=" * 50)
    print(f"Server running at: http://localhost:{PORT}")
    print(f"Namespace: /speech")
    print("=" * 50)


def run_server():
    socketio.run(
        app,
        host=HOST,
        port=PORT,
        debug=False,
        allow_unsafe_werkzeug=True,
    )


if __name__ == '__main__':
    print_banner()
    run_server()
