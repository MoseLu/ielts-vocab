import json
import sqlite3
import time
from pathlib import Path

from flask import Flask

from services.db_backup import (
    create_sqlite_backup,
    initialize_sqlite_backup_runtime,
    list_sqlite_backups,
    resolve_sqlite_database_path,
    restore_sqlite_backup,
)


def _create_sample_db(path: Path, *, username: str = 'alice', extra_username: str | None = None):
    conn = sqlite3.connect(path)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute(
        '''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            avatar_url TEXT,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT,
            tokens_revoked_before TEXT
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE user_study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mode TEXT,
            book_id TEXT,
            chapter_id TEXT,
            words_studied INTEGER DEFAULT 0,
            correct_count INTEGER DEFAULT 0,
            wrong_count INTEGER DEFAULT 0,
            duration_seconds INTEGER DEFAULT 0,
            started_at TEXT,
            ended_at TEXT
        )
        '''
    )
    conn.execute(
        '''
        CREATE TABLE user_quick_memory_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            book_id TEXT,
            chapter_id TEXT,
            status TEXT NOT NULL,
            first_seen INTEGER DEFAULT 0,
            last_seen INTEGER DEFAULT 0,
            known_count INTEGER DEFAULT 0,
            unknown_count INTEGER DEFAULT 0,
            next_review INTEGER DEFAULT 0,
            fuzzy_count INTEGER DEFAULT 0
        )
        '''
    )
    conn.execute(
        '''
        INSERT INTO users (email, username, password_hash, avatar_url, is_admin, created_at, tokens_revoked_before)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        (f'{username}@example.com', username, 'hash', None, 0, '2026-04-04 10:00:00', None),
    )
    user_id = conn.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()[0]
    conn.execute(
        '''
        INSERT INTO user_study_sessions
        (user_id, mode, book_id, chapter_id, words_studied, correct_count, wrong_count, duration_seconds, started_at, ended_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (user_id, 'quickmemory', 'book-a', '1', 5, 4, 1, 42, '2026-04-04 10:01:00', '2026-04-04 10:01:42'),
    )
    conn.execute(
        '''
        INSERT INTO user_quick_memory_records
        (user_id, word, book_id, chapter_id, status, first_seen, last_seen, known_count, unknown_count, next_review, fuzzy_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (user_id, 'kind', 'book-a', '1', 'known', 1, 2, 2, 0, 3, 0),
    )

    if extra_username:
        conn.execute(
            '''
            INSERT INTO users (email, username, password_hash, avatar_url, is_admin, created_at, tokens_revoked_before)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (f'{extra_username}@example.com', extra_username, 'hash', None, 0, '2026-04-04 10:02:00', None),
        )

    conn.commit()
    conn.close()


def test_resolve_sqlite_database_path_handles_file_backed_uris(tmp_path):
    db_path = (tmp_path / 'database.sqlite').resolve()
    uri = f'sqlite:///{db_path}'
    assert resolve_sqlite_database_path(uri) == db_path


def test_create_sqlite_backup_creates_consistent_snapshot_and_manifest(tmp_path):
    db_path = tmp_path / 'source.sqlite'
    backup_dir = tmp_path / 'backups'
    _create_sample_db(db_path)

    manifest = create_sqlite_backup(db_path, backup_dir, label='manual', keep=5)

    backup_file = Path(manifest['backup_path'])
    manifest_file = Path(f"{backup_file}.json")
    assert backup_file.exists()
    assert manifest_file.exists()
    assert manifest['integrity_check'] == 'ok'
    assert manifest['critical_table_counts']['users'] == 1
    assert manifest['critical_table_counts']['user_study_sessions'] == 1
    assert manifest['critical_table_counts']['user_quick_memory_records'] == 1
    assert manifest['audit_context']['operation'] == 'backup'
    assert manifest['audit_context']['label'] == 'manual'
    assert manifest['audit_context']['actor_pid'] > 0

    payload = json.loads(manifest_file.read_text(encoding='utf-8'))
    assert payload['sha256'] == manifest['sha256']
    assert payload['audit_context']['operation'] == 'backup'

    conn = sqlite3.connect(backup_file)
    assert conn.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 1
    assert conn.execute("SELECT username FROM users").fetchone()[0] == 'alice'
    conn.close()


def test_create_sqlite_backup_enforces_retention(tmp_path):
    db_path = tmp_path / 'source.sqlite'
    backup_dir = tmp_path / 'backups'
    _create_sample_db(db_path)

    for _ in range(3):
        create_sqlite_backup(db_path, backup_dir, label='auto', keep=2)
        time.sleep(0.01)

    backups = list_sqlite_backups(backup_dir, db_path.stem)
    assert len(backups) == 2
    for backup_file in backups:
        assert Path(f'{backup_file}.json').exists()


def test_restore_sqlite_backup_restores_target_and_creates_restore_point(tmp_path):
    source_db = tmp_path / 'source.sqlite'
    target_db = tmp_path / 'target.sqlite'
    backup_dir = tmp_path / 'backups'
    restore_points = tmp_path / 'restore-points'

    _create_sample_db(source_db, username='luo')
    _create_sample_db(target_db, username='admin', extra_username='old-user')

    manifest = create_sqlite_backup(source_db, backup_dir, label='restore-source', keep=5)
    result = restore_sqlite_backup(
        Path(manifest['backup_path']),
        target_db,
        pre_restore_backup_dir=restore_points,
        keep_pre_restore=5,
    )

    conn = sqlite3.connect(target_db)
    users = {row[0] for row in conn.execute('SELECT username FROM users')}
    conn.close()

    assert users == {'luo'}
    assert result['integrity_check'] == 'ok'
    assert result['pre_restore_backup'] is not None
    assert result['audit_context']['operation'] == 'restore'
    assert result['audit_context']['actor_pid'] > 0
    assert list_sqlite_backups(restore_points, target_db.stem)


def test_initialize_sqlite_backup_runtime_creates_startup_snapshot(tmp_path):
    db_path = tmp_path / 'runtime.sqlite'
    backup_dir = tmp_path / 'runtime-backups'
    _create_sample_db(db_path)

    app = Flask(__name__)
    app.config.update({
        'DB_BACKUP_ENABLED': True,
        'DB_BACKUP_DIR': str(backup_dir),
        'DB_BACKUP_INTERVAL_SECONDS': 0,
        'DB_BACKUP_KEEP': 3,
        'DB_BACKUP_ON_START': True,
        'DB_BACKUP_STARTUP_MIN_AGE_SECONDS': 0,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
    })

    scheduler = initialize_sqlite_backup_runtime(app)

    assert scheduler is not None
    backups = list_sqlite_backups(backup_dir, db_path.stem)
    assert len(backups) == 1


def test_backup_and_restore_emit_audit_logs(tmp_path, caplog):
    source_db = tmp_path / 'source.sqlite'
    target_db = tmp_path / 'target.sqlite'
    backup_dir = tmp_path / 'backups'
    restore_points = tmp_path / 'restore-points'
    _create_sample_db(source_db, username='luo')
    _create_sample_db(target_db, username='admin')

    caplog.set_level('INFO')
    manifest = create_sqlite_backup(
        source_db,
        backup_dir,
        label='audit-check',
    )
    restore_sqlite_backup(
        Path(manifest['backup_path']),
        target_db,
        pre_restore_backup_dir=restore_points,
        keep_pre_restore=5,
    )

    assert 'sqlite_backup_created |' in caplog.text
    assert '"label": "audit-check"' in caplog.text
    assert 'sqlite_backup_restored |' in caplog.text
    assert f'"target_database": {json.dumps(str(target_db))}' in caplog.text
