from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa

from platform_sdk.wave5_projection_split_verification import (
    can_verify_split_runtime,
    collect_split_runtime_status,
)


def _create_db(path: Path, statements: list[str]) -> None:
    engine = sa.create_engine(f"sqlite:///{path.as_posix()}")
    try:
        with engine.begin() as connection:
            for statement in statements:
                connection.execute(sa.text(statement))
    finally:
        engine.dispose()


def _set_service_sqlite(monkeypatch, service_name: str, sqlite_path: Path) -> None:
    prefix = ''.join(char if char.isalnum() else '_' for char in service_name).strip('_').upper()
    monkeypatch.setenv(f'{prefix}_SQLITE_DB_PATH', str(sqlite_path))
    monkeypatch.delenv(f'{prefix}_DATABASE_URL', raising=False)
    monkeypatch.delenv(f'{prefix}_SQLALCHEMY_DATABASE_URI', raising=False)


def _clear_split_database_env(monkeypatch) -> None:
    for name in (
        'CURRENT_SERVICE_NAME',
        'SQLALCHEMY_DATABASE_URI',
        'DATABASE_URL',
        'SQLITE_DB_PATH',
        'POSTGRES_HOST',
        'POSTGRES_PORT',
        'POSTGRES_DB',
        'POSTGRES_DATABASE',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'POSTGRES_SSLMODE',
        'IDENTITY_SERVICE_DATABASE_URL',
        'IDENTITY_SERVICE_SQLALCHEMY_DATABASE_URI',
        'IDENTITY_SERVICE_SQLITE_DB_PATH',
        'LEARNING_CORE_SERVICE_DATABASE_URL',
        'LEARNING_CORE_SERVICE_SQLALCHEMY_DATABASE_URI',
        'LEARNING_CORE_SERVICE_SQLITE_DB_PATH',
        'AI_EXECUTION_SERVICE_DATABASE_URL',
        'AI_EXECUTION_SERVICE_SQLALCHEMY_DATABASE_URI',
        'AI_EXECUTION_SERVICE_SQLITE_DB_PATH',
        'NOTES_SERVICE_DATABASE_URL',
        'NOTES_SERVICE_SQLALCHEMY_DATABASE_URI',
        'NOTES_SERVICE_SQLITE_DB_PATH',
        'ADMIN_OPS_SERVICE_DATABASE_URL',
        'ADMIN_OPS_SERVICE_SQLALCHEMY_DATABASE_URI',
        'ADMIN_OPS_SERVICE_SQLITE_DB_PATH',
        'ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES',
        'ALLOW_SHARED_SPLIT_SERVICE_SQLITE',
    ):
        monkeypatch.delenv(name, raising=False)


