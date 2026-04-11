from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'validate_notes_export_oss_reference.py'
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location('validate_notes_export_oss_reference', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def get_json(self):
        return self._payload


class _FakeAppContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeApp:
    def app_context(self):
        return _FakeAppContext()


def test_validate_notes_export_reference_reports_success(monkeypatch):
    module = _load_script_module()
    content = '# summary body\n'
    filename = 'ielts_notes_2026-03-30_2026-03-30.md'
    expected_object_key = 'exports/notes-service/user-7/ielts_notes_2026-03-30_2026-03-30.md'
    expected_byte_length = len(content.encode('utf-8'))
    expected_content_type = 'text/markdown; charset=utf-8'

    monkeypatch.setattr(module, 'bucket_is_configured', lambda: True)
    monkeypatch.setattr(module, 'create_notes_flask_app', lambda: _FakeApp())
    monkeypatch.setattr(
        module,
        'export_notes_response',
        lambda user_id, export_args: _FakeResponse({
            'content': content,
            'filename': filename,
            'format': 'md',
            'provider': 'aliyun-oss',
            'object_key': expected_object_key,
            'byte_length': expected_byte_length,
        }),
    )
    monkeypatch.setattr(
        module,
        'resolve_notes_export_metadata',
        lambda **kwargs: SimpleNamespace(
            object_key=expected_object_key,
            byte_length=expected_byte_length,
            content_type=expected_content_type,
        ),
    )
    monkeypatch.setattr(
        module,
        'fetch_notes_export_payload',
        lambda **kwargs: SimpleNamespace(
            object_key=expected_object_key,
            byte_length=expected_byte_length,
            content_type=expected_content_type,
            body=content.encode('utf-8'),
        ),
    )

    report = module.validate_notes_export_reference(
        user_id=7,
        export_args={'start_date': '2026-03-30', 'end_date': '2026-03-30', 'format': 'md', 'type': 'all'},
    )

    assert report.ok is True
    assert report.expected_object_key == expected_object_key
    assert report.errors == ()


def test_validate_notes_export_reference_flags_object_key_drift(monkeypatch):
    module = _load_script_module()
    content = '# summary body\n'
    filename = 'ielts_notes_2026-03-30_2026-03-30.md'
    expected_object_key = 'exports/notes-service/user-7/ielts_notes_2026-03-30_2026-03-30.md'
    wrong_object_key = 'exports/notes-service/user-7/wrong.md'
    expected_byte_length = len(content.encode('utf-8'))
    expected_content_type = 'text/markdown; charset=utf-8'

    monkeypatch.setattr(module, 'bucket_is_configured', lambda: True)
    monkeypatch.setattr(module, 'create_notes_flask_app', lambda: _FakeApp())
    monkeypatch.setattr(
        module,
        'export_notes_response',
        lambda user_id, export_args: _FakeResponse({
            'content': content,
            'filename': filename,
            'format': 'md',
            'provider': 'aliyun-oss',
            'object_key': wrong_object_key,
            'byte_length': expected_byte_length,
        }),
    )
    monkeypatch.setattr(
        module,
        'resolve_notes_export_metadata',
        lambda **kwargs: SimpleNamespace(
            object_key=wrong_object_key,
            byte_length=expected_byte_length,
            content_type=expected_content_type,
        ),
    )
    monkeypatch.setattr(
        module,
        'fetch_notes_export_payload',
        lambda **kwargs: SimpleNamespace(
            object_key=wrong_object_key,
            byte_length=expected_byte_length,
            content_type=expected_content_type,
            body=content.encode('utf-8'),
        ),
    )

    report = module.validate_notes_export_reference(
        user_id=7,
        export_args={'start_date': '2026-03-30', 'end_date': '2026-03-30', 'format': 'md', 'type': 'all'},
    )

    assert report.ok is False
    assert report.expected_object_key == expected_object_key
    assert any('object_key drifted' in error for error in report.errors)


def test_validate_notes_export_payload_reports_body_drift(monkeypatch):
    module = _load_script_module()
    content = '# summary body\n'
    filename = 'ielts_notes_2026-03-30_2026-03-30.md'
    expected_object_key = 'exports/notes-service/user-7/ielts_notes_2026-03-30_2026-03-30.md'
    expected_byte_length = len(content.encode('utf-8'))
    expected_content_type = 'text/markdown; charset=utf-8'

    monkeypatch.setattr(
        module,
        'resolve_notes_export_metadata',
        lambda **kwargs: SimpleNamespace(
            object_key=expected_object_key,
            byte_length=expected_byte_length,
            content_type=expected_content_type,
        ),
    )
    monkeypatch.setattr(
        module,
        'fetch_notes_export_payload',
        lambda **kwargs: SimpleNamespace(
            object_key=expected_object_key,
            byte_length=expected_byte_length,
            content_type=expected_content_type,
            body=b'wrong body',
        ),
    )

    report = module.validate_notes_export_payload(
        user_id=7,
        payload={
            'content': content,
            'filename': filename,
            'format': 'md',
            'provider': 'aliyun-oss',
            'object_key': expected_object_key,
            'byte_length': expected_byte_length,
        },
    )

    assert report.ok is False
    assert any('does not match the exported response content' in error for error in report.errors)


def test_validate_notes_export_script_adds_backend_path_to_sys_path():
    module = _load_script_module()
    assert str(module.BACKEND_PATH) in sys.path
