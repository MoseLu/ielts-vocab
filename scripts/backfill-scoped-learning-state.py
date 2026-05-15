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
for path in (BACKEND_PATH, SDK_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from platform_sdk.runtime_env import load_split_service_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Backfill canonical scoped learning state from legacy projections.')
    parser.add_argument('--user-id', type=int, action='append', help='Backfill one user; can be repeated.')
    parser.add_argument('--dry-run', action='store_true', help='Compute and roll back without committing.')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    parser.add_argument('--env-file', help='Optional microservices env file.')
    parser.add_argument('--service-name', default='learning-core-service')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.env_file:
        os.environ['MICROSERVICES_ENV_FILE'] = str(Path(args.env_file).resolve())
    load_split_service_env(service_name=args.service_name)

    from app import create_app
    from services.scoped_learning_state_backfill import backfill_scoped_learning_state

    app = create_app()
    with app.app_context():
        summary = backfill_scoped_learning_state(user_ids=args.user_id, commit=not args.dry_run)

    if args.format == 'json':
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            'Backfilled scoped learning state: '
            f'users={summary["users"]} '
            f'quick_memory={summary["scoped_quick_memory_upserts"]} '
            f'wrong_words={summary["scoped_wrong_word_upserts"]} '
            f'committed={summary["committed"]}'
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
