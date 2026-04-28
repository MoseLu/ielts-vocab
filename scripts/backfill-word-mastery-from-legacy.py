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
        description='Backfill UserWordMasteryState from QuickMemory, wrong words, and smart stats.',
    )
    parser.add_argument('--user-id', type=int, action='append', help='Backfill one user; can be repeated.')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    parser.add_argument('--env-file', help='Optional microservices env file.')
    parser.add_argument('--service-name', default='learning-core-service')
    parser.add_argument('--dry-run', action='store_true', help='Run audit only; do not write mastery rows.')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.env_file:
        os.environ['MICROSERVICES_ENV_FILE'] = str(Path(args.env_file).resolve())
    load_split_service_env(service_name=args.service_name)

    from app import create_app
    from services.learning_truth_maintenance import (
        audit_learning_truth,
        backfill_word_mastery_from_legacy,
    )

    app = create_app()
    with app.app_context():
        if args.dry_run:
            result = {'dry_run': True, 'audit': audit_learning_truth(user_ids=args.user_id)}
        else:
            result = {
                'dry_run': False,
                'backfill': backfill_word_mastery_from_legacy(user_ids=args.user_id),
                'audit': audit_learning_truth(user_ids=args.user_id),
            }

    if args.format == 'json':
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.dry_run:
        audit = result['audit']
        print(
            'Learning truth dry-run: '
            f"ok={audit['ok']} "
            f"legacy_words={audit['legacy_word_count']} "
            f"missing_mastery={len(audit['missing_mastery_words'])}"
        )
        return 0
    backfill = result['backfill']
    audit = result['audit']
    print(
        'Backfilled word mastery: '
        f"users={backfill['users']} "
        f"legacy_words={backfill['legacy_words']} "
        f"created={backfill['created']} "
        f"updated={backfill['updated']} "
        f"post_audit_ok={audit['ok']}"
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
