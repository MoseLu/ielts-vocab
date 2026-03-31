import eventlet
eventlet.monkey_patch()

from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

import sqlite3
import secrets
from sqlalchemy import event
from sqlalchemy.engine import Engine
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from flask_migrate import Migrate
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from models import db
from routes.auth import auth_bp, init_auth
from routes.progress import progress_bp
from routes.vocabulary import vocabulary_bp
from routes.speech import speech_bp
from routes.books import books_bp, init_books
from routes.speech_socketio import register_socketio_events
from routes.ai import ai_bp
from routes.admin import admin_bp, init_admin
from routes.notes import notes_bp
from routes.tts import tts_bp
from routes.middleware import init_middleware

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


def _ensure_admin_user():
    """Create an admin user if not exists. Credentials must be set via environment variables."""
    import os
    from models import User

    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_INITIAL_PASSWORD')

    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        # Generate a secure random password if none was provided. Startup is no longer blocked.
        if not admin_password:
            admin_password = secrets.token_urlsafe(24)
            print(
                f"[Admin] ADMIN_INITIAL_PASSWORD not set - generated random password.\n"
                f"         Save this NOW: ADMIN_USERNAME={admin_username} ADMIN_INITIAL_PASSWORD={admin_password}\n"
                f"         Or set env var and re-run: export ADMIN_INITIAL_PASSWORD=your_secure_password"
            )
        else:
            print(f"[Admin] Using password from ADMIN_INITIAL_PASSWORD env var.")
        admin = User(username=admin_username, email=None)
        admin.set_password(admin_password)
        admin.is_admin = True
        db.session.add(admin)
        db.session.commit()
        print(f"[Admin] User '{admin_username}' created.")
    else:
        if not admin.is_admin:
            admin.is_admin = True
            db.session.commit()
            print(f"[Admin] Existing user '{admin_username}' updated to admin flag.")


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if app.config.get('TRUST_PROXY_HEADERS'):
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=app.config.get('PROXY_FIX_X_FOR', 1),
            x_proto=app.config.get('PROXY_FIX_X_PROTO', 1),
        )

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    CORS(app,
         resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}},
         supports_credentials=True)

    # Initialize auth + shared middleware with app reference
    init_auth(app)
    init_middleware(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(progress_bp, url_prefix='/api/progress')
    app.register_blueprint(vocabulary_bp, url_prefix='/api/vocabulary')
    app.register_blueprint(speech_bp, url_prefix='/api/speech')
    app.register_blueprint(books_bp, url_prefix='/api/books')
    init_books(app)
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(notes_bp, url_prefix='/api/notes')
    app.register_blueprint(tts_bp, url_prefix='/api/tts')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    init_admin(app)

    # Create database tables and ensure admin user.
    # db.create_all() is idempotent and safe to call on every startup.
    # For schema changes going forward, use Flask-Migrate:
    #   flask db migrate -m "description"
    #   flask db upgrade
    with app.app_context():
        db.create_all()
        _ensure_admin_user()

    return app


# Create app instance
app = create_app()

# Initialize SocketIO with eventlet for better WebSocket support
socketio = SocketIO(
    app,
    cors_allowed_origins=app.config['CORS_ORIGINS'],
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=25,
    logger=app.config.get('DEBUG', False),
    engineio_logger=app.config.get('DEBUG', False),
)

# Register Socket.IO events for speech recognition
register_socketio_events(socketio)


if __name__ == '__main__':
    print("=" * 50)
    print("IELTS Vocabulary Backend")
    print("=" * 50)
    print("Server running at: http://localhost:5000")
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
    print("WebSocket Endpoints:")
    print("  /speech - Real-time speech recognition")
    print("=" * 50)

    socketio.run(app, debug=False, host='0.0.0.0', port=5000)
