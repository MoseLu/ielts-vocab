from __future__ import annotations

from dataclasses import dataclass


IDENTITY_SERVICE_REPOSITORIES = frozenset({
    'auth_repository',
})

LEARNING_CORE_SERVICE_REPOSITORIES = frozenset({
    'ai_quick_memory_repository',
    'ai_smart_word_stat_repository',
    'ai_wrong_word_repository',
    'books_user_state_repository',
    'learning_core_personalization_repository',
    'learning_event_repository',
    'learning_stats_repository',
    'legacy_progress_repository',
    'quick_memory_record_repository',
    'study_session_repository',
})

CATALOG_CONTENT_SERVICE_REPOSITORIES = frozenset({
    'ai_custom_book_repository',
    'books_confusable_repository',
    'word_catalog_repository',
})

NOTES_SERVICE_REPOSITORIES = frozenset({
    'daily_summary_repository',
    'learning_note_repository',
    'notes_summary_context_repository',
    'notes_word_note_repository',
})

AI_EXECUTION_SERVICE_REPOSITORIES = frozenset({
    'ai_assistant_repository',
    'search_cache_repository',
})

ADMIN_OPS_SERVICE_REPOSITORIES = frozenset({
    'admin_overview_repository',
    'admin_user_detail_repository',
    'admin_user_directory_repository',
    'admin_user_session_repository',
})


@dataclass(frozen=True)
class ServiceRepositoryPlan:
    owned_repositories: frozenset[str]
    shadow_repositories: frozenset[str] = frozenset()

    @property
    def repository_names(self) -> frozenset[str]:
        return self.owned_repositories | self.shadow_repositories


SERVICE_REPOSITORY_PLANS: dict[str, ServiceRepositoryPlan] = {
    'gateway-bff': ServiceRepositoryPlan(owned_repositories=frozenset()),
    'identity-service': ServiceRepositoryPlan(
        owned_repositories=IDENTITY_SERVICE_REPOSITORIES,
    ),
    'learning-core-service': ServiceRepositoryPlan(
        owned_repositories=LEARNING_CORE_SERVICE_REPOSITORIES,
    ),
    'catalog-content-service': ServiceRepositoryPlan(
        owned_repositories=CATALOG_CONTENT_SERVICE_REPOSITORIES,
        shadow_repositories=frozenset({'notes_word_note_repository'}),
    ),
    'notes-service': ServiceRepositoryPlan(
        owned_repositories=NOTES_SERVICE_REPOSITORIES,
    ),
    'ai-execution-service': ServiceRepositoryPlan(
        owned_repositories=AI_EXECUTION_SERVICE_REPOSITORIES,
        shadow_repositories=frozenset({
            'ai_custom_book_repository',
            'ai_quick_memory_repository',
            'ai_smart_word_stat_repository',
            'ai_wrong_word_repository',
            'learner_profile_repository',
            'learning_event_repository',
            'learning_stats_repository',
            'quick_memory_record_repository',
            'study_session_repository',
        }),
    ),
    'admin-ops-service': ServiceRepositoryPlan(
        owned_repositories=ADMIN_OPS_SERVICE_REPOSITORIES,
    ),
    'tts-media-service': ServiceRepositoryPlan(owned_repositories=frozenset()),
    'asr-service': ServiceRepositoryPlan(owned_repositories=frozenset()),
}


def get_service_repository_plan(service_name: str) -> ServiceRepositoryPlan:
    try:
        return SERVICE_REPOSITORY_PLANS[service_name]
    except KeyError as exc:
        raise KeyError(f'Unknown microservice repository plan: {service_name}') from exc


def get_service_owned_repository_names(service_name: str) -> frozenset[str]:
    return get_service_repository_plan(service_name).owned_repositories


def get_service_repository_names(service_name: str) -> frozenset[str]:
    return get_service_repository_plan(service_name).repository_names


def validate_service_repository_plans(available_repository_names: set[str]) -> list[str]:
    errors: list[str] = []
    for service_name, plan in SERVICE_REPOSITORY_PLANS.items():
        overlap = plan.owned_repositories & plan.shadow_repositories
        if overlap:
            errors.append(
                f'{service_name} declares the same repositories as owned and shadow: {sorted(overlap)}'
            )
        unknown = plan.repository_names - available_repository_names
        if unknown:
            errors.append(
                f'{service_name} references unknown repositories: {sorted(unknown)}'
            )
    return errors
