from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from app import create_app
from platform_sdk.admin_projection_bootstrap import bootstrap_admin_projection_snapshots


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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
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
