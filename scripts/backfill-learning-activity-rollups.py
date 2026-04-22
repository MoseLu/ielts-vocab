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
    parser = argparse.ArgumentParser(
        description='Backfill the five-level learning activity ledgers and rollups.',
    )
    parser.add_argument('--user-id', type=int, action='append', help='Backfill one user; can be repeated.')
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
    from services.learning_activity_backfill import backfill_learning_activity_rollups

    app = create_app()
    with app.app_context():
        summary = backfill_learning_activity_rollups(user_ids=args.user_id)

    if args.format == 'json':
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(
        'Backfilled learning activity rollups: '
        f'users={summary["users"]} '
        f'ledger_writes={summary["ledger_writes"]} '
        f'rebuilt_scopes={summary["rebuilt_scopes"]}'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
