from __future__ import annotations

from dataclasses import dataclass


AUTH_CONTEXT_TABLES = frozenset({
    'users',
    'revoked_tokens',
})

IDENTITY_SERVICE_TABLES = frozenset({
    'users',
    'email_verification_codes',
    'rate_limit_buckets',
    'revoked_tokens',
})

LEARNING_CORE_SERVICE_TABLES = frozenset({
    'user_progress',
    'user_book_progress',
    'user_chapter_progress',
    'user_chapter_mode_progress',
    'user_added_books',
    'user_favorite_words',
    'user_familiar_words',
    'user_wrong_words',
    'user_study_sessions',
    'user_learning_events',
    'user_quick_memory_records',
    'user_smart_word_stats',
})

CATALOG_CONTENT_SERVICE_TABLES = frozenset({
    'custom_books',
    'custom_book_chapters',
    'custom_book_words',
    'word_root_details',
    'word_derivative_entries',
    'word_english_meanings',
    'word_example_entries',
    'word_catalog_entries',
    'word_catalog_book_refs',
})

NOTES_SERVICE_TABLES = frozenset({
    'user_learning_notes',
    'user_daily_summaries',
    'user_word_notes',
})

AI_EXECUTION_SERVICE_TABLES = frozenset({
    'user_conversation_history',
    'user_memory',
    'search_cache',
})


@dataclass(frozen=True)
class ServiceTablePlan:
    owned_tables: frozenset[str]
    shadow_tables: frozenset[str] = frozenset()

    @property
    def bootstrap_tables(self) -> frozenset[str]:
        return self.owned_tables | self.shadow_tables


SERVICE_TABLE_PLANS: dict[str, ServiceTablePlan] = {
    'gateway-bff': ServiceTablePlan(owned_tables=frozenset()),
    'identity-service': ServiceTablePlan(
        owned_tables=IDENTITY_SERVICE_TABLES,
    ),
    'learning-core-service': ServiceTablePlan(
        owned_tables=LEARNING_CORE_SERVICE_TABLES,
        shadow_tables=AUTH_CONTEXT_TABLES,
    ),
    'catalog-content-service': ServiceTablePlan(
        owned_tables=CATALOG_CONTENT_SERVICE_TABLES,
        shadow_tables=AUTH_CONTEXT_TABLES | {'user_word_notes'},
    ),
    'notes-service': ServiceTablePlan(
        owned_tables=NOTES_SERVICE_TABLES,
        shadow_tables=AUTH_CONTEXT_TABLES | LEARNING_CORE_SERVICE_TABLES | {'custom_books'},
    ),
    'ai-execution-service': ServiceTablePlan(
        owned_tables=AI_EXECUTION_SERVICE_TABLES,
        shadow_tables=AUTH_CONTEXT_TABLES | LEARNING_CORE_SERVICE_TABLES | NOTES_SERVICE_TABLES | CATALOG_CONTENT_SERVICE_TABLES,
    ),
    'admin-ops-service': ServiceTablePlan(
        owned_tables=frozenset(),
        shadow_tables=AUTH_CONTEXT_TABLES | LEARNING_CORE_SERVICE_TABLES | CATALOG_CONTENT_SERVICE_TABLES,
    ),
    'tts-media-service': ServiceTablePlan(owned_tables=frozenset()),
    'asr-service': ServiceTablePlan(owned_tables=frozenset()),
}


def get_service_table_plan(service_name: str) -> ServiceTablePlan:
    try:
        return SERVICE_TABLE_PLANS[service_name]
    except KeyError as exc:
        raise KeyError(f'Unknown microservice table plan: {service_name}') from exc


def get_service_owned_table_names(service_name: str) -> frozenset[str]:
    return get_service_table_plan(service_name).owned_tables


def get_service_bootstrap_table_names(service_name: str) -> frozenset[str]:
    return get_service_table_plan(service_name).bootstrap_tables


def iter_stateful_service_names(*, include_shadow_only: bool = True) -> list[str]:
    names: list[str] = []
    for service_name, plan in SERVICE_TABLE_PLANS.items():
        if plan.owned_tables or (include_shadow_only and plan.shadow_tables):
            names.append(service_name)
    return names


def validate_service_table_plans(available_table_names: set[str]) -> list[str]:
    errors: list[str] = []
    for service_name, plan in SERVICE_TABLE_PLANS.items():
        overlap = plan.owned_tables & plan.shadow_tables
        if overlap:
            errors.append(
                f'{service_name} declares the same tables as owned and shadow: {sorted(overlap)}'
            )
        unknown = plan.bootstrap_tables - available_table_names
        if unknown:
            errors.append(
                f'{service_name} references unknown tables: {sorted(unknown)}'
            )
    return errors
