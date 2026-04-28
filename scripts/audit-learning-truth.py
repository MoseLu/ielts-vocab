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
        description='Audit legacy learning facts against mastery and learning ledgers.',
    )
    parser.add_argument('--user-id', type=int, action='append', help='Audit one user; can be repeated.')
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
    from services.learning_truth_maintenance import audit_learning_truth

    app = create_app()
    with app.app_context():
        report = audit_learning_truth(user_ids=args.user_id)

    if args.format == 'json':
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if report['ok'] else 1
    print(
        'Learning truth audit: '
        f"ok={report['ok']} "
        f"users={report['users']} "
        f"legacy_words={report['legacy_word_count']} "
        f"mastery_words={report['mastery_word_count']} "
        f"missing_mastery={len(report['missing_mastery_words'])} "
        f"scope_mismatches={len(report['scope_mismatches'])}"
    )
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
