from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / 'scripts'
SUPPORT_PATH = SCRIPTS_DIR / 'word_audio_oss_support.py'
VALIDATE_PATH = SCRIPTS_DIR / 'validate_word_audio_oss_parity.py'
BACKFILL_PATH = SCRIPTS_DIR / 'backfill_word_audio_to_oss.py'


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_classify_word_audio_drift_reports_size_mismatch():
    module = _load_module(SUPPORT_PATH, 'test_word_audio_oss_support')

    status = module.classify_word_audio_drift(
        oss_byte_length=800,
        oss_content_type='audio/mpeg',
        expected_content_type='audio/mpeg',
        local_exists=True,
        local_is_valid=True,
        local_byte_length=640,
    )

    assert status == module.SIZE_MISMATCH


def test_classify_word_audio_drift_reports_content_type_mismatch():
    module = _load_module(SUPPORT_PATH, 'test_word_audio_oss_support_content_type')

    status = module.classify_word_audio_drift(
        oss_byte_length=800,
        oss_content_type='application/octet-stream',
        expected_content_type='audio/mpeg',
        local_exists=False,
        local_is_valid=False,
        local_byte_length=None,
    )

    assert status == module.CONTENT_TYPE_MISMATCH


def test_validate_word_audio_oss_parity_returns_nonzero_on_drift(monkeypatch, tmp_path, capsys):
    support_module = _load_module(SUPPORT_PATH, 'test_word_audio_oss_support_validate')
    validate_module = _load_module(VALIDATE_PATH, 'test_validate_word_audio_oss_parity')

    record = support_module.WordAudioRecord(
        index=1,
        word='hello',
        normalized_word='hello',
        model='model-a',
        voice='voice-a',
        cache_file=tmp_path / 'example.mp3',
        object_key='projects/ielts-vocab/word-tts-cache/model-a-voice-a/example.mp3',
    )
    drift = support_module.WordAudioAuditResult(
        record=record,
        status=support_module.MISSING_IN_OSS,
        local_byte_length=803,
        oss_byte_length=None,
        oss_content_type=None,
    )

    monkeypatch.setattr(validate_module.support.runtime, '_bucket_signature', lambda: ('a', 'b', 'c', 'd', 'e'))
    monkeypatch.setattr(validate_module.support, 'resolve_book_ids', lambda selected: None)
    monkeypatch.setattr(validate_module.support, 'iter_word_audio_audit_results', lambda book_ids: iter([drift]))

    original_argv = sys.argv
    try:
        sys.argv = ['validate_word_audio_oss_parity.py']
        exit_code = validate_module.main()
    finally:
        sys.argv = original_argv

    output = capsys.readouterr().out
    assert exit_code == 1
    assert '[missing_in_oss] projects/ielts-vocab/word-tts-cache/model-a-voice-a/example.mp3 word=hello' in output
    assert 'missing_in_oss: 1' in output


def test_validate_word_audio_oss_parity_reports_content_type_mismatch(monkeypatch, tmp_path, capsys):
    support_module = _load_module(SUPPORT_PATH, 'test_word_audio_oss_support_validate_content_type')
    validate_module = _load_module(VALIDATE_PATH, 'test_validate_word_audio_oss_parity_content_type')

    record = support_module.WordAudioRecord(
        index=1,
        word='hello',
        normalized_word='hello',
        model='model-a',
        voice='voice-a',
        cache_file=tmp_path / 'example.mp3',
        object_key='projects/ielts-vocab/word-tts-cache/model-a-voice-a/example.mp3',
    )
    drift = support_module.WordAudioAuditResult(
        record=record,
        status=support_module.CONTENT_TYPE_MISMATCH,
        local_byte_length=803,
        oss_byte_length=803,
        oss_content_type='application/octet-stream',
    )

    monkeypatch.setattr(validate_module.support.runtime, '_bucket_signature', lambda: ('a', 'b', 'c', 'd', 'e'))
    monkeypatch.setattr(validate_module.support, 'resolve_book_ids', lambda selected: None)
    monkeypatch.setattr(validate_module.support, 'iter_word_audio_audit_results', lambda book_ids: iter([drift]))

    original_argv = sys.argv
    try:
        sys.argv = ['validate_word_audio_oss_parity.py']
        exit_code = validate_module.main()
    finally:
        sys.argv = original_argv

    output = capsys.readouterr().out
    assert exit_code == 1
    assert 'expected=audio/mpeg oss=application/octet-stream' in output
    assert 'content_type_mismatch: 1' in output


