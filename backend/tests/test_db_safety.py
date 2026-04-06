import sqlite3
from pathlib import Path

import pytest

from app import create_app
from models import db as _db
from services import db_safety
from services.db_backup import create_sqlite_backup, restore_sqlite_backup


def _create_sample_db(path: Path, *, username: str):
    conn = sqlite3.connect(path)
    conn.execute(
        '''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        '''
    )
    conn.execute(
        '''
        INSERT INTO users (email, username, password_hash)
        VALUES (?, ?, ?)
        ''',
        (f'{username}@example.com', username, 'hash'),
    )
    conn.commit()
    conn.close()


def _file_config(db_path: Path):
    class FileConfig:
        TESTING = False
        SECRET_KEY = 'test-secret'
        JWT_SECRET_KEY = 'test-jwt-secret'
        JWT_ACCESS_TOKEN_EXPIRES = 3600
        JWT_REFRESH_TOKEN_EXPIRES = 86400 * 30
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        ALLOW_DESTRUCTIVE_DB_OPERATIONS = False
        DB_BACKUP_ENABLED = False
        CORS_ORIGINS = ['http://localhost:3000']
        COOKIE_SECURE = False
        COOKIE_SAMESITE = 'Strict'
        COOKIE_HTTPONLY = True
        LOGIN_MAX_ATTEMPTS = 10
        LOGIN_LOCKOUT_MINUTES = 15
        TRUST_PROXY_HEADERS = True
        PROXY_FIX_X_FOR = 2
        PROXY_FIX_X_PROTO = 1

    return FileConfig


def test_drop_all_blocks_file_backed_sqlite_without_unlock(tmp_path, monkeypatch):
    monkeypatch.delenv(db_safety.DESTRUCTIVE_DB_UNLOCK_ENV_VAR, raising=False)
    db_path = (tmp_path / 'guarded.sqlite').resolve()
    app = create_app(_file_config(db_path))

    with app.app_context():
        with pytest.raises(RuntimeError, match='ALLOW_DESTRUCTIVE_DB_OPERATIONS=true'):
            _db.drop_all()


def test_drop_all_allows_file_backed_sqlite_with_unlock(tmp_path, monkeypatch):
    monkeypatch.setenv(db_safety.DESTRUCTIVE_DB_UNLOCK_ENV_VAR, 'true')
    db_path = (tmp_path / 'guarded.sqlite').resolve()
    app = create_app(_file_config(db_path))

    with app.app_context():
        _db.drop_all()

    conn = sqlite3.connect(db_path)
    try:
        users_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
    finally:
        conn.close()

    assert users_table is None


def test_restore_blocks_primary_database_without_unlock(tmp_path, monkeypatch):
    monkeypatch.delenv(db_safety.DESTRUCTIVE_DB_UNLOCK_ENV_VAR, raising=False)
    source_db = tmp_path / 'source.sqlite'
    target_db = tmp_path / 'target.sqlite'
    backup_dir = tmp_path / 'backups'

    _create_sample_db(source_db, username='luo')
    _create_sample_db(target_db, username='admin')
    manifest = create_sqlite_backup(source_db, backup_dir, label='restore-source', keep=5)

    monkeypatch.setattr(db_safety, 'primary_sqlite_database_path', lambda: target_db.resolve())

    with pytest.raises(RuntimeError, match='ALLOW_DESTRUCTIVE_DB_OPERATIONS=true'):
        restore_sqlite_backup(Path(manifest['backup_path']), target_db)

    conn = sqlite3.connect(target_db)
    try:
        usernames = {row[0] for row in conn.execute('SELECT username FROM users')}
    finally:
        conn.close()

    assert usernames == {'admin'}


def test_restore_allows_primary_database_with_unlock(tmp_path, monkeypatch):
    monkeypatch.setenv(db_safety.DESTRUCTIVE_DB_UNLOCK_ENV_VAR, 'true')
    source_db = tmp_path / 'source.sqlite'
    target_db = tmp_path / 'target.sqlite'
    backup_dir = tmp_path / 'backups'

    _create_sample_db(source_db, username='luo')
    _create_sample_db(target_db, username='admin')
    manifest = create_sqlite_backup(source_db, backup_dir, label='restore-source', keep=5)

    monkeypatch.setattr(db_safety, 'primary_sqlite_database_path', lambda: target_db.resolve())

    result = restore_sqlite_backup(Path(manifest['backup_path']), target_db)

    conn = sqlite3.connect(target_db)
    try:
        usernames = {row[0] for row in conn.execute('SELECT username FROM users')}
    finally:
        conn.close()

    assert usernames == {'luo'}
    assert result['integrity_check'] == 'ok'
