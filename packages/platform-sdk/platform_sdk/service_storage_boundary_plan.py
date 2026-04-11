from __future__ import annotations

from dataclasses import dataclass

from platform_sdk.service_table_plan import SERVICE_TABLE_PLANS, get_service_owned_table_names


ALLOW_SHARED_SPLIT_SERVICE_SQLITE_ENV = 'ALLOW_SHARED_SPLIT_SERVICE_SQLITE'
ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES_ENV = 'ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES'


@dataclass(frozen=True)
class ServiceStorageBoundaryPlan:
    service_name: str
    primary_storage_kind: str
    boundary_scope: str
    owned_tables: frozenset[str]
    shared_sqlite_fallback_locked: bool = True
    allow_service_local_sqlite: bool = True
    service_override_env: str = ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES_ENV
    global_override_env: str = ALLOW_SHARED_SPLIT_SERVICE_SQLITE_ENV


def _build_plan(
    service_name: str,
    *,
    primary_storage_kind: str,
    boundary_scope: str,
) -> ServiceStorageBoundaryPlan:
    return ServiceStorageBoundaryPlan(
        service_name=service_name,
        primary_storage_kind=primary_storage_kind,
        boundary_scope=boundary_scope,
        owned_tables=get_service_owned_table_names(service_name),
    )


SERVICE_STORAGE_BOUNDARY_PLANS: dict[str, ServiceStorageBoundaryPlan] = {
    'identity-service': _build_plan(
        'identity-service',
        primary_storage_kind='postgresql',
        boundary_scope='owned-data',
    ),
    'learning-core-service': _build_plan(
        'learning-core-service',
        primary_storage_kind='postgresql',
        boundary_scope='owned-data',
    ),
    'catalog-content-service': _build_plan(
        'catalog-content-service',
        primary_storage_kind='postgresql',
        boundary_scope='owned-data',
    ),
    'ai-execution-service': _build_plan(
        'ai-execution-service',
        primary_storage_kind='postgresql',
        boundary_scope='owned-data',
    ),
    'notes-service': _build_plan(
        'notes-service',
        primary_storage_kind='postgresql',
        boundary_scope='owned-data',
    ),
    'tts-media-service': _build_plan(
        'tts-media-service',
        primary_storage_kind='postgresql',
        boundary_scope='service-eventing',
    ),
    'asr-service': _build_plan(
        'asr-service',
        primary_storage_kind='postgresql',
        boundary_scope='service-eventing',
    ),
    'admin-ops-service': _build_plan(
        'admin-ops-service',
        primary_storage_kind='postgresql',
        boundary_scope='eventing-and-projections',
    ),
}


def get_service_storage_boundary_plan(service_name: str) -> ServiceStorageBoundaryPlan:
    try:
        return SERVICE_STORAGE_BOUNDARY_PLANS[service_name]
    except KeyError as exc:
        raise KeyError(f'Unknown service storage boundary plan: {service_name}') from exc


def iter_service_storage_boundary_plans() -> list[ServiceStorageBoundaryPlan]:
    return list(SERVICE_STORAGE_BOUNDARY_PLANS.values())


def iter_guarded_split_service_names() -> list[str]:
    return [plan.service_name for plan in iter_service_storage_boundary_plans()]


def shared_sqlite_fallback_locked_for_service(service_name: str | None) -> bool:
    if not service_name:
        return False
    plan = SERVICE_STORAGE_BOUNDARY_PLANS.get(service_name)
    return bool(plan and plan.shared_sqlite_fallback_locked)


def validate_service_storage_boundary_plans() -> list[str]:
    errors: list[str] = []
    expected_services = {
        service_name
        for service_name, plan in SERVICE_TABLE_PLANS.items()
        if plan.owned_tables
    }
    configured_services = set(SERVICE_STORAGE_BOUNDARY_PLANS)

    missing = sorted(expected_services - configured_services)
    if missing:
        errors.append(f'missing storage boundary plans for services: {missing}')

    extra = sorted(configured_services - expected_services)
    if extra:
        errors.append(f'storage boundary plans reference unknown services: {extra}')

    for service_name, plan in SERVICE_STORAGE_BOUNDARY_PLANS.items():
        expected_owned_tables = get_service_owned_table_names(service_name)
        if not plan.owned_tables:
            errors.append(f'{service_name} has no owned tables in the storage boundary plan')
        if plan.owned_tables != expected_owned_tables:
            errors.append(
                f'{service_name} storage boundary owned tables drifted: '
                f'expected {sorted(expected_owned_tables)}, got {sorted(plan.owned_tables)}'
            )
        if not plan.shared_sqlite_fallback_locked:
            errors.append(f'{service_name} leaves shared SQLite fallback unlocked')
        if not plan.service_override_env:
            errors.append(f'{service_name} is missing a service-scoped SQLite override env name')
        if not plan.global_override_env:
            errors.append(f'{service_name} is missing a global SQLite override env name')

    return errors
