from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / 'scripts'
SUPPORT_PATH = SCRIPTS_DIR / 'example_audio_oss_support.py'
VALIDATE_PATH = SCRIPTS_DIR / 'validate_example_audio_oss_parity.py'
BACKFILL_PATH = SCRIPTS_DIR / 'backfill_example_audio_to_oss.py'


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_classify_example_audio_drift_reports_size_mismatch():
    module = _load_module(SUPPORT_PATH, 'test_example_audio_oss_support')

    status = module.classify_example_audio_drift(
        oss_byte_length=800,
        oss_content_type='audio/mpeg',
        expected_content_type='audio/mpeg',
        local_exists=True,
        local_is_valid=True,
        local_byte_length=640,
    )

    assert status == module.SIZE_MISMATCH


def test_classify_example_audio_drift_reports_content_type_mismatch():
    module = _load_module(SUPPORT_PATH, 'test_example_audio_oss_support_content_type')

    status = module.classify_example_audio_drift(
        oss_byte_length=800,
        oss_content_type='application/octet-stream',
        expected_content_type='audio/mpeg',
        local_exists=False,
        local_is_valid=False,
        local_byte_length=None,
    )

    assert status == module.CONTENT_TYPE_MISMATCH


def test_validate_example_audio_oss_parity_returns_nonzero_on_drift(monkeypatch, tmp_path, capsys):
    support_module = _load_module(SUPPORT_PATH, 'test_example_audio_oss_support_validate')
    validate_module = _load_module(VALIDATE_PATH, 'test_validate_example_audio_oss_parity')

    record = support_module.ExampleAudioRecord(
        index=1,
        book_id='book-a',
        sentence='hello',
        model='model-a',
        voice='voice-a',
        cache_file=tmp_path / 'example.mp3',
        object_key='tts-media-service/example-audio/model-a/voice-a/example.mp3',
    )
    drift = support_module.ExampleAudioAuditResult(
        record=record,
        status=support_module.MISSING_IN_OSS,
        local_byte_length=803,
        oss_byte_length=None,
        oss_content_type=None,
    )

    monkeypatch.setattr(validate_module.support.runtime, 'bucket_is_configured', lambda: True)
    monkeypatch.setattr(validate_module.support, 'resolve_book_ids', lambda selected: ['book-a'])
    monkeypatch.setattr(validate_module.support, 'iter_example_audio_audit_results', lambda book_ids: iter([drift]))

    original_argv = sys.argv
    try:
        sys.argv = ['validate_example_audio_oss_parity.py']
        exit_code = validate_module.main()
    finally:
        sys.argv = original_argv

    output = capsys.readouterr().out
    assert exit_code == 1
    assert '[missing_in_oss] tts-media-service/example-audio/model-a/voice-a/example.mp3 book=book-a' in output
    assert 'missing_in_oss: 1' in output


def test_validate_example_audio_oss_parity_reports_content_type_mismatch(monkeypatch, tmp_path, capsys):
    support_module = _load_module(SUPPORT_PATH, 'test_example_audio_oss_support_validate_content_type')
    validate_module = _load_module(VALIDATE_PATH, 'test_validate_example_audio_oss_parity_content_type')

    record = support_module.ExampleAudioRecord(
        index=1,
        book_id='book-a',
        sentence='hello',
        model='model-a',
        voice='voice-a',
        cache_file=tmp_path / 'example.mp3',
        object_key='tts-media-service/example-audio/model-a/voice-a/example.mp3',
    )
    drift = support_module.ExampleAudioAuditResult(
        record=record,
        status=support_module.CONTENT_TYPE_MISMATCH,
        local_byte_length=803,
        oss_byte_length=803,
        oss_content_type='application/octet-stream',
    )

    monkeypatch.setattr(validate_module.support.runtime, 'bucket_is_configured', lambda: True)
    monkeypatch.setattr(validate_module.support, 'resolve_book_ids', lambda selected: ['book-a'])
    monkeypatch.setattr(validate_module.support, 'iter_example_audio_audit_results', lambda book_ids: iter([drift]))

    original_argv = sys.argv
    try:
        sys.argv = ['validate_example_audio_oss_parity.py']
        exit_code = validate_module.main()
    finally:
        sys.argv = original_argv

    output = capsys.readouterr().out
    assert exit_code == 1
    assert 'expected=audio/mpeg oss=application/octet-stream' in output
    assert 'content_type_mismatch: 1' in output


