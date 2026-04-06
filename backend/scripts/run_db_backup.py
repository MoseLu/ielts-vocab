import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(BACKEND_DIR / '.env')

from services.db_backup import create_sqlite_backup


def _cli_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
    )
    return logging.getLogger('sqlite-backup-cli')


def parse_args():
    parser = argparse.ArgumentParser(description='Create a consistent SQLite backup snapshot.')
    parser.add_argument('--database', default=str(BACKEND_DIR / 'database.sqlite'), help='Path to the live SQLite database')
    parser.add_argument('--backup-dir', default=str(BACKEND_DIR / 'backups'), help='Directory where backup files are stored')
    parser.add_argument('--label', default='manual', help='Label included in the backup filename')
    parser.add_argument('--keep', type=int, default=max(1, int(os.environ.get('DB_BACKUP_KEEP', '96'))), help='How many snapshots to retain')
    return parser.parse_args()


def main():
    args = parse_args()
    logger = _cli_logger()
    manifest = create_sqlite_backup(
        Path(args.database),
        Path(args.backup_dir),
        label=args.label,
        keep=max(1, args.keep),
        logger=logger,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
