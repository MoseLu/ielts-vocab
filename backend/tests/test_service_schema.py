from platform_sdk.service_model_registry import get_service_model_module_names
from platform_sdk.service_schema import resolve_monolith_tables, resolve_service_tables
from platform_sdk.service_table_plan import (
    get_service_bootstrap_table_names,
    get_service_owned_table_names,
    iter_stateful_service_names,
    validate_service_table_plans,
)

from models import db



def test_service_table_plans_reference_known_models():
    errors = validate_service_table_plans(set(db.metadata.tables))
    assert errors == []



def test_identity_service_bootstrap_includes_identity_eventing_tables():
    table_names = {table.name for table in resolve_service_tables('identity-service', metadata=db.metadata)}

    assert table_names == {
        'users',
        'email_verification_codes',
        'rate_limit_buckets',
        'revoked_tokens',
        'identity_outbox_events',
        'identity_inbox_events',
    }
    assert 'user_progress' not in table_names



def test_learning_core_bootstrap_includes_auth_shadow_tables():
    table_names = get_service_bootstrap_table_names('learning-core-service')

    assert 'users' in table_names
    assert 'revoked_tokens' in table_names
    assert 'user_progress' in table_names
    assert 'custom_books' in table_names
    assert 'custom_book_chapters' in table_names
    assert 'custom_book_words' in table_names
    assert 'learning_core_outbox_events' in table_names
    assert 'learning_core_inbox_events' in table_names
    assert 'user_word_notes' not in table_names



def test_notes_and_ai_ownership_stays_split():
    notes_owned = get_service_owned_table_names('notes-service')
    ai_owned = get_service_owned_table_names('ai-execution-service')

    assert notes_owned == {
        'user_learning_notes',
        'user_daily_summaries',
        'user_word_notes',
        'notes_outbox_events',
        'notes_inbox_events',
    }
    assert ai_owned == {
        'user_conversation_history',
        'user_memory',
        'search_cache',
        'ai_execution_outbox_events',
        'ai_execution_inbox_events',
    }



def test_event_only_services_become_stateful_via_eventing_tables():
    tts_owned = get_service_owned_table_names('tts-media-service')
    asr_owned = get_service_owned_table_names('asr-service')
    admin_owned = get_service_owned_table_names('admin-ops-service')

    assert tts_owned == {'tts_media_outbox_events', 'tts_media_inbox_events'}
    assert asr_owned == {'asr_outbox_events', 'asr_inbox_events'}
    assert admin_owned >= {'admin_ops_outbox_events', 'admin_ops_inbox_events', 'admin_projection_cursors'}



def test_service_model_registry_stays_explicit_for_split_runtime():
    learning_core_modules = get_service_model_module_names('learning-core-service')
    notes_modules = get_service_model_module_names('notes-service')
    ai_modules = get_service_model_module_names('ai-execution-service')

    assert learning_core_modules[0] == 'service_models.learning_core_models'
    assert 'service_models.eventing_models' in learning_core_modules
    assert 'service_models.identity_models' in learning_core_modules
    assert 'service_models.catalog_content_models' in learning_core_modules
    assert notes_modules[0] == 'service_models.notes_models'
    assert 'service_models.eventing_models' in notes_modules
    assert 'service_models.learning_core_models' in notes_modules
    assert ai_modules[0] == 'service_models.ai_execution_models'
    assert 'service_models.eventing_models' in ai_modules
    assert 'service_models.catalog_content_models' in ai_modules



def test_monolith_bootstrap_resolves_owned_tables_only():
    table_names = {
        table.name
        for table in resolve_monolith_tables(metadata=db.metadata)
    }
    expected = set()
    for service_name in iter_stateful_service_names(include_shadow_only=False):
        expected.update(get_service_owned_table_names(service_name))

    assert table_names == expected