def test_validate_example_audio_oss_parity_ignores_lazy_generation_gaps_by_default(
    monkeypatch,
    tmp_path,
    capsys,
):
    support_module = _load_module(SUPPORT_PATH, 'test_example_audio_oss_support_validate_missing_default')
    validate_module = _load_module(VALIDATE_PATH, 'test_validate_example_audio_oss_parity_missing_default')

    record = support_module.ExampleAudioRecord(
        index=1,
        book_id='book-a',
        sentence='hello',
        model='model-a',
        voice='voice-a',
        cache_file=tmp_path / 'missing-local.mp3',
        object_key='tts-media-service/example-audio/model-a/voice-a/example.mp3',
    )
    missing = support_module.ExampleAudioAuditResult(
        record=record,
        status=support_module.MISSING_EVERYWHERE,
        local_byte_length=None,
        oss_byte_length=None,
        oss_content_type=None,
    )

    monkeypatch.setattr(validate_module.support.runtime, 'bucket_is_configured', lambda: True)
    monkeypatch.setattr(validate_module.support, 'resolve_book_ids', lambda selected: ['book-a'])
    monkeypatch.setattr(validate_module.support, 'iter_example_audio_audit_results', lambda book_ids: iter([missing]))

    original_argv = sys.argv
    try:
        sys.argv = ['validate_example_audio_oss_parity.py']
        exit_code = validate_module.main()
    finally:
        sys.argv = original_argv

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '[missing_everywhere]' not in output
    assert 'missing_everywhere: 1' in output


def test_validate_example_audio_oss_parity_can_require_materialized_examples(
    monkeypatch,
    tmp_path,
    capsys,
):
    support_module = _load_module(SUPPORT_PATH, 'test_example_audio_oss_support_validate_missing_required')
    validate_module = _load_module(VALIDATE_PATH, 'test_validate_example_audio_oss_parity_missing_required')

    record = support_module.ExampleAudioRecord(
        index=1,
        book_id='book-a',
        sentence='hello',
        model='model-a',
        voice='voice-a',
        cache_file=tmp_path / 'missing-local.mp3',
        object_key='tts-media-service/example-audio/model-a/voice-a/example.mp3',
    )
    missing = support_module.ExampleAudioAuditResult(
        record=record,
        status=support_module.MISSING_EVERYWHERE,
        local_byte_length=None,
        oss_byte_length=None,
        oss_content_type=None,
    )

    monkeypatch.setattr(validate_module.support.runtime, 'bucket_is_configured', lambda: True)
    monkeypatch.setattr(validate_module.support, 'resolve_book_ids', lambda selected: ['book-a'])
    monkeypatch.setattr(validate_module.support, 'iter_example_audio_audit_results', lambda book_ids: iter([missing]))

    original_argv = sys.argv
    try:
        sys.argv = ['validate_example_audio_oss_parity.py', '--require-materialized']
        exit_code = validate_module.main()
    finally:
        sys.argv = original_argv

    output = capsys.readouterr().out
    assert exit_code == 1
    assert '[missing_everywhere] tts-media-service/example-audio/model-a/voice-a/example.mp3 book=book-a' in output
    assert 'missing_everywhere: 1' in output


def test_backfill_example_audio_can_dry_run_size_mismatch_repair(monkeypatch, tmp_path, capsys):
    support_module = _load_module(SUPPORT_PATH, 'test_example_audio_oss_support_backfill')
    backfill_module = _load_module(BACKFILL_PATH, 'test_backfill_example_audio_to_oss')

    record = support_module.ExampleAudioRecord(
        index=1,
        book_id='book-a',
        sentence='hello',
        model='model-a',
        voice='voice-a',
        cache_file=tmp_path / 'example.mp3',
        object_key='tts-media-service/example-audio/model-a/voice-a/example.mp3',
    )
    mismatch = support_module.ExampleAudioAuditResult(
        record=record,
        status=support_module.SIZE_MISMATCH,
        local_byte_length=803,
        oss_byte_length=640,
        oss_content_type='audio/mpeg',
    )
    record.cache_file.write_bytes(b'ID3-demo-audio')

    monkeypatch.setattr(backfill_module.support.runtime, 'bucket_is_configured', lambda: True)
    monkeypatch.setattr(backfill_module.support.runtime, 'is_probably_valid_mp3_file', lambda path: True)
    monkeypatch.setattr(backfill_module.support, 'resolve_book_ids', lambda selected: ['book-a'])
    monkeypatch.setattr(backfill_module.support, 'iter_example_audio_audit_results', lambda book_ids: iter([mismatch]))

    original_argv = sys.argv
    try:
        sys.argv = [
            'backfill_example_audio_to_oss.py',
            '--repair-size-mismatch',
            '--dry-run',
        ]
        exit_code = backfill_module.main()
    finally:
        sys.argv = original_argv

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '[dry-run] repair tts-media-service/example-audio/model-a/voice-a/example.mp3' in output
    assert 'would_upload: 1' in output


