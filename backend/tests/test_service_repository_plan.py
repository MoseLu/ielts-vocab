from pathlib import Path

from platform_sdk.service_repository_plan import (
    get_service_owned_repository_names,
    get_service_repository_names,
    validate_service_repository_plans,
)


def _available_repository_names() -> set[str]:
    services_dir = Path(__file__).resolve().parents[1] / 'services'
    return {
        path.stem
        for path in services_dir.glob('*_repository.py')
    }


def test_service_repository_plans_reference_known_repositories():
    errors = validate_service_repository_plans(_available_repository_names())
    assert errors == []


def test_learning_core_owns_personalization_but_not_word_note_repository():
    owned = get_service_owned_repository_names('learning-core-service')

    assert 'learning_core_personalization_repository' in owned
    assert 'notes_word_note_repository' not in owned


def test_notes_service_owns_word_note_repository():
    owned = get_service_owned_repository_names('notes-service')

    assert owned >= {
        'daily_summary_repository',
        'learning_note_repository',
        'notes_summary_context_repository',
        'notes_word_note_repository',
    }


def test_catalog_and_ai_shadow_cross_domain_repositories_explicitly():
    catalog_repositories = get_service_repository_names('catalog-content-service')
    ai_repositories = get_service_repository_names('ai-execution-service')

    assert 'notes_word_note_repository' in catalog_repositories
    assert 'ai_custom_book_repository' in ai_repositories
    assert 'search_cache_repository' in ai_repositories
