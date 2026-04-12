from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from platform_sdk.service_migration_plan import (
    get_service_migration_plan,
    iter_service_migration_service_names,
    validate_service_migration_plans,
)


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'describe-service-migration-plan.py'
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location('describe_service_migration_plan', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_service_migration_plan_registry_stays_valid():
    assert validate_service_migration_plans() == []


def test_service_migration_plan_covers_write_owning_services():
    assert iter_service_migration_service_names() == [
        'identity-service',
        'learning-core-service',
        'catalog-content-service',
        'notes-service',
        'ai-execution-service',
        'tts-media-service',
        'asr-service',
        'admin-ops-service',
    ]


def test_service_migration_plan_exposes_unique_baseline_metadata():
    identity_plan = get_service_migration_plan('identity-service')
    ai_plan = get_service_migration_plan('ai-execution-service')

    assert identity_plan.baseline_revision == 'identity_service_0001'
    assert identity_plan.version_table == 'alembic_version_identity_service'
    assert ai_plan.baseline_revision == 'ai_execution_service_0001'
    assert ai_plan.version_table == 'alembic_version_ai_execution_service'
    tts_plan = get_service_migration_plan('tts-media-service')
    asr_plan = get_service_migration_plan('asr-service')
    assert tts_plan.baseline_revision == 'tts_media_service_0001'
    assert tts_plan.version_table == 'alembic_version_tts_media_service'
    assert asr_plan.baseline_revision == 'asr_service_0001'
    assert asr_plan.version_table == 'alembic_version_asr_service'


def test_describe_service_migration_plan_json_output_round_trips(capsys):
    module = _load_script_module()

    original_argv = sys.argv
    try:
        sys.argv = ['describe-service-migration-plan.py', '--service', 'notes-service', '--json']
        exit_code = module.main()
    finally:
        sys.argv = original_argv

    captured = capsys.readouterr().out
    payload = json.loads(captured)

    assert exit_code == 0
    assert payload == [{
        'service_name': 'notes-service',
        'migration_slug': 'notes_service',
        'baseline_revision': 'notes_service_0001',
        'baseline_label': 'notes baseline',
        'version_table': 'alembic_version_notes_service',
        'env_prefix': 'NOTES_SERVICE',
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
    }]
