#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / 'backend'
SDK_ROOT = REPO_ROOT / 'packages' / 'platform-sdk'
for candidate in (BACKEND_ROOT, SDK_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from dotenv import load_dotenv  # noqa: E402
from platform_sdk.storage import aliyun_oss as shared_oss  # noqa: E402
from platform_sdk.word_audio_cache_profiles import CURRENT_WORD_CACHE_TAG  # noqa: E402
from services.word_tts import (  # noqa: E402
    azure_default_model,
    azure_word_voice,
    is_azure_tts_phonetic_safe,
    is_probably_valid_mp3_file,
    normalize_word_key,
    synthesize_word_to_bytes,
    word_tts_cache_path,
    word_tts_data_dir,
)
from services.word_tts_oss import (  # noqa: E402
    DEFAULT_WORD_AUDIO_CONTENT_TYPE,
    word_audio_oss_object_key,
)


load_dotenv(BACKEND_ROOT / '.env')


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Regenerate and upload Azure word TTS for phonetic audit rerun-list entries.',
    )
    parser.add_argument('--rerun-list', required=True)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--output', default='')
    parser.add_argument('--voice', default='')
    parser.add_argument('--oss-timeout', type=int, default=60)
    parser.add_argument('--synth-retries', type=int, default=4)
    parser.add_argument('--retry-delay', type=float, default=1.5)
    parser.add_argument('--force-upload', action='store_true')
    return parser


def _cache_model_for_phonetic(request_model: str, phonetic: str) -> str:
    digest = hashlib.md5(f'ipa:{phonetic}'.encode('utf-8')).hexdigest()[:8]
    return f'{request_model}@{CURRENT_WORD_CACHE_TAG}@ipa-{digest}'


def _default_output_path(rerun_list: Path) -> Path:
    timestamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    return rerun_list.parent / f'tts-rerun-{timestamp}.json'


