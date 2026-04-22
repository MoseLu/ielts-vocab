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
        description='Repair learning evidence, rebuild five-level ledgers, and purge deprecated progress rows.',
    )
    parser.add_argument('--user-id', type=int, action='append', help='Finalize one user; can be repeated.')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    parser.add_argument('--env-file', help='Optional microservices env file.')
    parser.add_argument('--service-name', default='learning-core-service')
    parser.add_argument('--skip-repair', action='store_true')
    parser.add_argument('--skip-purge', action='store_true')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.env_file:
        os.environ['MICROSERVICES_ENV_FILE'] = str(Path(args.env_file).resolve())
    load_split_service_env(service_name=args.service_name)

    from app import create_app
    from services.learning_activity_backfill import backfill_learning_activity_rollups
    from services.learning_activity_cutover import (
        learning_activity_cutover_report,
        purge_deprecated_learning_progress,
        repair_learning_activity_evidence,
    )

    app = create_app()
    with app.app_context():
        repair = (
            {'skipped': True}
            if args.skip_repair
            else repair_learning_activity_evidence(user_ids=args.user_id)
        )
        backfill = backfill_learning_activity_rollups(user_ids=args.user_id)
        purge = (
            {'skipped': True}
            if args.skip_purge
            else purge_deprecated_learning_progress(user_ids=args.user_id)
        )
        report = learning_activity_cutover_report(user_ids=args.user_id)

    summary = {
        'repair': repair,
        'backfill': backfill,
        'purge': purge,
        'report': report,
    }
    if args.format == 'json':
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            'Finalized learning activity cutover: '
            f"users={backfill.get('users', 0)} "
            f"ledger_writes={backfill.get('ledger_writes', 0)} "
            f"deprecated_rows={report['deprecated_rows']} "
            f"fallback_ledgers={report['fallback_ledgers']}"
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
