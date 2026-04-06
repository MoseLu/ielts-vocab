def create_sqlite_backup(
    source_db: Path,
    backup_dir: Path,
    *,
    label: str = 'manual',
    keep: int = 10,
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
