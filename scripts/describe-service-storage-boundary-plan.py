from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from platform_sdk.service_storage_boundary_plan import (
    get_service_storage_boundary_plan,
    iter_service_storage_boundary_plans,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Print the Wave 4 split-service storage boundary plan.',
    )
    parser.add_argument(
        '--service',
        action='append',
        dest='services',
        help='Filter to a service. Repeat for multiple services.',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Emit JSON instead of plain text.',
    )
    return parser.parse_args()


def resolve_service_names(raw_services: list[str] | None) -> list[str]:
    if not raw_services:
        return [plan.service_name for plan in iter_service_storage_boundary_plans()]
    resolved: list[str] = []
    for service_name in raw_services:
        get_service_storage_boundary_plan(service_name)
        resolved.append(service_name)
    return resolved


def _plan_to_dict(service_name: str) -> dict:
    plan = get_service_storage_boundary_plan(service_name)
    return {
        'service_name': plan.service_name,
        'primary_storage_kind': plan.primary_storage_kind,
        'boundary_scope': plan.boundary_scope,
        'shared_sqlite_fallback_locked': plan.shared_sqlite_fallback_locked,
        'allow_service_local_sqlite': plan.allow_service_local_sqlite,
        'service_override_env': plan.service_override_env,
        'global_override_env': plan.global_override_env,
        'owned_tables': sorted(plan.owned_tables),
    }


def print_text(items: list[dict]) -> None:
    for item in items:
        print(f'[{item["service_name"]}]')
        print(f'  primary storage: {item["primary_storage_kind"]}')
        print(f'  boundary scope: {item["boundary_scope"]}')
        print(f'  shared SQLite fallback locked: {item["shared_sqlite_fallback_locked"]}')
        print(f'  service-local SQLite allowed: {item["allow_service_local_sqlite"]}')
        print(f'  service override env: {item["service_override_env"]}')
        print(f'  global override env: {item["global_override_env"]}')
        print('  owned tables:')
        for table_name in item['owned_tables']:
            print(f'  - {table_name}')
        print()


def main() -> int:
    args = parse_args()
    service_names = resolve_service_names(args.services)
    payload = [_plan_to_dict(service_name) for service_name in service_names]
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print_text(payload)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
