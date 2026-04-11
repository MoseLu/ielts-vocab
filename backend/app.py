from services.runtime_async import patch_standard_library

patch_standard_library()

from runtime_paths import ensure_shared_package_paths


ensure_shared_package_paths()

from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
os.environ.setdefault('CURRENT_SERVICE_NAME', 'backend-monolith')

import sqlite3
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from werkzeug.middleware.proxy_fix import ProxyFix
from compat_runtime_guard import require_explicit_monolith_compat_runtime
from monolith_compat_runtime import configure_monolith_compat_runtime
from config import Config
from service_models.identity_models import db

# SQLite WAL mode
# Runs once per new connection. WAL allows concurrent reads during writes,
# which removes the read-write lock contention on a multi-user server.
# synchronous=NORMAL is safe with WAL and significantly faster than FULL.
@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_conn, _record):
    if isinstance(dbapi_conn, sqlite3.Connection):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()

migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if app.config.get('TRUST_PROXY_HEADERS'):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config.get('PROXY_FIX_X_FOR', 1),
            x_proto=app.config.get('PROXY_FIX_X_PROTO', 1),
        )

    # Initialize compatibility runtime shell around the archived monolith routes.
    CORS(app,
         resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}},
         supports_credentials=True)
    configure_monolith_compat_runtime(app, migrate=migrate)

    return app


app = None if os.environ.get('PYTEST_RUNNING') == '1' else create_app()

def _get_backend_host() -> str:
    return (os.environ.get('BACKEND_HOST') or '0.0.0.0').strip() or '0.0.0.0'


def _get_backend_port() -> int:
    raw_port = (os.environ.get('BACKEND_PORT') or '5000').strip()
    try:
        return int(raw_port)
    except ValueError:
        return 5000


def _get_waitress_threads() -> int:
    raw_threads = (os.environ.get('WAITRESS_THREADS') or '8').strip()
    try:
        return max(4, int(raw_threads))
    except ValueError:
        return 8


def _print_banner(host: str, port: int) -> None:
    print("=" * 50)
    print("IELTS Vocabulary Backend")
    print("=" * 50)
    print(f"Local access: http://127.0.0.1:{port}")
    if host not in {'127.0.0.1', 'localhost'}:
        print(f"Bind host: {host}")
    print()
    print("API Endpoints:")
    print("  POST /api/auth/register - Register new user")
    print("  POST /api/auth/login    - Login")
    print("  POST /api/auth/logout   - Logout")
    print("  GET  /api/auth/me       - Get current user")
    print("  GET  /api/progress      - Get all progress")
    print("  POST /api/progress      - Save progress")
    print("  GET  /api/progress/<day> - Get day progress")
    print("  GET  /api/vocabulary    - Get all vocabulary")
    print("  GET  /api/vocabulary/day/<day> - Get day vocabulary")
    print()
    print("Speech Service:")
    print("  Socket.IO /speech runs in backend/speech_service.py on port 5001")
    print("=" * 50)


def _print_compatibility_notice() -> None:
    print("[Compat] backend/app.py is a rollback and compatibility runtime.")
    print("         Preferred local backend path is start-project.ps1 -> gateway-bff (:8000).")


def _run_backend_server(flask_app: Flask, host: str, port: int) -> None:
    preferred_server = (os.environ.get('BACKEND_SERVER') or 'waitress').strip().lower()

    if preferred_server != 'flask':
        try:
            from waitress import serve
        except ImportError:
            print("[WARN] waitress is not installed. Falling back to the Flask development server.")
            print("       Run `pip install -r backend/requirements.txt` to enable the production HTTP server.")
        else:
            threads = _get_waitress_threads()
            print(f"[Runtime] HTTP server: waitress (threads={threads})")
            serve(flask_app, host=host, port=port, threads=threads)
            return

    print("[Runtime] HTTP server: flask development server")
    flask_app.run(debug=False, host=host, port=port, threaded=True)


if __name__ == '__main__':
    require_explicit_monolith_compat_runtime(
        runtime_label='backend/app.py',
        startup_hint='start-monolith-compat.ps1',
    )
    backend_host = _get_backend_host()
    backend_port = _get_backend_port()

    _print_banner(backend_host, backend_port)
    _print_compatibility_notice()
    _run_backend_server(app, backend_host, backend_port)
