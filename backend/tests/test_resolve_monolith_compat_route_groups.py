from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'resolve-monolith-compat-route-groups.py'
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location('resolve_monolith_compat_route_groups', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_resolve_monolith_compat_route_groups_script_resolves_rollback_surface(capsys):
    module = _load_script_module()

    original_argv = sys.argv
    try:
        sys.argv = [
            'resolve-monolith-compat-route-groups.py',
            '--surface',
            'rollback',
            '--json',
        ]
        exit_code = module.main()
    finally:
        sys.argv = original_argv

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        'surface': 'rollback',
        'route_groups': ['tts-admin'],
        'probe_path': '/api/tts/books-summary',
    }


def test_resolve_monolith_compat_route_groups_script_plain_output_is_csv(capsys):
    module = _load_script_module()

    original_argv = sys.argv
    try:
        sys.argv = [
            'resolve-monolith-compat-route-groups.py',
            '--surface',
            'browser',
        ]
        exit_code = module.main()
    finally:
        sys.argv = original_argv

    output = capsys.readouterr().out.strip()

    assert exit_code == 0
    assert output == 'auth,progress,vocabulary,speech,books,ai,notes,tts,admin'


def test_resolve_monolith_compat_route_groups_script_accepts_explicit_route_groups(capsys):
    module = _load_script_module()

    original_argv = sys.argv
    try:
        sys.argv = [
            'resolve-monolith-compat-route-groups.py',
            '--surface',
            'all',
            '--route-groups',
            'tts-admin,auth',
            '--json',
        ]
        exit_code = module.main()
    finally:
        sys.argv = original_argv

    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload == {
        'surface': 'all',
        'route_groups': ['auth', 'tts-admin'],
        'probe_path': '/api/auth/me',
    }
