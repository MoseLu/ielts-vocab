import eventlet
eventlet.monkey_patch()

from dotenv import load_dotenv
import os
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
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
from routes.middleware import init_middleware


def _ensure_admin_user():
    """Create an admin user if not exists. Credentials must be set via environment variables."""
    import os
    from models import User

    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_INITIAL_PASSWORD')

    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        if not admin_password:
            raise ValueError(
                f"ADMIN_INITIAL_PASSWORD env var must be set on first run to create admin user '{admin_username}'. "
                "Example: export ADMIN_INITIAL_PASSWORD=your_secure_password"
            )
        admin = User(username=admin_username, email=None)
        admin.set_password(admin_password)
        admin.is_admin = True
        db.session.add(admin)
        db.session.commit()
        print(f"[Admin] User '{admin_username}' created. Password set from ADMIN_INITIAL_PASSWORD env var.")
    else:
        if not admin.is_admin:
            admin.is_admin = True
            db.session.commit()
            print(f"[Admin] Existing user '{admin_username}' updated to admin flag.")


def _migrate_db(app):
    """Apply incremental SQLite schema migrations."""
    from sqlalchemy import text
    with app.app_context():
        with db.engine.connect() as conn:
            # Migration 1: make users.email nullable and add unique username
            pragma = conn.execute(text("PRAGMA table_info(users)")).fetchall()
            col_names = [row[1] for row in pragma]
            email_col = next((row for row in pragma if row[1] == 'email'), None)
            has_username_unique = False

            # Check if email is NOT NULL (notnull flag == 1)
            if email_col and email_col[3] == 1:
                print("[Migration] Making users.email nullable...")
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS users_migrated (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email VARCHAR(255) UNIQUE,
                        username VARCHAR(100) NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        avatar_url TEXT,
                        is_admin BOOLEAN NOT NULL DEFAULT 0,
                        created_at DATETIME
                    )
                """))
                conn.execute(text("INSERT OR IGNORE INTO users_migrated SELECT id, NULLIF(email,''), username, password_hash, avatar_url, 0, created_at FROM users"))
                conn.execute(text("DROP TABLE users"))
                conn.execute(text("ALTER TABLE users_migrated RENAME TO users"))
                conn.commit()
                print("[Migration] Done.")

            # Migration 2: add is_admin column if missing
            if 'is_admin' not in col_names:
                print("[Migration] Adding is_admin column to users...")
                conn.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"))
                conn.commit()
                print("[Migration] is_admin column added.")

            # Migration 3: add per-dimension stat columns to user_wrong_words
            ww_pragma = conn.execute(text("PRAGMA table_info(user_wrong_words)")).fetchall()
            ww_cols = [row[1] for row in ww_pragma]
            dim_cols = [
                'listening_correct', 'listening_wrong',
                'meaning_correct',   'meaning_wrong',
                'dictation_correct', 'dictation_wrong',
            ]
            for col in dim_cols:
                if col not in ww_cols:
                    print(f"[Migration] Adding {col} to user_wrong_words...")
                    conn.execute(text(f"ALTER TABLE user_wrong_words ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0"))
            conn.commit()

            # Migration 4: add fuzzy_count to user_quick_memory_records
            qm_pragma = conn.execute(text("PRAGMA table_info(user_quick_memory_records)")).fetchall()
            qm_cols = [row[1] for row in qm_pragma]
            if qm_cols and 'fuzzy_count' not in qm_cols:
                print("[Migration] Adding fuzzy_count to user_quick_memory_records...")
                conn.execute(text("ALTER TABLE user_quick_memory_records ADD COLUMN fuzzy_count INTEGER NOT NULL DEFAULT 0"))
                conn.commit()
                print("[Migration] fuzzy_count column added.")

            # Migration 5: add tokens_revoked_before to users (for mass token revocation on theft)
            if 'tokens_revoked_before' not in col_names:
                print("[Migration] Adding tokens_revoked_before to users...")
                conn.execute(text("ALTER TABLE users ADD COLUMN tokens_revoked_before DATETIME"))
                conn.commit()
                print("[Migration] tokens_revoked_before column added.")

            # Migration 6: create user_learning_notes table if missing
            tables = [row[0] for row in conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()]
            if 'user_learning_notes' not in tables:
                print("[Migration] Creating user_learning_notes table...")
                conn.execute(text("""
                    CREATE TABLE user_learning_notes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        word_context VARCHAR(200),
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                conn.execute(text("CREATE INDEX ix_user_learning_notes_user_id ON user_learning_notes (user_id)"))
                conn.commit()
                print("[Migration] user_learning_notes table created.")

            # Migration 7: create user_daily_summaries table if missing
            if 'user_daily_summaries' not in tables:
                print("[Migration] Creating user_daily_summaries table...")
                conn.execute(text("""
                    CREATE TABLE user_daily_summaries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        date VARCHAR(10) NOT NULL,
                        content TEXT NOT NULL,
                        generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE (user_id, date)
                    )
                """))
                conn.execute(text("CREATE INDEX ix_user_daily_summaries_user_id ON user_daily_summaries (user_id)"))
                conn.commit()
                print("[Migration] user_daily_summaries table created.")


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
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
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    init_admin(app)

    # Create database tables then apply migrations and ensure admin user
    with app.app_context():
        db.create_all()
        _migrate_db(app)
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
