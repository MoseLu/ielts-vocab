from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'describe-monolith-route-coverage.py'
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location('describe_monolith_route_coverage', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_route_path_normalization_and_coverage_matching():
    module = _load_script_module()

    assert module.normalize_route_path('/api/progress/<int:day>') == '/api/progress/{param}'
    assert module.normalize_route_path('/api/admin/{admin_path:path}') == '/api/admin/{path...}'
    assert module.route_pattern_covers('/api/auth/{auth_path:path}', '/api/auth/login')
    assert module.route_pattern_covers('/api/progress/{day}', '/api/progress/<int:day>')
    assert not module.route_pattern_covers('/api/books/stats', '/api/books/<book_id>')
    assert not module.route_pattern_covers('/api/tts/example-audio', '/api/tts/<path:asset_path>')


def test_describe_monolith_route_coverage_json_output_round_trips(capsys):
    module = _load_script_module()

    original_argv = sys.argv
    try:
        sys.argv = [
            'describe-monolith-route-coverage.py',
            '--group',
            'auth',
            '--group',
            'tts',
            '--json',
        ]
        exit_code = module.main()
    finally:
        sys.argv = original_argv

    payload = json.loads(capsys.readouterr().out)
    summary = payload['summary']
    route_groups = payload['route_groups']

    assert exit_code == 0
    assert summary['selected_surface'] == 'browser'
    assert summary['selected_route_groups'] == ['auth', 'tts']
    assert [group['name'] for group in route_groups] == ['auth', 'tts']
    assert summary['monolith_route_method_count'] == sum(
        group['monolith_route_method_count']
        for group in route_groups
    )
    assert summary['covered_monolith_route_method_count'] == sum(
        group['covered_monolith_route_method_count']
        for group in route_groups
    )
    assert summary['gateway_only_route_method_count'] == len(payload['gateway_only_route_methods'])
    assert route_groups[0]['covered_monolith_route_method_count'] > 0
    assert route_groups[1]['gateway_route_method_count'] > 0


def test_wave6c_browser_route_coverage_contract_has_no_uncovered_groups_by_default():
    module = _load_script_module()

    payload = module.describe_monolith_route_coverage()
    uncovered = {
        group['name']: sorted(
            f"{record['method']} {record['normalized_path']}"
            for record in group['monolith_only_route_methods']
        )
        for group in payload['route_groups']
        if group['monolith_only_route_methods']
    }

    assert payload['summary']['selected_surface'] == 'browser'
    assert uncovered == {}


def test_wave6c_route_coverage_contract_marks_only_tts_admin_as_rollback_gap():
    module = _load_script_module()

    payload = module.describe_monolith_route_coverage(surface='all')
    uncovered = {
        group['name']: sorted(
            f"{record['method']} {record['normalized_path']}"
            for record in group['monolith_only_route_methods']
        )
        for group in payload['route_groups']
        if group['monolith_only_route_methods']
    }

    assert payload['summary']['selected_surface'] == 'all'
    assert uncovered == {
        'tts-admin': [
            'GET /api/tts/admin/word-audio-status',
            'GET /api/tts/books-summary',
            'GET /api/tts/status/{param}',
            'POST /api/tts/admin/generate-words',
            'POST /api/tts/generate/{param}',
        ],
    }
