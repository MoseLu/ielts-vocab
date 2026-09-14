from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / 'scripts' / 'ops' / 'feature-wish-workflow.py'


def load_workflow_module():
    spec = importlib.util.spec_from_file_location('feature_wish_workflow', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_ticket_id_extraction_accepts_supported_trailers():
    module = load_workflow_module()

    text = """
    Fix wrong-word chapter completion drift

    Ticket: feature_wish:42
    Feature-Wish: 43
    Related: feature-wish #42
    Follow-up: feature_wish:44
    """

    assert module.ordered_ticket_ids(text) == ['42', '43', '44']


def test_handoff_keeps_fixed_sop_and_ticket_trailer():
    module = load_workflow_module()

    rendered = module.render_handoff({
        'id': 7,
        'title': '错词本进度异常',
        'content': '错词本 A 章节已完成但仍显示未完成。',
        'status': 'open',
        'username': 'learner',
        'created_at': '2026-06-01T00:00:00',
        'images': [],
    })

    assert 'Ticket: feature_wish:7' in rendered
    assert 'Run focused tests' in rendered
    assert 'Push through normal Git smart HTTP' in rendered
    assert 'Mark the ticket `done` only after production verification passes' in rendered
