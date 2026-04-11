from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from platform_sdk.service_storage_boundary_plan import (
    get_service_storage_boundary_plan,
    iter_guarded_split_service_names,
    validate_service_storage_boundary_plans,
)


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'describe-service-storage-boundary-plan.py'
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location('describe_service_storage_boundary_plan', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_service_storage_boundary_plan_registry_stays_valid():
    assert validate_service_storage_boundary_plans() == []


def test_service_storage_boundary_plan_covers_all_guarded_split_services():
    assert iter_guarded_split_service_names() == [
        'identity-service',
        'learning-core-service',
        'catalog-content-service',
        'ai-execution-service',
        'notes-service',
        'tts-media-service',
        'asr-service',
        'admin-ops-service',
    ]


def test_service_storage_boundary_plan_exposes_admin_projection_scope():
    admin_plan = get_service_storage_boundary_plan('admin-ops-service')

    assert admin_plan.primary_storage_kind == 'postgresql'
    assert admin_plan.boundary_scope == 'eventing-and-projections'
    assert admin_plan.shared_sqlite_fallback_locked is True
    assert admin_plan.service_override_env == 'ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES'
    assert admin_plan.global_override_env == 'ALLOW_SHARED_SPLIT_SERVICE_SQLITE'


def test_describe_service_storage_boundary_plan_json_output_round_trips(capsys):
    module = _load_script_module()

    original_argv = sys.argv
    try:
        sys.argv = [
            'describe-service-storage-boundary-plan.py',
            '--service',
            'tts-media-service',
            '--json',
        ]
        exit_code = module.main()
    finally:
        sys.argv = original_argv

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == [{
        'service_name': 'tts-media-service',
        'primary_storage_kind': 'postgresql',
        'boundary_scope': 'service-eventing',
        'shared_sqlite_fallback_locked': True,
        'allow_service_local_sqlite': True,
        'service_override_env': 'ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES',
        'global_override_env': 'ALLOW_SHARED_SPLIT_SERVICE_SQLITE',
        'owned_tables': [
            'tts_media_assets',
            'tts_media_inbox_events',
            'tts_media_outbox_events',
        ],
    }]
