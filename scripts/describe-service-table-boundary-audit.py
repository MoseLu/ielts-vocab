from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from platform_sdk.service_table_plan import (
    SERVICE_TABLE_PLANS,
    get_service_table_plan,
    iter_table_boundary_audit_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Print the Wave 4 service-table boundary audit.',
    )
    parser.add_argument(
        '--view',
        choices=('services', 'tables'),
        default='services',
        help='Render the audit grouped by service or by table.',
    )
    parser.add_argument(
        '--service',
        action='append',
        dest='services',
        help='Filter to a service. Repeat for multiple services.',
    )
    parser.add_argument(
        '--table',
        action='append',
        dest='tables',
        help='Filter to a table. Repeat for multiple tables.',
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Emit JSON instead of plain text.',
    )
    return parser.parse_args()


def _sorted_list(values) -> list[str]:
    return sorted(values)


def _service_to_dict(service_name: str) -> dict:
    plan = get_service_table_plan(service_name)
    return {
        'service_name': service_name,
        'owned_tables': _sorted_list(plan.owned_tables),
        'read_only_tables': _sorted_list(plan.read_only_tables),
        'transitional_tables': _sorted_list(plan.transitional_tables),
        'non_owned_tables': _sorted_list(plan.non_owned_tables),
        'bootstrap_tables': _sorted_list(plan.bootstrap_tables),
    }


def _table_to_dict(row) -> dict:
    return {
        'table_name': row.table_name,
        'owner_service': row.owner_service,
        'owner_services': list(row.owner_services),
        'read_only_services': list(row.read_only_services),
        'transitional_services': list(row.transitional_services),
    }


def resolve_service_names(raw_services: list[str] | None) -> list[str]:
    if not raw_services:
        return list(SERVICE_TABLE_PLANS)
    service_names: list[str] = []
    for service_name in raw_services:
        get_service_table_plan(service_name)
        service_names.append(service_name)
    return service_names


def resolve_table_rows(
    *,
    raw_services: list[str] | None,
    raw_tables: list[str] | None,
):
    selected_services = set(raw_services or [])
    selected_tables = set(raw_tables or [])
    rows = iter_table_boundary_audit_rows()

    if selected_services:
        rows = [
            row
            for row in rows
            if selected_services.intersection(
                set(row.owner_services)
                | set(row.read_only_services)
                | set(row.transitional_services)
            )
        ]

    if selected_tables:
        rows = [row for row in rows if row.table_name in selected_tables]

    return rows


def _print_table_block(label: str, table_names) -> None:
    print(f'  {label}:')
    if not table_names:
        print('  - none')
        return
    for table_name in sorted(table_names):
        print(f'  - {table_name}')


def print_services_text(items: list[dict]) -> None:
    for item in items:
        print(f'[{item["service_name"]}]')
        _print_table_block('owned', item['owned_tables'])
        _print_table_block('read-only', item['read_only_tables'])
        _print_table_block('transitional', item['transitional_tables'])
        print()


def _render_service_list(services: tuple[str, ...]) -> str:
    return ', '.join(services) if services else '-'


def print_tables_text(rows) -> None:
    for row in rows:
        print(f'[{row.table_name}]')
        print(f'  owner: {_render_service_list(row.owner_services)}')
        print(f'  read-only: {_render_service_list(row.read_only_services)}')
        print(f'  transitional: {_render_service_list(row.transitional_services)}')
        print()


def main() -> int:
    args = parse_args()
    service_names = resolve_service_names(args.services)

    if args.view == 'services':
        payload = [_service_to_dict(service_name) for service_name in service_names]
        if args.tables:
            selected = set(args.tables)
            payload = [
                {
                    **item,
                    'owned_tables': [name for name in item['owned_tables'] if name in selected],
                    'read_only_tables': [name for name in item['read_only_tables'] if name in selected],
                    'transitional_tables': [name for name in item['transitional_tables'] if name in selected],
                    'non_owned_tables': [name for name in item['non_owned_tables'] if name in selected],
                    'bootstrap_tables': [name for name in item['bootstrap_tables'] if name in selected],
                }
                for item in payload
                if selected.intersection(item['bootstrap_tables'])
            ]
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        print_services_text(payload)
        return 0

    rows = resolve_table_rows(
        raw_services=args.services,
        raw_tables=args.tables,
    )
    payload = [_table_to_dict(row) for row in rows]
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    print_tables_text(rows)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
