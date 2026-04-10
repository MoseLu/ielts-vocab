from platform_sdk.service_schema import resolve_service_tables
from platform_sdk.service_table_plan import (
    get_service_bootstrap_table_names,
    get_service_owned_table_names,
    validate_service_table_plans,
)

from models import db


def test_service_table_plans_reference_known_models():
    errors = validate_service_table_plans(set(db.metadata.tables))
    assert errors == []


def test_identity_service_bootstrap_is_auth_only():
    table_names = [table.name for table in resolve_service_tables('identity-service', metadata=db.metadata)]

    assert set(table_names) == {
        'users',
        'email_verification_codes',
        'rate_limit_buckets',
        'revoked_tokens',
    }
    assert 'user_progress' not in table_names


def test_learning_core_bootstrap_includes_auth_shadow_tables():
    table_names = get_service_bootstrap_table_names('learning-core-service')

    assert 'users' in table_names
    assert 'revoked_tokens' in table_names
    assert 'user_progress' in table_names
    assert 'user_word_notes' not in table_names


def test_notes_and_ai_ownership_stays_split():
    notes_owned = get_service_owned_table_names('notes-service')
    ai_owned = get_service_owned_table_names('ai-execution-service')

    assert notes_owned == {
        'user_learning_notes',
        'user_daily_summaries',
        'user_word_notes',
    }
    assert ai_owned == {
        'user_conversation_history',
        'user_memory',
        'search_cache',
    }
