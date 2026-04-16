from __future__ import annotations

from dataclasses import dataclass


AUTH_CONTEXT_TABLES = frozenset({
    'users',
    'revoked_tokens',
})

IDENTITY_EVENTING_TABLES = frozenset({
    'identity_outbox_events',
    'identity_inbox_events',
})
LEARNING_CORE_EVENTING_TABLES = frozenset({
    'learning_core_outbox_events',
    'learning_core_inbox_events',
})
CATALOG_CONTENT_EVENTING_TABLES = frozenset({
    'catalog_content_outbox_events',
    'catalog_content_inbox_events',
})
NOTES_EVENTING_TABLES = frozenset({
    'notes_outbox_events',
    'notes_inbox_events',
})
AI_EXECUTION_EVENTING_TABLES = frozenset({
    'ai_execution_outbox_events',
    'ai_execution_inbox_events',
})
TTS_MEDIA_EVENTING_TABLES = frozenset({
    'tts_media_assets',
    'tts_media_outbox_events',
    'tts_media_inbox_events',
})
ASR_EVENTING_TABLES = frozenset({
    'asr_outbox_events',
    'asr_inbox_events',
})
ADMIN_OPS_EVENTING_TABLES = frozenset({
    'admin_word_feedback',
    'admin_ops_outbox_events',
    'admin_ops_inbox_events',
    'admin_projection_cursors',
    'admin_projected_daily_summaries',
    'admin_projected_prompt_runs',
    'admin_projected_tts_media',
    'admin_projected_wrong_words',
    'admin_projected_study_sessions',
    'admin_projected_users',
})
ADMIN_OPS_EXAM_TABLES = frozenset({
    'exam_sources',
    'exam_assets',
    'exam_papers',
    'exam_sections',
    'exam_passages',
    'exam_questions',
    'exam_choices',
    'exam_answer_keys',
    'exam_ingestion_jobs',
    'exam_review_items',
    'exam_attempts',
    'exam_responses',
})

IDENTITY_SERVICE_TABLES = frozenset({
    'users',
    'email_verification_codes',
    'rate_limit_buckets',
    'revoked_tokens',
}) | IDENTITY_EVENTING_TABLES

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
    'user_word_mastery_states',
}) | LEARNING_CORE_EVENTING_TABLES

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
}) | CATALOG_CONTENT_EVENTING_TABLES

CUSTOM_BOOK_SHADOW_TABLES = frozenset({
    'custom_books',
    'custom_book_chapters',
    'custom_book_words',
})

USER_SCHEMA_SUPPORT_TABLES = frozenset({'users'})
NOTES_LEGACY_CONTEXT_TABLES = frozenset({
    'user_study_sessions',
    'user_wrong_words',
})
ADMIN_LEGACY_DETAIL_TABLES = frozenset({
    'users',
    'user_book_progress',
    'user_chapter_progress',
    'user_favorite_words',
    'user_learning_events',
    'user_study_sessions',
    'user_wrong_words',
})
AI_LEGACY_NOTES_TABLES = frozenset({
    'user_daily_summaries',
    'user_learning_notes',
})

NOTES_SERVICE_TABLES = frozenset({
    'notes_projection_cursors',
    'notes_projected_prompt_runs',
    'notes_projected_study_sessions',
    'notes_projected_wrong_words',
    'user_learning_notes',
    'user_daily_summaries',
    'user_word_notes',
}) | NOTES_EVENTING_TABLES

AI_EXECUTION_SERVICE_TABLES = frozenset({
    'ai_projection_cursors',
    'ai_projected_daily_summaries',
    'ai_projected_wrong_words',
    'ai_prompt_runs',
    'ai_speaking_assessments',
    'ai_word_image_assets',
    'user_home_todo_items',
    'user_home_todo_plans',
    'user_conversation_history',
    'user_memory',
    'search_cache',
}) | AI_EXECUTION_EVENTING_TABLES

ADMIN_OPS_SERVICE_TABLES = ADMIN_OPS_EVENTING_TABLES | ADMIN_OPS_EXAM_TABLES
TTS_MEDIA_SERVICE_TABLES = TTS_MEDIA_EVENTING_TABLES
ASR_SERVICE_TABLES = ASR_EVENTING_TABLES


@dataclass(frozen=True)
class ServiceTablePlan:
    owned_tables: frozenset[str]
    read_only_tables: frozenset[str] = frozenset()
    transitional_tables: frozenset[str] = frozenset()
    schema_support_tables: frozenset[str] = frozenset()

    @property
    def non_owned_tables(self) -> frozenset[str]:
        return self.read_only_tables | self.transitional_tables

    @property
    def shadow_tables(self) -> frozenset[str]:
        # Compatibility alias for callers that still consume the old Wave 3 term.
        return self.non_owned_tables

    @property
    def bootstrap_tables(self) -> frozenset[str]:
        return self.owned_tables | self.non_owned_tables | self.schema_support_tables


@dataclass(frozen=True)
class TableBoundaryAuditRow:
    table_name: str
    owner_services: tuple[str, ...]
    read_only_services: tuple[str, ...] = ()
    transitional_services: tuple[str, ...] = ()

    @property
    def owner_service(self) -> str | None:
        if len(self.owner_services) == 1:
            return self.owner_services[0]
        return None


