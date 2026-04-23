import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def _top_level_import_sources(relative_path: str) -> set[str]:
    source = _read(relative_path)
    tree = ast.parse(source)
    imports: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_learning_core_service_no_longer_warms_quick_memory_on_startup():
    source = _read('services/learning-core-service/main.py')

    assert 'get_quick_memory_vocab_lookup' not in source


def test_catalog_content_runtime_no_longer_primes_search_catalog_on_startup():
    source = _read('packages/platform-sdk/platform_sdk/catalog_content_runtime.py')

    assert 'prime_global_word_search_catalog' not in source


def test_ai_dependency_probe_support_loads_lazily():
    source = _read('services/ai-execution-service/main.py')
    imports = _top_level_import_sources('services/ai-execution-service/main.py')

    assert 'def _load_ai_dependency_probe_support()' in source
    assert 'platform_sdk.learner_profile_application_support' not in imports
    assert 'platform_sdk.learning_core_quick_memory_read_adapter' not in imports
    assert 'platform_sdk.learning_core_internal_client' not in imports


def test_service_app_keeps_fastapi_imports_lazy_for_starlette_shell_services():
    imports = _top_level_import_sources('packages/platform-sdk/platform_sdk/service_app.py')

    assert 'fastapi' not in imports
    assert 'fastapi.responses' not in imports


def test_tts_follow_read_and_materialization_support_loads_lazily():
    source = _read('services/tts-media-service/main.py')
    imports = _top_level_import_sources('services/tts-media-service/main.py')

    assert 'def _load_follow_read_support()' in source
    assert 'services.follow_read_timeline_service' not in imports
    assert 'platform_sdk.tts_media_event_application' not in imports


def test_admin_transport_loads_heavy_application_support_lazily():
    source = _read('packages/platform-sdk/platform_sdk/admin_ops_transport.py')
    imports = _top_level_import_sources('packages/platform-sdk/platform_sdk/admin_ops_transport.py')

    assert 'def _load_admin_overview_support()' in source
    assert 'def _load_admin_user_management_support()' in source
    assert 'def _load_word_feedback_support()' in source
    assert 'platform_sdk.admin_overview_application' not in imports
    assert 'platform_sdk.admin_user_management_application' not in imports
    assert 'platform_sdk.admin_word_feedback_application' not in imports


def test_exam_transport_loads_exam_application_lazily():
    source = _read('packages/platform-sdk/platform_sdk/exam_transport.py')
    imports = _top_level_import_sources('packages/platform-sdk/platform_sdk/exam_transport.py')

    assert 'def _load_exam_application_support()' in source
    assert 'platform_sdk.exam_application' not in imports


def test_notes_transport_loads_summary_and_query_support_lazily():
    source = _read('packages/platform-sdk/platform_sdk/notes_transport.py')
    imports = _top_level_import_sources('packages/platform-sdk/platform_sdk/notes_transport.py')

    assert 'def _load_notes_internal_support()' in source
    assert 'def _load_notes_query_support()' in source
    assert 'def _load_notes_summary_job_support()' in source
    assert 'platform_sdk.notes_internal_application' not in imports
    assert 'platform_sdk.notes_query_application' not in imports
    assert 'platform_sdk.notes_summary_jobs_application' not in imports
    assert 'platform_sdk.notes_word_notes_application' not in imports


def test_ai_shared_route_shell_no_longer_imports_ai_route_support_service():
    source = _read('backend/routes/ai_routes/shared/learning_metrics.py')
    imports = _top_level_import_sources('backend/routes/ai_routes/shared/learning_metrics.py')

    assert "ai_bp = Blueprint('ai', __name__)" in source
    assert 'services.ai_route_support_service' not in imports


def test_ai_assistant_routes_load_heavy_support_lazily():
    ask_source = _read('backend/routes/ai_routes/assistant/ask_and_custom_books.py')
    ask_imports = _top_level_import_sources('backend/routes/ai_routes/assistant/ask_and_custom_books.py')
    practice_source = _read('backend/routes/ai_routes/assistant/practice_support.py')
    practice_imports = _top_level_import_sources('backend/routes/ai_routes/assistant/practice_support.py')

    assert 'def _load_ask_route_support()' in ask_source
    assert 'def _load_custom_book_route_support()' in ask_source
    assert 'services.ai_assistant_ask_service' not in ask_imports
    assert 'services.ai_custom_books_service' not in ask_imports
    assert 'def _load_ai_practice_route_support()' in practice_source
    assert 'def _load_ai_speaking_route_support()' in practice_source
    assert 'services.ai_practice_support_service' not in practice_imports
    assert 'platform_sdk.ai_speaking_assessment_application' not in practice_imports


def test_ai_profile_and_progress_routes_load_support_lazily():
    profile_source = _read('backend/routes/ai_routes/profile/context_and_profile.py')
    profile_imports = _top_level_import_sources('backend/routes/ai_routes/profile/context_and_profile.py')
    similar_source = _read('backend/routes/ai_routes/practice/similar_words.py')
    similar_imports = _top_level_import_sources('backend/routes/ai_routes/practice/similar_words.py')
    stats_source = _read('backend/routes/ai_routes/progress/learning_stats_and_session_start.py')
    stats_imports = _top_level_import_sources('backend/routes/ai_routes/progress/learning_stats_and_session_start.py')
    session_source = _read('backend/routes/ai_routes/progress/session_logging_and_quick_memory.py')
    session_imports = _top_level_import_sources('backend/routes/ai_routes/progress/session_logging_and_quick_memory.py')
    sync_source = _read('backend/routes/ai_routes/progress/sync_endpoints.py')
    sync_imports = _top_level_import_sources('backend/routes/ai_routes/progress/sync_endpoints.py')
    wrong_words_source = _read('backend/routes/ai_routes/progress/wrong_words.py')
    wrong_words_imports = _top_level_import_sources('backend/routes/ai_routes/progress/wrong_words.py')

    assert 'def _load_context_route_support()' in profile_source
    assert 'def _load_profile_route_support()' in profile_source
    assert 'services.ai_context_service' not in profile_imports
    assert 'platform_sdk.ai_home_todo_application' not in profile_imports
    assert 'platform_sdk.learner_profile_builder_adapter' not in profile_imports
    assert 'def _load_similarity_route_support()' in similar_source
    assert 'platform_sdk.ai_similarity_application' not in similar_imports
    assert 'services.listening_confusables' not in similar_imports
    assert 'def _load_learning_stats_route_support()' in stats_source
    assert 'def _load_session_start_route_support()' in stats_source
    assert 'services.learning_stats_service' not in stats_imports
    assert 'services.study_sessions' not in stats_imports
    assert 'def _load_session_logging_route_support()' in session_source
    assert 'def _load_quick_memory_route_support()' in session_source
    assert 'services.session_logging_service' not in session_imports
    assert 'services.quick_memory_review_queue_service' not in session_imports
    assert 'def _load_sync_endpoint_support()' in sync_source
    assert 'services.ai_progress_sync_service' not in sync_imports
    assert 'def _load_wrong_word_route_support()' in wrong_words_source
    assert 'services.ai_wrong_words_service' not in wrong_words_imports
