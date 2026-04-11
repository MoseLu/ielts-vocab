from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'describe-service-table-boundary-audit.py'
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location('describe_service_table_boundary_audit', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_describe_service_table_boundary_audit_service_json_output_round_trips(capsys):
    module = _load_script_module()

    original_argv = sys.argv
    try:
        sys.argv = [
            'describe-service-table-boundary-audit.py',
            '--service',
            'notes-service',
            '--json',
        ]
        exit_code = module.main()
    finally:
        sys.argv = original_argv

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == [{
        'service_name': 'notes-service',
        'owned_tables': [
            'notes_inbox_events',
            'notes_outbox_events',
            'notes_projected_prompt_runs',
            'notes_projected_study_sessions',
            'notes_projected_wrong_words',
            'notes_projection_cursors',
            'user_daily_summaries',
            'user_learning_notes',
            'user_word_notes',
        ],
        'read_only_tables': [
            'custom_books',
            'revoked_tokens',
            'users',
        ],
        'transitional_tables': [
            'learning_core_inbox_events',
            'learning_core_outbox_events',
            'user_added_books',
            'user_book_progress',
            'user_chapter_mode_progress',
            'user_chapter_progress',
            'user_familiar_words',
            'user_favorite_words',
            'user_learning_events',
            'user_progress',
            'user_quick_memory_records',
            'user_smart_word_stats',
            'user_study_sessions',
            'user_wrong_words',
        ],
        'non_owned_tables': [
            'custom_books',
            'learning_core_inbox_events',
            'learning_core_outbox_events',
            'revoked_tokens',
            'user_added_books',
            'user_book_progress',
            'user_chapter_mode_progress',
            'user_chapter_progress',
            'user_familiar_words',
            'user_favorite_words',
            'user_learning_events',
            'user_progress',
            'user_quick_memory_records',
            'user_smart_word_stats',
            'user_study_sessions',
            'user_wrong_words',
            'users',
        ],
        'bootstrap_tables': [
            'custom_books',
            'learning_core_inbox_events',
            'learning_core_outbox_events',
            'notes_inbox_events',
            'notes_outbox_events',
            'notes_projected_prompt_runs',
            'notes_projected_study_sessions',
            'notes_projected_wrong_words',
            'notes_projection_cursors',
            'revoked_tokens',
            'user_added_books',
            'user_book_progress',
            'user_chapter_mode_progress',
            'user_chapter_progress',
            'user_daily_summaries',
            'user_familiar_words',
            'user_favorite_words',
            'user_learning_events',
            'user_learning_notes',
            'user_progress',
            'user_quick_memory_records',
            'user_smart_word_stats',
            'user_study_sessions',
            'user_word_notes',
            'user_wrong_words',
            'users',
        ],
    }]


def test_describe_service_table_boundary_audit_table_json_output_round_trips(capsys):
    module = _load_script_module()

    original_argv = sys.argv
    try:
        sys.argv = [
            'describe-service-table-boundary-audit.py',
            '--view',
            'tables',
            '--table',
            'custom_books',
            '--json',
        ]
        exit_code = module.main()
    finally:
        sys.argv = original_argv

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == [{
        'table_name': 'custom_books',
        'owner_service': 'catalog-content-service',
        'owner_services': ['catalog-content-service'],
        'read_only_services': ['notes-service'],
        'transitional_services': [
            'admin-ops-service',
            'ai-execution-service',
            'learning-core-service',
        ],
    }]
