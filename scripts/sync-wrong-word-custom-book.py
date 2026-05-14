#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from platform_sdk.runtime_env import load_split_service_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Sync canonical wrong-word custom books for one or more users.')
    parser.add_argument('--user-id', type=int, action='append', help='Sync one user; can be repeated. Defaults to all users with wrong words.')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    parser.add_argument('--env-file', help='Optional microservices env file.')
    parser.add_argument('--service-name', default='learning-core-service')
    return parser.parse_args()


def _collect_user_ids() -> list[int]:
    from app import create_app
    from service_models.learning_core_models import UserWrongWord

    app = create_app()
    with app.app_context():
        rows = (
            UserWrongWord.query
            .with_entities(UserWrongWord.user_id)
            .distinct()
            .order_by(UserWrongWord.user_id.asc())
            .all()
        )
    return [int(row[0]) for row in rows if row[0] is not None]


def main() -> int:
    args = parse_args()
    if args.env_file:
        os.environ['MICROSERVICES_ENV_FILE'] = str(Path(args.env_file).resolve())
    load_split_service_env(service_name=args.service_name)

    from app import create_app
    from service_models.learning_core_models import db
    from services.wrong_word_custom_book_service import sync_wrong_word_custom_book

    target_user_ids = args.user_id if args.user_id is not None else _collect_user_ids()
    summary = {'users': len(target_user_ids), 'synced': 0}

    app = create_app()
    with app.app_context():
        for user_id in target_user_ids:
            sync_wrong_word_custom_book(user_id)
            summary['synced'] += 1
        db.session.commit()

    if args.format == 'json':
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"Synced wrong-word custom books: users={summary['users']} synced={summary['synced']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
