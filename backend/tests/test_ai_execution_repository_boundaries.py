from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
FORBIDDEN_IMPORT_SNIPPETS = (
    'services.learning_note_repository',
    'services.learning_stats_repository',
    'services.quick_memory_record_repository',
    'services.learning_event_repository',
    'services.learner_profile_repository',
    'services.learner_profile import build_learner_profile',
)
AI_BOUNDARY_FILES = (
    BACKEND_ROOT / 'services' / 'ai_assistant_ask_service.py',
    BACKEND_ROOT / 'services' / 'ai_assistant_tool_service.py',
    BACKEND_ROOT / 'services' / 'ai_context_service.py',
    BACKEND_ROOT / 'services' / 'ai_learning_summary_service.py',
    BACKEND_ROOT / 'services' / 'ai_metric_tracking_service.py',
    BACKEND_ROOT / 'services' / 'ai_practice_support_service.py',
    BACKEND_ROOT / 'services' / 'ai_related_notes_service.py',
    BACKEND_ROOT / 'services' / 'ai_route_support_service.py',
    BACKEND_ROOT / 'services' / 'ai_practice_support_service_parts' / 'speaking_and_plans.py',
)
PLATFORM_AI_BOUNDARY_FILES = {
    PROJECT_ROOT / 'packages' / 'platform-sdk' / 'platform_sdk' / 'ai_assistant_application.py': (
        'platform_sdk.notes_repository_adapters',
        'platform_sdk.learning_repository_adapters',
    ),
    PROJECT_ROOT / 'packages' / 'platform-sdk' / 'platform_sdk' / 'ai_related_notes_support.py': (
        'platform_sdk.notes_repository_adapters',
        'platform_sdk.ai_repository_adapters import learner_profile_repository',
    ),
    PROJECT_ROOT / 'packages' / 'platform-sdk' / 'platform_sdk' / 'ai_custom_books_application.py': (
        'platform_sdk.ai_repository_adapters',
    ),
    PROJECT_ROOT / 'packages' / 'platform-sdk' / 'platform_sdk' / 'ai_assistant_tool_support.py': (
        'platform_sdk.learning_repository_adapters',
    ),
    PROJECT_ROOT / 'packages' / 'platform-sdk' / 'platform_sdk' / 'ai_learning_stats_application.py': (
        'platform_sdk.study_session_repository_adapter',
    ),
    PROJECT_ROOT / 'packages' / 'platform-sdk' / 'platform_sdk' / 'ai_metric_support.py': (
        'platform_sdk.learning_repository_adapters',
    ),
    PROJECT_ROOT / 'packages' / 'platform-sdk' / 'platform_sdk' / 'ai_progress_sync_application.py': (
        'platform_sdk.learning_repository_adapters',
        'platform_sdk.learning_event_support',
        'platform_sdk.ai_repository_adapters',
    ),
    PROJECT_ROOT / 'packages' / 'platform-sdk' / 'platform_sdk' / 'ai_wrong_words_application.py': (
        'platform_sdk.learning_repository_adapters',
        'platform_sdk.learning_event_support',
        'platform_sdk.ai_repository_adapters',
    ),
    PROJECT_ROOT / 'packages' / 'platform-sdk' / 'platform_sdk' / 'ai_practice_speaking_application.py': (
        'platform_sdk.learning_repository_adapters',
        'platform_sdk.learning_event_support',
    ),
    PROJECT_ROOT / 'packages' / 'platform-sdk' / 'platform_sdk' / 'ai_assistant_application.py': (
        'platform_sdk.learning_event_support',
    ),
    PROJECT_ROOT / 'packages' / 'platform-sdk' / 'platform_sdk' / 'ai_session_application.py': (
        'platform_sdk.learning_event_support',
        'platform_sdk.learning_repository_adapters',
        'platform_sdk.study_session_repository_adapter',
    ),
}


def test_ai_execution_application_modules_use_platform_adapters_for_cross_service_reads():
    for path in AI_BOUNDARY_FILES:
        content = path.read_text(encoding='utf-8')
        for snippet in FORBIDDEN_IMPORT_SNIPPETS:
            assert snippet not in content, f'{path.name} still imports {snippet}'


def test_platform_ai_execution_modules_use_internal_clients_for_notes_reads_and_writes():
    for path, snippets in PLATFORM_AI_BOUNDARY_FILES.items():
        content = path.read_text(encoding='utf-8')
        for snippet in snippets:
            assert snippet not in content, f'{path.name} still imports {snippet}'
