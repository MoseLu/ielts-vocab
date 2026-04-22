from __future__ import annotations

import argparse
import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))


VALIDATE_SCRIPT_PATH = REPO_ROOT / 'scripts' / 'validate_microservice_storage_parity.py'
MIGRATE_SCRIPT_PATH = REPO_ROOT / 'scripts' / 'migrate-sqlite-to-microservice-postgres.py'


def _load_script_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_validate_script = _load_script_module(
    VALIDATE_SCRIPT_PATH,
    'repair_microservice_storage_parity_validate',
)
_migrate_script = _load_script_module(
    MIGRATE_SCRIPT_PATH,
    'repair_microservice_storage_parity_migrate',
)


DEFAULT_SOURCE_SQLITE = _validate_script.DEFAULT_SOURCE_SQLITE
DEFAULT_ENV_FILE = _validate_script.DEFAULT_ENV_FILE


@dataclass(frozen=True)
class ServiceRepairReport:
    service_name: str
    target_url: str
    mismatched_tables_before: tuple[str, ...]
    mismatched_tables_after: tuple[str, ...]
    copied_counts: dict[str, int]
    repair_attempted: bool

    @property
    def clean(self) -> bool:
        return not self.mismatched_tables_after

    @property
    def repaired(self) -> bool:
        return self.repair_attempted and self.clean


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Repair microservice PostgreSQL parity drift from the canonical SQLite snapshot.',
    )
    parser.add_argument(
        '--service',
        action='append',
        dest='services',
        help='Service name to repair. Repeat for multiple services. Defaults to all write-owning services.',
    )
    parser.add_argument(
        '--scope',
        choices=('owned', 'bootstrap'),
        default='owned',
        help='Repair owned tables only, or the full bootstrap set including transitional tables.',
    )
    parser.add_argument(
        '--source-sqlite',
        default=None,
        help='Path to the canonical SQLite database snapshot.',
    )
    parser.add_argument(
        '--env-file',
        default=str(DEFAULT_ENV_FILE),
        help='Env file that contains per-service target database URLs.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Report the services that would be repaired without changing target databases.',
    )
    return parser.parse_args()


def _mismatched_table_names(results) -> tuple[str, ...]:
    return tuple(sorted(
        result.table_name
        for result in results
        if not result.matches
    ))


def repair_service_parity(
    service_name: str,
    *,
    scope: str,
    source_engine,
    target_engine,
    target_url: str,
    dry_run: bool,
) -> ServiceRepairReport:
    before_results = _validate_script.validate_service_parity(
        service_name,
        scope=scope,
        source_engine=source_engine,
        target_engine=target_engine,
    )
    mismatched_before = _mismatched_table_names(before_results)
    if not mismatched_before:
        return ServiceRepairReport(
            service_name=service_name,
            target_url=target_url,
            mismatched_tables_before=(),
            mismatched_tables_after=(),
            copied_counts={},
            repair_attempted=False,
        )

    if dry_run:
        return ServiceRepairReport(
            service_name=service_name,
            target_url=target_url,
            mismatched_tables_before=mismatched_before,
            mismatched_tables_after=mismatched_before,
            copied_counts={},
            repair_attempted=False,
        )

    copied_counts = _migrate_script.migrate_service(
        service_name,
        scope=scope,
        source_engine=source_engine,
        target_engine=target_engine,
        replace=True,
        bootstrap_only=False,
    )
    after_results = _validate_script.validate_service_parity(
        service_name,
        scope=scope,
        source_engine=source_engine,
        target_engine=target_engine,
    )
    return ServiceRepairReport(
        service_name=service_name,
        target_url=target_url,
        mismatched_tables_before=mismatched_before,
        mismatched_tables_after=_mismatched_table_names(after_results),
        copied_counts=copied_counts,
        repair_attempted=True,
    )


def _print_copied_counts(copied_counts: dict[str, int]) -> None:
    if not copied_counts:
        print('  copied rows: none')
        return
    print('  copied rows:')
    for table_name in sorted(copied_counts):
        print(f'  - {table_name}: {copied_counts[table_name]}')


def print_report(report: ServiceRepairReport) -> None:
    print(f'[{report.service_name}] target={report.target_url}')
    if not report.mismatched_tables_before:
        print('  status: already matched')
        return

    print(f'  before mismatch: {", ".join(report.mismatched_tables_before)}')
    if not report.repair_attempted:
        print('  action: dry-run only, no repair executed')
        return

    print('  action: replaced selected target tables from SQLite snapshot')
    _print_copied_counts(report.copied_counts)
    if report.mismatched_tables_after:
        print(f'  after mismatch: {", ".join(report.mismatched_tables_after)}')
        return
    print('  after mismatch: none')


def main() -> int:
    args = parse_args()
    env_file = Path(args.env_file).resolve()
    source_sqlite = _validate_script.resolve_source_sqlite_path(
        args.source_sqlite,
        env_file=env_file,
    )
    service_names = _validate_script.resolve_service_names(args.services, scope=args.scope)

    if not env_file.exists():
        raise FileNotFoundError(f'Env file not found: {env_file}')

    print(f'[source-sqlite] {source_sqlite}')
    source_engine = create_engine(f'sqlite:///{source_sqlite.as_posix()}')
    any_remaining_mismatch = False

    for service_name in service_names:
        target_url = _validate_script.load_target_database_url(service_name, env_file)
        target_engine = create_engine(target_url)
        report = repair_service_parity(
            service_name,
            scope=args.scope,
            source_engine=source_engine,
            target_engine=target_engine,
            target_url=target_engine.url.render_as_string(hide_password=True),
            dry_run=args.dry_run,
        )
        print_report(report)
        any_remaining_mismatch = any_remaining_mismatch or bool(report.mismatched_tables_after)

    return 1 if any_remaining_mismatch else 0


if __name__ == '__main__':
    raise SystemExit(main())
