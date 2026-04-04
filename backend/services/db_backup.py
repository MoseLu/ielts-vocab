from __future__ import annotations

import getpass
import hashlib
import json
import logging
import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from services.db_safety import ensure_sqlite_restore_allowed, resolve_sqlite_database_path


CRITICAL_TABLES = (
    'users',
    'user_progress',
    'user_book_progress',
    'user_chapter_progress',
    'user_chapter_mode_progress',
    'user_wrong_words',
    'user_conversation_history',
    'user_study_sessions',
    'user_learning_events',
    'user_memory',
    'user_quick_memory_records',
    'user_smart_word_stats',
    'user_learning_notes',
    'user_daily_summaries',
    'user_added_books',
    'custom_books',
    'custom_book_chapters',
    'custom_book_words',
)


def utc_now_naive() -> datetime:
    return datetime.utcnow()


def _actor_context() -> dict[str, Any]:
    try:
        actor_username = getpass.getuser()
    except Exception:
        actor_username = 'unknown'
    return {
        'actor_username': actor_username or 'unknown',
        'actor_pid': os.getpid(),
        'actor_cwd': str(Path.cwd()),
    }


def _emit_operation_log(
    logger: logging.Logger | None,
    level: int,
    event: str,
    **details: Any,
):
    audit_logger = logger or logging.getLogger(__name__)
    audit_logger.log(
        level,
        '%s | %s',
        event,
        json.dumps(details, ensure_ascii=False, sort_keys=True),
    )


def _sanitize_label(label: str) -> str:
    cleaned = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '-' for ch in (label or 'manual').strip())
    cleaned = cleaned.strip('-_')
    return cleaned or 'manual'


def _timestamp_slug(dt: datetime) -> str:
    return dt.strftime('%Y%m%d-%H%M%S-%f')


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _table_counts(conn: sqlite3.Connection, table_names: tuple[str, ...]) -> dict[str, int]:
    counts: dict[str, int] = {}
    available = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    for table_name in table_names:
        if table_name not in available:
            continue
        counts[table_name] = int(conn.execute(f'SELECT COUNT(*) FROM {table_name}').fetchone()[0])
    return counts


def _integrity_check(conn: sqlite3.Connection) -> str:
    row = conn.execute('PRAGMA integrity_check').fetchone()
    if not row:
        return 'unknown'
    return str(row[0])


def _artifact_paths(backup_dir: Path, db_stem: str, timestamp_slug: str, label: str) -> tuple[Path, Path]:
    base_name = f'{db_stem}-{timestamp_slug}-{label}.sqlite'
    db_path = backup_dir / base_name
    manifest_path = backup_dir / f'{base_name}.json'
    return db_path, manifest_path


def list_sqlite_backups(backup_dir: Path, db_stem: str) -> list[Path]:
    if not backup_dir.exists():
        return []
    backups = [
        path for path in backup_dir.glob(f'{db_stem}-*.sqlite')
        if path.is_file() and not path.name.startswith('.')
    ]
    backups.sort(key=lambda item: item.stat().st_mtime, reverse=True)
    return backups


def prune_sqlite_backups(backup_dir: Path, db_stem: str, keep: int, logger: logging.Logger | None = None) -> list[Path]:
    if keep <= 0:
        return []

    backups = list_sqlite_backups(backup_dir, db_stem)
    removed: list[Path] = []
    for stale in backups[keep:]:
        manifest_path = Path(f'{stale}.json')
        if stale.exists():
            stale.unlink()
            removed.append(stale)
        if manifest_path.exists():
            manifest_path.unlink()
        if logger:
            logger.info('Removed stale SQLite backup %s', stale)
    return removed


