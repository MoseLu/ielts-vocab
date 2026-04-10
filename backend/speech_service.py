from __future__ import annotations

from runtime_paths import ensure_shared_package_paths


ensure_shared_package_paths()

from platform_sdk.asr_runtime import (  # noqa: E402
    create_socketio_service,
    print_socketio_banner,
    resolve_socketio_async_mode,
    run_socketio_server,
)


app, socketio, HOST, PORT = create_socketio_service(
    service_name='speech',
    version='0.1.0',
)


def print_banner():
    print_socketio_banner(
        title='Speech Recognition Service',
        socketio=socketio,
        port=PORT,
    )


def run_server():
    run_socketio_server(
        app=app,
        socketio=socketio,
        host=HOST,
        port=PORT,
    )


if __name__ == '__main__':
    print_banner()
    run_server()
