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
        description='Bootstrap admin read-model projections from the current shared tables.',
    )
    parser.add_argument(
        '--format',
        choices=('text', 'json'),
        default='text',
        help='Output format.',
    )
    parser.add_argument(
        '--env-file',
        help='Optional microservices env file. Defaults to MICROSERVICES_ENV_FILE or backend/.env.microservices.local.',
    )
    parser.add_argument(
        '--service-name',
        default='admin-ops-service',
        help='Split service context to load before connecting to storage.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.env_file:
        os.environ['MICROSERVICES_ENV_FILE'] = str(Path(args.env_file).resolve())
    load_split_service_env(service_name=args.service_name)

    from app import create_app
    from platform_sdk.admin_projection_bootstrap import bootstrap_admin_projection_snapshots

    app = create_app()
    with app.app_context():
        summary = bootstrap_admin_projection_snapshots()

    if args.format == 'json':
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            'Bootstrapped admin projections: '
            f'users={summary["users"]} '
            f'study_sessions={summary["study_sessions"]} '
            f'wrong_words={summary["wrong_words"]}'
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
