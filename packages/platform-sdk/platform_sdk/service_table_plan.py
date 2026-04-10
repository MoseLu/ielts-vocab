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
    'tts_media_outbox_events',
    'tts_media_inbox_events',
})
ASR_EVENTING_TABLES = frozenset({
    'asr_outbox_events',
    'asr_inbox_events',
})
ADMIN_OPS_EVENTING_TABLES = frozenset({
    'admin_ops_outbox_events',
    'admin_ops_inbox_events',
    'admin_projection_cursors',
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

NOTES_SERVICE_TABLES = frozenset({
    'user_learning_notes',
    'user_daily_summaries',
    'user_word_notes',
}) | NOTES_EVENTING_TABLES

AI_EXECUTION_SERVICE_TABLES = frozenset({
    'user_conversation_history',
    'user_memory',
    'search_cache',
}) | AI_EXECUTION_EVENTING_TABLES

ADMIN_OPS_SERVICE_TABLES = ADMIN_OPS_EVENTING_TABLES
TTS_MEDIA_SERVICE_TABLES = TTS_MEDIA_EVENTING_TABLES
ASR_SERVICE_TABLES = ASR_EVENTING_TABLES


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
        shadow_tables=AUTH_CONTEXT_TABLES | CUSTOM_BOOK_SHADOW_TABLES,
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
        owned_tables=ADMIN_OPS_SERVICE_TABLES,
        shadow_tables=AUTH_CONTEXT_TABLES | LEARNING_CORE_SERVICE_TABLES | CATALOG_CONTENT_SERVICE_TABLES,
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
