import argparse
import json
import logging
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from services.db_backup import restore_sqlite_backup


def _cli_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
    )
    return logging.getLogger('sqlite-restore-cli')


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            'Restore a SQLite database from a backup snapshot. '
            'Overwriting backend/database.sqlite requires ALLOW_DESTRUCTIVE_DB_OPERATIONS=true.'
        )
    )
    parser.add_argument('backup_file', help='Path to the backup .sqlite file to restore from')
    parser.add_argument('--target', default=str(BACKEND_DIR / 'database.sqlite'), help='Path to the live SQLite database file')
    parser.add_argument(
        '--pre-restore-dir',
        default=str(BACKEND_DIR / 'restore_points'),
        help='Directory where a safety snapshot of the current live DB is stored before overwrite',
    )
    parser.add_argument('--keep-pre-restore', type=int, default=20, help='How many restore-point snapshots to retain')
    return parser.parse_args()


def main():
    args = parse_args()
    logger = _cli_logger()
    print('Restoring a SQLite backup should be done with the backend process stopped.')
    result = restore_sqlite_backup(
        Path(args.backup_file),
        Path(args.target),
        pre_restore_backup_dir=Path(args.pre_restore_dir),
        keep_pre_restore=max(1, args.keep_pre_restore),
        logger=logger,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