def create_sqlite_backup(
    source_db: Path,
    backup_dir: Path,
    *,
    label: str = 'manual',
    keep: int = 96,
    critical_tables: tuple[str, ...] = CRITICAL_TABLES,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    source_db = Path(source_db).resolve()
    if not source_db.exists():
        raise FileNotFoundError(f'SQLite database not found: {source_db}')

    backup_dir = Path(backup_dir).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)

    now = utc_now_naive()
    safe_label = _sanitize_label(label)
    timestamp_slug = _timestamp_slug(now)
    final_db_path, manifest_path = _artifact_paths(backup_dir, source_db.stem, timestamp_slug, safe_label)
    temp_db_path = final_db_path.with_name(f'.{final_db_path.name}.tmp')
    temp_manifest_path = manifest_path.with_name(f'.{manifest_path.name}.tmp')

    if temp_db_path.exists():
        temp_db_path.unlink()
    if temp_manifest_path.exists():
        temp_manifest_path.unlink()

    source_conn = sqlite3.connect(str(source_db), timeout=30)
    dest_conn = sqlite3.connect(str(temp_db_path), timeout=30)
    try:
        source_conn.execute('PRAGMA busy_timeout = 5000')
        try:
            source_conn.backup(dest_conn)
            dest_conn.commit()
            integrity = _integrity_check(dest_conn)
            if integrity.lower() != 'ok':
                raise RuntimeError(f'Backup integrity check failed: {integrity}')
            table_counts = _table_counts(dest_conn, critical_tables)
        finally:
            dest_conn.close()
    except Exception:
        if temp_db_path.exists():
            temp_db_path.unlink()
        if temp_manifest_path.exists():
            temp_manifest_path.unlink()
        raise
    finally:
        source_conn.close()

    temp_db_path.replace(final_db_path)

    manifest = {
        'backup_file': final_db_path.name,
        'backup_path': str(final_db_path),
        'created_at': now.isoformat(timespec='seconds') + 'Z',
        'label': safe_label,
        'source_database': str(source_db),
        'source_size_bytes': source_db.stat().st_size,
        'backup_size_bytes': final_db_path.stat().st_size,
        'sha256': _sha256_file(final_db_path),
        'integrity_check': 'ok',
        'critical_table_counts': table_counts,
        'audit_context': {
            **_actor_context(),
            'operation': 'backup',
            'label': safe_label,
        },
    }

    temp_manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding='utf-8',
    )
    temp_manifest_path.replace(manifest_path)

    prune_sqlite_backups(backup_dir, source_db.stem, keep, logger=logger)

    _emit_operation_log(
        logger,
        logging.INFO,
        'sqlite_backup_created',
        backup_path=str(final_db_path),
        source_database=str(source_db),
        sha256=manifest['sha256'],
        critical_table_counts=table_counts,
        **manifest['audit_context'],
    )
    return manifest


def restore_sqlite_backup(
    backup_file: Path,
    target_db: Path,
    *,
    pre_restore_backup_dir: Path | None = None,
    keep_pre_restore: int = 20,
    logger: logging.Logger | None = None,
) -> dict[str, Any]:
    backup_file = Path(backup_file).resolve()
    target_db = Path(target_db).resolve()

    if not backup_file.exists():
        raise FileNotFoundError(f'Backup file not found: {backup_file}')

    ensure_sqlite_restore_allowed(target_db)

    conn = sqlite3.connect(str(backup_file), timeout=30)
    try:
        integrity = _integrity_check(conn)
        if integrity.lower() != 'ok':
            raise RuntimeError(f'Cannot restore corrupt backup: {integrity}')
        table_counts = _table_counts(conn, CRITICAL_TABLES)
    finally:
        conn.close()

    pre_restore_manifest: dict[str, Any] | None = None
    if target_db.exists():
        restore_point_dir = Path(pre_restore_backup_dir or target_db.parent / 'restore_points').resolve()
        pre_restore_manifest = create_sqlite_backup(
            target_db,
            restore_point_dir,
            label='pre-restore',
            keep=keep_pre_restore,
            logger=logger,
        )

    target_db.parent.mkdir(parents=True, exist_ok=True)
    temp_restore = target_db.with_name(f'.{target_db.name}.restore.tmp')
    if temp_restore.exists():
        temp_restore.unlink()

    source_conn = sqlite3.connect(str(backup_file), timeout=30)
    dest_conn = sqlite3.connect(str(temp_restore), timeout=30)
    try:
        source_conn.execute('PRAGMA busy_timeout = 5000')
        try:
            source_conn.backup(dest_conn)
            dest_conn.commit()
            restored_integrity = _integrity_check(dest_conn)
            if restored_integrity.lower() != 'ok':
                raise RuntimeError(f'Restored database integrity check failed: {restored_integrity}')
        finally:
            dest_conn.close()
    except Exception:
        if temp_restore.exists():
            temp_restore.unlink()
        raise
    finally:
        source_conn.close()

    for suffix in ('-wal', '-shm', '-journal'):
        stale_sidecar = target_db.with_name(f'{target_db.name}{suffix}')
        if stale_sidecar.exists():
            stale_sidecar.unlink()

    temp_restore.replace(target_db)

    result = {
        'restored_backup': str(backup_file),
        'target_database': str(target_db),
        'restored_at': utc_now_naive().isoformat(timespec='seconds') + 'Z',
        'integrity_check': 'ok',
        'critical_table_counts': table_counts,
        'pre_restore_backup': pre_restore_manifest,
        'audit_context': {
            **_actor_context(),
            'operation': 'restore',
        },
    }
    _emit_operation_log(
        logger,
        logging.WARNING,
        'sqlite_backup_restored',
        backup_file=str(backup_file),
        target_database=str(target_db),
        pre_restore_backup=(
            pre_restore_manifest['backup_path']
            if pre_restore_manifest is not None
            else None
        ),
        critical_table_counts=table_counts,
        **result['audit_context'],
    )
    return result