def test_backfill_example_audio_can_repair_content_type_mismatch_from_oss_payload(
    monkeypatch,
    tmp_path,
    capsys,
):
    support_module = _load_module(SUPPORT_PATH, 'test_example_audio_oss_support_backfill_content_type')
    backfill_module = _load_module(BACKFILL_PATH, 'test_backfill_example_audio_to_oss_content_type')

    record = support_module.ExampleAudioRecord(
        index=1,
        book_id='book-a',
        sentence='hello',
        model='model-a',
        voice='voice-a',
        cache_file=tmp_path / 'missing-local.mp3',
        object_key='tts-media-service/example-audio/model-a/voice-a/example.mp3',
    )
    mismatch = support_module.ExampleAudioAuditResult(
        record=record,
        status=support_module.CONTENT_TYPE_MISMATCH,
        local_byte_length=None,
        oss_byte_length=803,
        oss_content_type='application/octet-stream',
    )

    class Payload:
        body = b'ID3-demo-audio'

    monkeypatch.setattr(backfill_module.support.runtime, 'bucket_is_configured', lambda: True)
    monkeypatch.setattr(backfill_module.support, 'resolve_book_ids', lambda selected: ['book-a'])
    monkeypatch.setattr(backfill_module.support, 'iter_example_audio_audit_results', lambda book_ids: iter([mismatch]))
    monkeypatch.setattr(
        backfill_module.support.runtime,
        'fetch_example_audio_oss_payload',
        lambda sentence, model, voice: Payload(),
    )

    original_argv = sys.argv
    try:
        sys.argv = [
            'backfill_example_audio_to_oss.py',
            '--repair-content-type-mismatch',
            '--dry-run',
        ]
        exit_code = backfill_module.main()
    finally:
        sys.argv = original_argv

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '[dry-run] repair tts-media-service/example-audio/model-a/voice-a/example.mp3 from oss:' in output
    assert 'would_upload: 1' in output


def test_backfill_example_audio_can_generate_missing_objects(monkeypatch, tmp_path, capsys):
    support_module = _load_module(SUPPORT_PATH, 'test_example_audio_oss_support_backfill_generate')
    backfill_module = _load_module(BACKFILL_PATH, 'test_backfill_example_audio_to_oss_generate')

    record = support_module.ExampleAudioRecord(
        index=1,
        book_id='book-a',
        sentence='hello',
        model='model-a',
        voice='voice-a',
        cache_file=tmp_path / 'missing-local.mp3',
        object_key='tts-media-service/example-audio/model-a/voice-a/example.mp3',
    )
    missing = support_module.ExampleAudioAuditResult(
        record=record,
        status=support_module.MISSING_EVERYWHERE,
        local_byte_length=None,
        oss_byte_length=None,
        oss_content_type=None,
    )
    seen: dict[str, tuple[str, str, str]] = {}

    def _synthesize(sentence: str, model: str, voice: str) -> bytes:
        seen['call'] = (sentence, model, voice)
        return b'ID3-demo-audio'

    monkeypatch.setattr(backfill_module.support.runtime, 'bucket_is_configured', lambda: True)
    monkeypatch.setattr(backfill_module.support, 'resolve_book_ids', lambda selected: ['book-a'])
    monkeypatch.setattr(backfill_module.support, 'iter_example_audio_audit_results', lambda book_ids: iter([missing]))
    monkeypatch.setattr(backfill_module.support.runtime, 'synthesize_example_audio', _synthesize)

    original_argv = sys.argv
    try:
        sys.argv = [
            'backfill_example_audio_to_oss.py',
            '--generate-missing',
            '--dry-run',
        ]
        exit_code = backfill_module.main()
    finally:
        sys.argv = original_argv

    output = capsys.readouterr().out
    assert exit_code == 0
    assert seen['call'] == ('hello', 'model-a', 'voice-a')
    assert '[dry-run] generate tts-media-service/example-audio/model-a/voice-a/example.mp3 from generated:' in output
    assert 'would_upload: 1' in output


def test_backfill_example_audio_flags_unrepaired_size_mismatch(monkeypatch, tmp_path, capsys):
    support_module = _load_module(SUPPORT_PATH, 'test_example_audio_oss_support_backfill_mismatch')
    backfill_module = _load_module(BACKFILL_PATH, 'test_backfill_example_audio_to_oss_mismatch')

    record = support_module.ExampleAudioRecord(
        index=1,
        book_id='book-a',
        sentence='hello',
        model='model-a',
        voice='voice-a',
        cache_file=tmp_path / 'example.mp3',
        object_key='tts-media-service/example-audio/model-a/voice-a/example.mp3',
    )
    mismatch = support_module.ExampleAudioAuditResult(
        record=record,
        status=support_module.SIZE_MISMATCH,
        local_byte_length=803,
        oss_byte_length=640,
        oss_content_type='audio/mpeg',
    )

    monkeypatch.setattr(backfill_module.support.runtime, 'bucket_is_configured', lambda: True)
    monkeypatch.setattr(backfill_module.support, 'resolve_book_ids', lambda selected: ['book-a'])
    monkeypatch.setattr(backfill_module.support, 'iter_example_audio_audit_results', lambda book_ids: iter([mismatch]))

    original_argv = sys.argv
    try:
        sys.argv = ['backfill_example_audio_to_oss.py']
        exit_code = backfill_module.main()
    finally:
        sys.argv = original_argv

    output = capsys.readouterr().out
    assert exit_code == 1
    assert '[mismatch] tts-media-service/example-audio/model-a/voice-a/example.mp3 local=803 oss=640' in output
    assert 'size_mismatch: 1' in output
