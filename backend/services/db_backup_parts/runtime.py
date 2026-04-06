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
        keep=max(1, int(app.config.get('DB_BACKUP_KEEP', 10))),
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