@dataclass
class SQLiteBackupScheduler:
    source_db: Path
    backup_dir: Path
    interval_seconds: int
    keep: int
    logger: logging.Logger

    def __post_init__(self):
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def latest_backup(self) -> Path | None:
        backups = list_sqlite_backups(self.backup_dir, self.source_db.stem)
        return backups[0] if backups else None

    def create_backup_now(self, label: str = 'manual') -> dict[str, Any]:
        return create_sqlite_backup(
            self.source_db,
            self.backup_dir,
            label=label,
            keep=self.keep,
            logger=self.logger,
        )

    def maybe_create_startup_backup(self, min_age_seconds: int) -> dict[str, Any] | None:
        latest = self.latest_backup()
        if latest is not None and min_age_seconds > 0:
            age_seconds = max(0, int(utc_now_naive().timestamp() - latest.stat().st_mtime))
            if age_seconds < min_age_seconds:
                self.logger.info(
                    'Skipping startup SQLite backup because latest snapshot is only %s seconds old',
                    age_seconds,
                )
                return None
        return self.create_backup_now(label='startup')

    def start(self):
        if self.interval_seconds <= 0:
            self.logger.info('SQLite backup scheduler disabled because interval <= 0')
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run,
            name='sqlite-backup-scheduler',
            daemon=True,
        )
        self._thread.start()
        self.logger.info(
            'Started SQLite backup scheduler for %s every %s seconds',
            self.source_db,
            self.interval_seconds,
        )

    def stop(self):
        self._stop_event.set()

    def _run(self):
        while not self._stop_event.wait(self.interval_seconds):
            try:
                self.create_backup_now(label='auto')
            except Exception:
                self.logger.exception('SQLite backup scheduler failed to create snapshot')


def initialize_sqlite_backup_runtime(app) -> SQLiteBackupScheduler | None:
    existing = app.extensions.get('sqlite_backup_scheduler')
    if existing is not None:
        return existing

    if not app.config.get('DB_BACKUP_ENABLED', True):
        app.logger.info('SQLite backups are disabled by config')
        return None

    db_path = resolve_sqlite_database_path(app.config.get('SQLALCHEMY_DATABASE_URI'))
    if db_path is None:
        app.logger.info('SQLite backups skipped because SQLALCHEMY_DATABASE_URI is not a file-backed SQLite database')
        return None

    backup_dir = Path(app.config.get('DB_BACKUP_DIR') or (db_path.parent / 'backups')).resolve()
    scheduler = SQLiteBackupScheduler(
        source_db=db_path,
        backup_dir=backup_dir,
        interval_seconds=max(0, int(app.config.get('DB_BACKUP_INTERVAL_SECONDS', 900))),
        keep=max(1, int(app.config.get('DB_BACKUP_KEEP', 96))),
        logger=app.logger,
    )
    app.extensions['sqlite_backup_scheduler'] = scheduler

    if app.config.get('DB_BACKUP_ON_START', True):
        try:
            scheduler.maybe_create_startup_backup(
                max(0, int(app.config.get('DB_BACKUP_STARTUP_MIN_AGE_SECONDS', 300)))
            )
        except Exception:
            app.logger.exception('Failed to create startup SQLite backup')

    scheduler.start()
    return scheduler
