from __future__ import annotations

import os
import secrets

from flask import Flask
from sqlalchemy import inspect, text

from monolith_compat_manifest import resolve_enabled_monolith_compat_route_groups
from platform_sdk.service_schema import bootstrap_monolith_schema
from routes.middleware import init_middleware
from service_models.identity_models import User, db
from services.db_backup import initialize_sqlite_backup_runtime
from services.word_catalog_schema_runtime import ensure_word_catalog_memory_note_column


def _ensure_quick_memory_context_columns() -> None:
    """Backfill newly added quick-memory context columns on existing SQLite files."""
    inspector = inspect(db.engine)
    try:
        columns = {column['name'] for column in inspector.get_columns('user_quick_memory_records')}
    except Exception:
        return

    statements: list[str] = []
    if 'book_id' not in columns:
        statements.append('ALTER TABLE user_quick_memory_records ADD COLUMN book_id VARCHAR(100)')
    if 'chapter_id' not in columns:
        statements.append('ALTER TABLE user_quick_memory_records ADD COLUMN chapter_id VARCHAR(100)')

    if not statements:
        return

    for statement in statements:
        db.session.execute(text(statement))

    db.session.execute(text(
        'CREATE INDEX IF NOT EXISTS ix_user_quick_memory_records_book_id '
        'ON user_quick_memory_records (book_id)'
    ))
    db.session.execute(text(
        'CREATE INDEX IF NOT EXISTS ix_user_quick_memory_records_chapter_id '
        'ON user_quick_memory_records (chapter_id)'
    ))
    db.session.commit()


def _ensure_wrong_word_dimension_state_column() -> None:
    """Backfill wrong-word per-dimension state column on existing SQLite files."""
    inspector = inspect(db.engine)
    try:
        columns = {column['name'] for column in inspector.get_columns('user_wrong_words')}
    except Exception:
        return

    if 'dimension_state' in columns:
        return

    db.session.execute(text('ALTER TABLE user_wrong_words ADD COLUMN dimension_state TEXT'))
    db.session.commit()


def _ensure_admin_user() -> None:
    """Create an admin user if not exists. Credentials must be set via environment variables."""
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_INITIAL_PASSWORD')

    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        if not admin_password:
            admin_password = secrets.token_urlsafe(24)
            print(
                f"[Admin] ADMIN_INITIAL_PASSWORD not set - generated random password.\n"
                f"         Save this NOW: ADMIN_USERNAME={admin_username} ADMIN_INITIAL_PASSWORD={admin_password}\n"
                f"         Or set env var and re-run: export ADMIN_INITIAL_PASSWORD=your_secure_password"
            )
        else:
            print('[Admin] Using password from ADMIN_INITIAL_PASSWORD env var.')
        admin = User(username=admin_username, email=None)
        admin.set_password(admin_password)
        admin.is_admin = True
        db.session.add(admin)
        db.session.commit()
        print(f"[Admin] User '{admin_username}' created.")
    elif not admin.is_admin:
        admin.is_admin = True
        db.session.commit()
        print(f"[Admin] Existing user '{admin_username}' updated to admin flag.")


def register_monolith_compat_blueprints(app: Flask) -> None:
    init_middleware(app)
    for group in resolve_enabled_monolith_compat_route_groups():
        if group.init_hook is not None:
            group.init_hook(app)
        app.register_blueprint(group.blueprint, url_prefix=group.url_prefix)


def configure_monolith_compat_runtime(app: Flask, *, migrate) -> None:
    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    register_monolith_compat_blueprints(app)

    with app.app_context():
        bootstrap_monolith_schema(bind=db.engine, metadata=db.metadata)
        _ensure_quick_memory_context_columns()
        _ensure_wrong_word_dimension_state_column()
        ensure_word_catalog_memory_note_column(engine=db.engine, session=db.session)
        _ensure_admin_user()

    if os.environ.get('PYTEST_RUNNING') != '1':
        initialize_sqlite_backup_runtime(app)
