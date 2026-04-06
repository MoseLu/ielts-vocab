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
