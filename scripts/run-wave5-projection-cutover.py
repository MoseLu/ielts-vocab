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
from platform_sdk.wave5_projection_cutover import run_wave5_projection_cutover


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Run the controlled Wave 5 projection cutover bootstrap and verification pack.',
    )
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Skip bootstrap and only verify current projection marker/count readiness.',
    )
    return parser.parse_args()


def _print_text(result: dict) -> None:
    print(
        'Wave 5 projection cutover: '
        f'ok={str(bool(result["ok"])).lower()} '
        f'bootstrap_ran={str(bool(result["bootstrap_ran"])).lower()}'
    )
    if isinstance(result.get('bootstrap'), dict):
        bootstrap = result['bootstrap']
        print(
            'Bootstrap summary: '
            f'admin={bootstrap["admin"]} '
            f'notes={bootstrap["notes"]} '
            f'ai={bootstrap["ai"]}'
        )
    for group_name in ('admin', 'notes', 'ai'):
        print(f'{group_name}:')
        for key, item in result[group_name].items():
            print(
                f'  - {key}: '
                f'ready={str(bool(item["ready"])).lower()} '
                f'counts_match={str(bool(item["counts_match"])).lower()} '
                f'source={item["source_count"]} '
                f'projected={item["projected_count"]}'
            )


def main() -> int:
    args = parse_args()
    app = create_app()
    with app.app_context():
        result = run_wave5_projection_cutover(bootstrap=not args.verify_only)

    if args.format == 'json':
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_text(result)
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