SERVICE_TABLE_PLANS: dict[str, ServiceTablePlan] = {
    'gateway-bff': ServiceTablePlan(owned_tables=frozenset()),
    'identity-service': ServiceTablePlan(
        owned_tables=IDENTITY_SERVICE_TABLES,
    ),
    'learning-core-service': ServiceTablePlan(
        owned_tables=LEARNING_CORE_SERVICE_TABLES,
        transitional_tables=CUSTOM_BOOK_SHADOW_TABLES,
        schema_support_tables=USER_SCHEMA_SUPPORT_TABLES,
    ),
    'catalog-content-service': ServiceTablePlan(
        owned_tables=CATALOG_CONTENT_SERVICE_TABLES,
        transitional_tables={'user_word_notes'},
        schema_support_tables=USER_SCHEMA_SUPPORT_TABLES,
    ),
    'notes-service': ServiceTablePlan(
        owned_tables=NOTES_SERVICE_TABLES,
        schema_support_tables=USER_SCHEMA_SUPPORT_TABLES,
    ),
    'ai-execution-service': ServiceTablePlan(
        owned_tables=AI_EXECUTION_SERVICE_TABLES,
        schema_support_tables=USER_SCHEMA_SUPPORT_TABLES,
    ),
    'admin-ops-service': ServiceTablePlan(
        owned_tables=ADMIN_OPS_SERVICE_TABLES,
    ),
    'tts-media-service': ServiceTablePlan(owned_tables=TTS_MEDIA_SERVICE_TABLES),
    'asr-service': ServiceTablePlan(owned_tables=ASR_SERVICE_TABLES),
}


def get_service_table_plan(service_name: str) -> ServiceTablePlan:
    try:
        return SERVICE_TABLE_PLANS[service_name]
    except KeyError as exc:
        raise KeyError(f'Unknown microservice table plan: {service_name}') from exc


def get_service_owned_table_names(service_name: str) -> frozenset[str]:
    return get_service_table_plan(service_name).owned_tables


def get_service_read_only_table_names(service_name: str) -> frozenset[str]:
    return get_service_table_plan(service_name).read_only_tables


def get_service_transitional_table_names(service_name: str) -> frozenset[str]:
    return get_service_table_plan(service_name).transitional_tables


def get_service_bootstrap_table_names(service_name: str) -> frozenset[str]:
    return get_service_table_plan(service_name).bootstrap_tables


def iter_stateful_service_names(*, include_shadow_only: bool = True) -> list[str]:
    names: list[str] = []
    for service_name, plan in SERVICE_TABLE_PLANS.items():
        if plan.owned_tables or (include_shadow_only and plan.non_owned_tables):
            names.append(service_name)
    return names


def iter_table_boundary_audit_rows() -> list[TableBoundaryAuditRow]:
    owner_by_table: dict[str, list[str]] = {}
    read_only_by_table: dict[str, list[str]] = {}
    transitional_by_table: dict[str, list[str]] = {}
    planned_tables: set[str] = set()

    for service_name, plan in SERVICE_TABLE_PLANS.items():
        planned_tables.update(plan.bootstrap_tables)

        for table_name in plan.owned_tables:
            owner_by_table.setdefault(table_name, []).append(service_name)

        for table_name in plan.read_only_tables:
            read_only_by_table.setdefault(table_name, []).append(service_name)

        for table_name in plan.transitional_tables:
            transitional_by_table.setdefault(table_name, []).append(service_name)

    return [
        TableBoundaryAuditRow(
            table_name=table_name,
            owner_services=tuple(sorted(owner_by_table.get(table_name, ()))),
            read_only_services=tuple(sorted(read_only_by_table.get(table_name, ()))),
            transitional_services=tuple(sorted(transitional_by_table.get(table_name, ()))),
        )
        for table_name in sorted(planned_tables)
    ]


def validate_service_table_plans(available_table_names: set[str]) -> list[str]:
    errors: list[str] = []
    owner_by_table: dict[str, str] = {}

    for service_name, plan in SERVICE_TABLE_PLANS.items():
        overlap_owned_read_only = plan.owned_tables & plan.read_only_tables
        if overlap_owned_read_only:
            errors.append(
                f'{service_name} declares the same tables as owned and read-only: {sorted(overlap_owned_read_only)}'
            )

        overlap_owned_transitional = plan.owned_tables & plan.transitional_tables
        if overlap_owned_transitional:
            errors.append(
                f'{service_name} declares the same tables as owned and transitional: {sorted(overlap_owned_transitional)}'
            )

        overlap_read_only_transitional = plan.read_only_tables & plan.transitional_tables
        if overlap_read_only_transitional:
            errors.append(
                f'{service_name} declares the same tables as read-only and transitional: {sorted(overlap_read_only_transitional)}'
            )

        unknown = plan.bootstrap_tables - available_table_names
        if unknown:
            errors.append(
                f'{service_name} references unknown tables: {sorted(unknown)}'
            )

        for table_name in sorted(plan.owned_tables):
            previous_owner = owner_by_table.get(table_name)
            if previous_owner is not None:
                errors.append(
                    f'table {table_name} is owned by both {previous_owner} and {service_name}'
                )
            else:
                owner_by_table[table_name] = service_name

    for service_name, plan in SERVICE_TABLE_PLANS.items():
        unowned_non_owned = sorted(
            table_name
            for table_name in plan.non_owned_tables
            if table_name not in owner_by_table
        )
        if unowned_non_owned:
            errors.append(
                f'{service_name} references non-owned tables without an owning service: {unowned_non_owned}'
            )

    unowned_tables = sorted(available_table_names - set(owner_by_table))
    if unowned_tables:
        errors.append(
            f'tables missing an owning service assignment: {unowned_tables}'
        )

    return errors