def test_backfill_word_audio_can_dry_run_missing_upload(monkeypatch, tmp_path, capsys):
    support_module = _load_module(SUPPORT_PATH, 'test_word_audio_oss_support_backfill')
    backfill_module = _load_module(BACKFILL_PATH, 'test_backfill_word_audio_to_oss')

    cache_file = tmp_path / 'example.mp3'
    cache_file.write_bytes(b'ID3-demo-audio')
    record = support_module.WordAudioRecord(
        index=1,
        word='hello',
        normalized_word='hello',
        model='model-a',
        voice='voice-a',
        cache_file=cache_file,
        object_key='projects/ielts-vocab/word-tts-cache/model-a-voice-a/example.mp3',
    )
    drift = support_module.WordAudioAuditResult(
        record=record,
        status=support_module.MISSING_IN_OSS,
        local_byte_length=803,
        oss_byte_length=None,
        oss_content_type=None,
    )

    monkeypatch.setattr(backfill_module.support.runtime, '_bucket_signature', lambda: ('a', 'b', 'c', 'd', 'e'))
    monkeypatch.setattr(backfill_module.support, 'resolve_book_ids', lambda selected: None)
    monkeypatch.setattr(backfill_module.support, 'iter_word_audio_audit_results', lambda book_ids: iter([drift]))
    monkeypatch.setattr(backfill_module.support, 'is_probably_valid_mp3_file', lambda path: True)

    original_argv = sys.argv
    try:
        sys.argv = ['backfill_word_audio_to_oss.py', '--dry-run']
        exit_code = backfill_module.main()
    finally:
        sys.argv = original_argv

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '[dry-run] upload projects/ielts-vocab/word-tts-cache/model-a-voice-a/example.mp3' in output
    assert 'would_upload: 1' in output


def test_backfill_word_audio_can_repair_content_type_mismatch_from_oss_payload(monkeypatch, tmp_path, capsys):
    support_module = _load_module(SUPPORT_PATH, 'test_word_audio_oss_support_backfill_content_type')
    backfill_module = _load_module(BACKFILL_PATH, 'test_backfill_word_audio_to_oss_content_type')

    record = support_module.WordAudioRecord(
        index=1,
        word='hello',
        normalized_word='hello',
        model='model-a',
        voice='voice-a',
        cache_file=tmp_path / 'missing-local.mp3',
        object_key='projects/ielts-vocab/word-tts-cache/model-a-voice-a/example.mp3',
    )
    mismatch = support_module.WordAudioAuditResult(
        record=record,
        status=support_module.CONTENT_TYPE_MISMATCH,
        local_byte_length=None,
        oss_byte_length=803,
        oss_content_type='application/octet-stream',
    )

    class Payload:
        body = b'ID3-demo-audio'

    monkeypatch.setattr(backfill_module.support.runtime, '_bucket_signature', lambda: ('a', 'b', 'c', 'd', 'e'))
    monkeypatch.setattr(backfill_module.support, 'resolve_book_ids', lambda selected: None)
    monkeypatch.setattr(backfill_module.support, 'iter_word_audio_audit_results', lambda book_ids: iter([mismatch]))
    monkeypatch.setattr(
        backfill_module.support.runtime,
        'fetch_word_audio_oss_payload',
        lambda **kwargs: Payload(),
    )

    original_argv = sys.argv
    try:
        sys.argv = [
            'backfill_word_audio_to_oss.py',
            '--repair-content-type-mismatch',
            '--dry-run',
        ]
        exit_code = backfill_module.main()
    finally:
        sys.argv = original_argv

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '[dry-run] repair projects/ielts-vocab/word-tts-cache/model-a-voice-a/example.mp3 from oss:' in output
    assert 'would_upload: 1' in output
