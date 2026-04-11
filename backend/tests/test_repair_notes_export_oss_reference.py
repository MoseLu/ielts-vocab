from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'repair_notes_export_oss_reference.py'
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location('repair_notes_export_oss_reference', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_repair_notes_export_reference_replays_export_and_revalidates(monkeypatch):
    module = _load_script_module()
    payload = {
        'content': '# summary body\n',
        'filename': 'ielts_notes_2026-03-30_2026-03-30.md',
        'format': 'md',
        'provider': 'aliyun-oss',
        'object_key': 'exports/notes-service/user-7/ielts_notes_2026-03-30_2026-03-30.md',
        'byte_length': 15,
    }
    report = module.validate.NotesExportValidationReport(
        filename=payload['filename'],
        expected_object_key=payload['object_key'],
        payload_object_key=payload['object_key'],
        payload_byte_length=payload['byte_length'],
        metadata_byte_length=payload['byte_length'],
        fetched_byte_length=payload['byte_length'],
        content_type='text/markdown; charset=utf-8',
        errors=(),
    )
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(module.validate, 'bucket_is_configured', lambda: True)
    monkeypatch.setattr(
        module.validate,
        'generate_notes_export_payload',
        lambda **kwargs: calls.append(('generate', kwargs)) or payload,
    )
    monkeypatch.setattr(
        module.validate,
        'validate_notes_export_payload',
        lambda **kwargs: calls.append(('validate', kwargs)) or report,
    )

    result = module.repair_notes_export_reference(
        user_id=7,
        export_args={'start_date': '2026-03-30', 'end_date': '2026-03-30', 'format': 'md', 'type': 'all'},
    )

    assert result.ok is True
    assert calls == [
        (
            'generate',
            {
                'user_id': 7,
                'export_args': {
                    'start_date': '2026-03-30',
                    'end_date': '2026-03-30',
                    'format': 'md',
                    'type': 'all',
                },
            },
        ),
        (
            'validate',
            {
                'user_id': 7,
                'payload': payload,
            },
        ),
    ]


def test_repair_notes_export_reference_requires_bucket(monkeypatch):
    module = _load_script_module()

    monkeypatch.setattr(module.validate, 'bucket_is_configured', lambda: False)

    try:
        module.repair_notes_export_reference(user_id=7, export_args={'format': 'md', 'type': 'all'})
    except RuntimeError as exc:
        assert 'Aliyun OSS is not configured for notes-service.' in str(exc)
    else:
        raise AssertionError('Expected repair_notes_export_reference to raise when OSS is not configured')
