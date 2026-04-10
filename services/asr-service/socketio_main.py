from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from platform_sdk.runtime_env import load_split_service_env
from platform_sdk.asr_runtime import (
    create_socketio_service,
    print_socketio_banner,
    run_socketio_server,
)

load_split_service_env(service_name='asr-service')


app, socketio, HOST, PORT = create_socketio_service(
    service_name='asr-service',
    version='0.1.0',
)


def print_banner() -> None:
    print_socketio_banner(
        title='ASR Realtime Service',
        socketio=socketio,
        port=PORT,
    )


def run_server() -> None:
    run_socketio_server(
        app=app,
        socketio=socketio,
        host=HOST,
        port=PORT,
    )


if __name__ == '__main__':
    print_banner()
    run_server()
