from __future__ import annotations

from dataclasses import dataclass

from platform_sdk.service_table_plan import get_service_owned_table_names


def _service_slug(service_name: str) -> str:
    return service_name.replace('-', '_')


@dataclass(frozen=True)
class ServiceMigrationPlan:
    service_name: str
    migration_slug: str
    baseline_revision: str
    baseline_label: str
    version_table: str
    owned_tables: frozenset[str]

    @property
    def env_prefix(self) -> str:
        return self.migration_slug.upper()


def _build_plan(service_name: str, *, baseline_suffix: str, baseline_label: str) -> ServiceMigrationPlan:
    migration_slug = _service_slug(service_name)
    return ServiceMigrationPlan(
        service_name=service_name,
        migration_slug=migration_slug,
        baseline_revision=f'{migration_slug}_{baseline_suffix}',
        baseline_label=baseline_label,
        version_table=f'alembic_version_{migration_slug}',
        owned_tables=get_service_owned_table_names(service_name),
    )


SERVICE_MIGRATION_PLANS: dict[str, ServiceMigrationPlan] = {
    'identity-service': _build_plan(
        'identity-service',
        baseline_suffix='0001',
        baseline_label='identity baseline',
    ),
    'learning-core-service': _build_plan(
        'learning-core-service',
        baseline_suffix='0001',
        baseline_label='learning core baseline',
    ),
    'catalog-content-service': _build_plan(
        'catalog-content-service',
        baseline_suffix='0001',
        baseline_label='catalog content baseline',
    ),
    'notes-service': _build_plan(
        'notes-service',
        baseline_suffix='0001',
        baseline_label='notes baseline',
    ),
    'ai-execution-service': _build_plan(
        'ai-execution-service',
        baseline_suffix='0001',
        baseline_label='ai execution baseline',
    ),
}


def get_service_migration_plan(service_name: str) -> ServiceMigrationPlan:
    try:
        return SERVICE_MIGRATION_PLANS[service_name]
    except KeyError as exc:
        raise KeyError(f'Unknown microservice migration plan: {service_name}') from exc


def iter_service_migration_plans() -> list[ServiceMigrationPlan]:
    return list(SERVICE_MIGRATION_PLANS.values())


def iter_service_migration_service_names() -> list[str]:
    return [plan.service_name for plan in iter_service_migration_plans()]


def validate_service_migration_plans() -> list[str]:
    errors: list[str] = []
    seen_revisions: dict[str, str] = {}
    seen_version_tables: dict[str, str] = {}
    seen_slugs: dict[str, str] = {}

    for service_name, plan in SERVICE_MIGRATION_PLANS.items():
        if not plan.owned_tables:
            errors.append(f'{service_name} has no owned tables in the migration plan')

        expected_tables = get_service_owned_table_names(service_name)
        if plan.owned_tables != expected_tables:
            errors.append(
                f'{service_name} migration plan owned tables drifted: '
                f'expected {sorted(expected_tables)}, got {sorted(plan.owned_tables)}'
            )

        duplicated_revision = seen_revisions.get(plan.baseline_revision)
        if duplicated_revision is not None:
            errors.append(
                f'{service_name} reuses baseline revision {plan.baseline_revision} with {duplicated_revision}'
            )
        else:
            seen_revisions[plan.baseline_revision] = service_name

        duplicated_version_table = seen_version_tables.get(plan.version_table)
        if duplicated_version_table is not None:
            errors.append(
                f'{service_name} reuses version table {plan.version_table} with {duplicated_version_table}'
            )
        else:
            seen_version_tables[plan.version_table] = service_name

        duplicated_slug = seen_slugs.get(plan.migration_slug)
        if duplicated_slug is not None:
            errors.append(
                f'{service_name} reuses migration slug {plan.migration_slug} with {duplicated_slug}'
            )
        else:
            seen_slugs[plan.migration_slug] = service_name

    return errors