def _load_entries(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(payload, list):
        raise ValueError('rerun-list must be a JSON array')
    return [entry for entry in payload if str(entry.get('word') or '').strip()]


def _verify_required_env() -> None:
    missing = [
        key for key in (
            'AZURE_SPEECH_KEY',
            'AZURE_SPEECH_REGION',
            'AXI_ALIYUN_OSS_ACCESS_KEY_ID',
            'AXI_ALIYUN_OSS_ACCESS_KEY_SECRET',
            'AXI_ALIYUN_OSS_PRIVATE_BUCKET',
            'AXI_ALIYUN_OSS_REGION',
        )
        if not os.environ.get(key, '').strip()
    ]
    if missing:
        raise RuntimeError(f'Missing required env: {", ".join(missing)}')


def _build_oss_bucket(timeout_seconds: int):
    signature = shared_oss.bucket_signature_from_env()
    if signature is None:
        return None
    access_key_id, access_key_secret, bucket_name, region, endpoint = signature
    security_token = (os.environ.get('AXI_ALIYUN_OSS_STS_TOKEN') or '').strip()
    auth = (
        shared_oss.oss2.StsAuth(access_key_id, access_key_secret, security_token, auth_version='v4')
        if security_token
        else shared_oss.oss2.AuthV4(access_key_id, access_key_secret)
    )
    return shared_oss.oss2.Bucket(
        auth,
        shared_oss.build_endpoint(region, endpoint),
        bucket_name,
        region=shared_oss.normalize_bucket_region(region),
        connect_timeout=max(1, timeout_seconds),
    )


def _upload_and_fetch(*, file_name: str, model: str, voice: str, audio: bytes, bucket):
    object_key = word_audio_oss_object_key(file_name=file_name, model=model, voice=voice)
    metadata = shared_oss.put_object_bytes(
        object_key=object_key,
        body=audio,
        content_type=DEFAULT_WORD_AUDIO_CONTENT_TYPE,
        bucket=bucket,
    )
    payload = shared_oss.fetch_object_payload(
        object_key=object_key,
        file_name=file_name,
        bucket=bucket,
    )
    return metadata, payload


def _synthesize_with_retries(
    *,
    word: str,
    request_model: str,
    voice: str,
    phonetic: str,
    max_attempts: int,
    retry_delay: float,
) -> bytes:
    attempts = max(1, max_attempts)
    for attempt in range(1, attempts + 1):
        try:
            return synthesize_word_to_bytes(
                word,
                request_model,
                voice,
                provider='azure',
                content_mode='word',
                phonetic=phonetic,
            )
        except Exception:
            if attempt >= attempts:
                raise
            time.sleep(max(0.0, retry_delay) * attempt)
    raise RuntimeError('unreachable synthesis retry state')


def _success_from_payload(
    *,
    status: str,
    word: str,
    phonetic: str,
    model: str,
    voice: str,
    cache_file: Path,
    payload,
) -> dict:
    return {
        'word': word,
        'phonetic': phonetic,
        'status': status,
        'model': model,
        'voice': voice,
        'cache_file': str(cache_file),
        'object_key': payload.object_key,
        'byte_length': payload.byte_length,
        'sha256': hashlib.sha256(payload.body).hexdigest(),
    }


def _process_entry(
    entry: dict,
    *,
    request_model: str,
    voice: str,
    dry_run: bool,
    bucket,
    force_upload: bool,
    synth_retries: int,
    retry_delay: float,
) -> dict:
    word = str(entry.get('word') or '').strip()
    phonetic = str(entry.get('new_phonetic') or '').strip()
    if not is_azure_tts_phonetic_safe(phonetic):
        return {'word': word, 'phonetic': phonetic, 'status': 'skipped_unsafe'}

    model = _cache_model_for_phonetic(request_model, phonetic)
    cache_file = word_tts_cache_path(word_tts_data_dir(), normalize_word_key(word), model, voice)
    object_key = word_audio_oss_object_key(file_name=cache_file.name, model=model, voice=voice)
    if dry_run:
        return {
            'word': word,
            'phonetic': phonetic,
            'status': 'dry_run',
            'model': model,
            'voice': voice,
            'cache_file': str(cache_file),
        }

    if not force_upload:
        payload = shared_oss.fetch_object_payload(
            object_key=object_key,
            file_name=cache_file.name,
            bucket=bucket,
        )
        if payload is not None:
            return _success_from_payload(
                status='already_uploaded',
                word=word,
                phonetic=phonetic,
                model=model,
                voice=voice,
                cache_file=cache_file,
                payload=payload,
            )

    if cache_file.exists() and is_probably_valid_mp3_file(cache_file):
        audio = cache_file.read_bytes()
    else:
        try:
            audio = _synthesize_with_retries(
                word=word,
                request_model=request_model,
                voice=voice,
                phonetic=phonetic,
                max_attempts=synth_retries,
                retry_delay=retry_delay,
            )
        except Exception as exc:
            return {
                'word': word,
                'phonetic': phonetic,
                'status': 'synthesize_failed',
                'error': f'{exc.__class__.__name__}: {exc}',
            }
        cache_file.write_bytes(audio)
    if not is_probably_valid_mp3_file(cache_file):
        return {'word': word, 'phonetic': phonetic, 'status': 'invalid_mp3'}

    try:
        metadata, payload = _upload_and_fetch(
            file_name=cache_file.name,
            model=model,
            voice=voice,
            audio=audio,
            bucket=bucket,
        )
    except Exception as exc:
        return {
            'word': word,
            'phonetic': phonetic,
            'status': 'upload_exception',
            'model': model,
            'voice': voice,
            'cache_file': str(cache_file),
            'object_key': object_key,
            'error': f'{exc.__class__.__name__}: {exc}',
        }
    if metadata is None or payload is None:
        return {'word': word, 'phonetic': phonetic, 'status': 'upload_failed'}
    return _success_from_payload(
        status='uploaded',
        word=word,
        phonetic=phonetic,
        model=model,
        voice=voice,
        cache_file=cache_file,
        payload=payload,
    )


def _write_results(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if not args.dry_run:
        _verify_required_env()
    rerun_list = Path(args.rerun_list).resolve()
    entries = _load_entries(rerun_list)
    if args.limit > 0:
        entries = entries[:args.limit]

    request_model = azure_default_model()
    voice = (args.voice or azure_word_voice()).strip() or azure_word_voice()
    bucket = None if args.dry_run else _build_oss_bucket(args.oss_timeout)
    if not args.dry_run and bucket is None:
        raise RuntimeError('Missing required OSS bucket configuration')
    output_path = Path(args.output).resolve() if args.output else _default_output_path(rerun_list)
    results = []
    for index, entry in enumerate(entries, start=1):
        result = _process_entry(
            entry,
            request_model=request_model,
            voice=voice,
            dry_run=args.dry_run,
            bucket=bucket,
            force_upload=args.force_upload,
            synth_retries=args.synth_retries,
            retry_delay=args.retry_delay,
        )
        results.append(result)
        _write_results(output_path, results)
        print(f"[tts-rerun] {index}/{len(entries)} {result['status']} {result['word']}")

    failed = [row for row in results if row['status'] not in {'uploaded', 'already_uploaded', 'dry_run'}]
    print(json.dumps({'total': len(results), 'failed': len(failed), 'output': str(output_path)}, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
