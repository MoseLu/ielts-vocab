from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from platform_sdk.service_migration_plan import (
    get_service_migration_plan,
    iter_service_migration_plans,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Print the per-service migration baseline plan.',
    )
    parser.add_argument(
        '--service',
        action='append',
        dest='services',
        help='Service name to print. Repeat for multiple services. Defaults to all migration-planned services.',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Emit JSON instead of plain text.',
    )
    return parser.parse_args()


def resolve_plans(raw_services: list[str] | None):
    if not raw_services:
        return iter_service_migration_plans()
    return [get_service_migration_plan(service_name) for service_name in raw_services]


def to_dict(plan) -> dict:
    return {
        'service_name': plan.service_name,
        'migration_slug': plan.migration_slug,
        'baseline_revision': plan.baseline_revision,
        'baseline_label': plan.baseline_label,
        'version_table': plan.version_table,
        'env_prefix': plan.env_prefix,
        'owned_tables': sorted(plan.owned_tables),
    }


def print_text(plans) -> None:
    for plan in plans:
        print(f'[{plan.service_name}]')
        print(f'  migration_slug: {plan.migration_slug}')
        print(f'  baseline_revision: {plan.baseline_revision}')
        print(f'  baseline_label: {plan.baseline_label}')
        print(f'  version_table: {plan.version_table}')
        print(f'  env_prefix: {plan.env_prefix}')
        for table_name in sorted(plan.owned_tables):
            print(f'  - {table_name}')


def main() -> int:
    args = parse_args()
    plans = resolve_plans(args.services)
    if args.json:
        print(json.dumps([to_dict(plan) for plan in plans], ensure_ascii=False, indent=2))
        return 0
    print_text(plans)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