def test_collect_split_runtime_status_uses_service_owned_databases(monkeypatch, tmp_path):
    _clear_split_database_env(monkeypatch)
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')

    identity_db = tmp_path / 'identity.sqlite'
    learning_db = tmp_path / 'learning.sqlite'
    admin_db = tmp_path / 'admin.sqlite'
    notes_db = tmp_path / 'notes.sqlite'
    ai_db = tmp_path / 'ai.sqlite'

    _create_db(
        identity_db,
        [
            'CREATE TABLE users (id INTEGER PRIMARY KEY)',
            'INSERT INTO users (id) VALUES (1)',
        ],
    )
    _create_db(
        learning_db,
        [
            'CREATE TABLE user_study_sessions (id INTEGER PRIMARY KEY)',
            'CREATE TABLE user_wrong_words (id INTEGER PRIMARY KEY)',
            'INSERT INTO user_study_sessions (id) VALUES (1), (2)',
            'INSERT INTO user_wrong_words (id) VALUES (1), (2), (3)',
        ],
    )
    _create_db(
        admin_db,
        [
            'CREATE TABLE admin_projected_users (id INTEGER PRIMARY KEY)',
            'CREATE TABLE admin_projected_study_sessions (id INTEGER PRIMARY KEY)',
            'CREATE TABLE admin_projected_wrong_words (id INTEGER PRIMARY KEY)',
            'CREATE TABLE admin_projection_cursors (projection_name TEXT PRIMARY KEY, last_topic TEXT, last_processed_at TEXT)',
            "INSERT INTO admin_projected_users (id) VALUES (1)",
            "INSERT INTO admin_projected_study_sessions (id) VALUES (1), (2)",
            "INSERT INTO admin_projected_wrong_words (id) VALUES (1), (2), (3)",
            "INSERT INTO admin_projection_cursors (projection_name, last_topic, last_processed_at) VALUES ('admin.user-directory.bootstrap', '__bootstrap__', '2026-04-22T04:00:00')",
            "INSERT INTO admin_projection_cursors (projection_name, last_topic, last_processed_at) VALUES ('admin.study-session-analytics.bootstrap', '__bootstrap__', '2026-04-22T04:00:00')",
            "INSERT INTO admin_projection_cursors (projection_name, last_topic, last_processed_at) VALUES ('admin.wrong-word-directory.bootstrap', '__bootstrap__', '2026-04-22T04:00:00')",
        ],
    )
    _create_db(
        notes_db,
        [
            'CREATE TABLE notes_projected_study_sessions (id INTEGER PRIMARY KEY)',
            'CREATE TABLE notes_projected_wrong_words (id INTEGER PRIMARY KEY)',
            'CREATE TABLE notes_projection_cursors (projection_name TEXT PRIMARY KEY, last_topic TEXT, last_processed_at TEXT)',
            'CREATE TABLE user_daily_summaries (id INTEGER PRIMARY KEY)',
            'INSERT INTO notes_projected_study_sessions (id) VALUES (1), (2)',
            'INSERT INTO notes_projected_wrong_words (id) VALUES (1), (2), (3)',
            'INSERT INTO user_daily_summaries (id) VALUES (1), (2), (3), (4)',
            "INSERT INTO notes_projection_cursors (projection_name, last_topic, last_processed_at) VALUES ('notes.study-session-context.bootstrap', '__bootstrap__', '2026-04-22T04:00:00')",
            "INSERT INTO notes_projection_cursors (projection_name, last_topic, last_processed_at) VALUES ('notes.wrong-word-context.bootstrap', '__bootstrap__', '2026-04-22T04:00:00')",
        ],
    )
    _create_db(
        ai_db,
        [
            'CREATE TABLE ai_projected_wrong_words (id INTEGER PRIMARY KEY)',
            'CREATE TABLE ai_projected_daily_summaries (id INTEGER PRIMARY KEY)',
            'CREATE TABLE ai_projection_cursors (projection_name TEXT PRIMARY KEY, last_topic TEXT, last_processed_at TEXT)',
            'INSERT INTO ai_projected_wrong_words (id) VALUES (1), (2), (3)',
            'INSERT INTO ai_projected_daily_summaries (id) VALUES (1), (2), (3), (4)',
            "INSERT INTO ai_projection_cursors (projection_name, last_topic, last_processed_at) VALUES ('ai.wrong-word-context.bootstrap', '__bootstrap__', '2026-04-22T04:00:00')",
            "INSERT INTO ai_projection_cursors (projection_name, last_topic, last_processed_at) VALUES ('ai.daily-summary-context.bootstrap', '__bootstrap__', '2026-04-22T04:00:00')",
        ],
    )

    _set_service_sqlite(monkeypatch, 'identity-service', identity_db)
    _set_service_sqlite(monkeypatch, 'learning-core-service', learning_db)
    _set_service_sqlite(monkeypatch, 'admin-ops-service', admin_db)
    _set_service_sqlite(monkeypatch, 'notes-service', notes_db)
    _set_service_sqlite(monkeypatch, 'ai-execution-service', ai_db)

    assert can_verify_split_runtime()

    result = collect_split_runtime_status()

    assert result['runtime'] == 'split'
    assert result['bootstrap_ran'] is False
    assert result['ok'] is True
    assert result['admin']['user_directory']['source_count'] == 1
    assert result['admin']['user_directory']['projected_count'] == 1
    assert result['notes']['study_sessions']['source_count'] == 2
    assert result['notes']['study_sessions']['projected_count'] == 2
    assert result['ai']['daily_summaries']['source_count'] == 4
    assert result['ai']['daily_summaries']['projected_count'] == 4
