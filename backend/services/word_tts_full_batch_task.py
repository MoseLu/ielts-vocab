from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

HASHED_MP3_RE = re.compile(r'^[0-9a-f]{16}\.mp3$')
SAFE_OSS_SEGMENT_RE = re.compile(r'[^a-z0-9]+')
TASK_MANIFEST_NAME = 'word_tts_full_batch_manifest.json'
TASK_PROGRESS_NAME = 'word_tts_full_batch_progress.json'
TASK_VERIFICATION_NAME = 'word_tts_full_batch_verification.json'
LEGACY_PROGRESS_NAME = 'progress_all_words.json'


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_dump(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def json_load(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def task_identity(
    provider: str,
    model: str,
    voice: str,
    book_ids: list[str] | None,
    package_size: int,
) -> str:
    scope = ','.join(book_ids or ['ALL'])
    return f'{provider}|{model}|{voice}|{scope}|pkg={package_size}'


def build_manifest(
    words: list[str],
    *,
    provider: str,
    model: str,
    voice: str,
    book_ids: list[str] | None,
    package_size: int,
) -> dict:
    total_words = len(words)
    total_packages = math.ceil(total_words / package_size) if total_words else 0
    packages = []
    for index in range(total_packages):
        start = index * package_size
        end = min(total_words, start + package_size)
        package_words = words[start:end]
        packages.append({
            'index': index,
            'start': start,
            'end': end,
            'count': end - start,
            'first_word': package_words[0] if package_words else '',
            'last_word': package_words[-1] if package_words else '',
        })

    return {
        'created_at': utc_now_iso(),
        'provider': provider,
        'model': model,
        'voice': voice,
        'book_ids': book_ids or [],
        'package_size': package_size,
        'total_words': total_words,
        'total_packages': total_packages,
        'task_identity': task_identity(provider, model, voice, book_ids, package_size),
        'packages': packages,
        'words': words,
    }


def initial_progress(manifest: dict) -> dict:
    return {
        'task_identity': manifest['task_identity'],
        'status': 'pending',
        'total_words': manifest['total_words'],
        'completed_words': 0,
        'total_packages': manifest['total_packages'],
        'completed_package_indices': [],
        'next_package_index': 0,
        'current_package_index': None,
        'current_package_completed': 0,
        'current_package_total': 0,
        'current_word': None,
        'updated_at': utc_now_iso(),
    }


def resolve_task_files(cache_dir: Path) -> tuple[Path, Path, Path]:
    return (
        cache_dir / TASK_MANIFEST_NAME,
        cache_dir / TASK_PROGRESS_NAME,
        cache_dir / TASK_VERIFICATION_NAME,
    )


def cleanup_word_audio_cache(
    cache_dir: Path,
    words: list[str],
    *,
    model: str,
    voice: str,
    word_tts_cache_path,
    normalize_word_key,
) -> dict:
    expected_names = {
        word_tts_cache_path(cache_dir, normalize_word_key(word), model, voice).name
        for word in words
        if normalize_word_key(word)
    }
    removed_target = 0
    removed_stale = 0

    for path in cache_dir.iterdir():
        if not path.is_file() or not HASHED_MP3_RE.fullmatch(path.name):
            continue
        path.unlink()
        if path.name in expected_names:
            removed_target += 1
        else:
            removed_stale += 1

    for extra_name in (
        LEGACY_PROGRESS_NAME,
        TASK_MANIFEST_NAME,
        TASK_PROGRESS_NAME,
        TASK_VERIFICATION_NAME,
    ):
        extra_path = cache_dir / extra_name
        if extra_path.exists():
            extra_path.unlink()

    return {
        'removed_target_audio': removed_target,
        'removed_stale_audio': removed_stale,
        'expected_target_audio': len(expected_names),
    }


def load_or_create_manifest(
    manifest_path: Path,
    *,
    words: list[str],
    provider: str,
    model: str,
    voice: str,
    book_ids: list[str] | None,
    package_size: int,
    reset_task: bool,
) -> dict:
    manifest = build_manifest(
        words,
        provider=provider,
        model=model,
        voice=voice,
        book_ids=book_ids,
        package_size=package_size,
    )
    if reset_task or not manifest_path.exists():
        json_dump(manifest_path, manifest)
        return manifest

    existing = json_load(manifest_path)
    if existing.get('task_identity') != manifest['task_identity']:
        json_dump(manifest_path, manifest)
        return manifest
    return existing


def load_or_create_progress(
    progress_path: Path,
    *,
    manifest: dict,
    reset_task: bool,
) -> dict:
    if reset_task or not progress_path.exists():
        progress = initial_progress(manifest)
        json_dump(progress_path, progress)
        return progress

    progress = json_load(progress_path)
    if progress.get('task_identity') != manifest['task_identity']:
        progress = initial_progress(manifest)
        json_dump(progress_path, progress)
    return progress


def update_progress(progress_path: Path, progress: dict, **updates) -> dict:
    progress.update(updates)
    progress['updated_at'] = utc_now_iso()
    json_dump(progress_path, progress)
    return progress


def build_package_upload_payload(
    package: dict,
    package_words: list[str],
    *,
    cache_dir: Path,
    model: str,
    voice: str,
    normalize_word_key,
    word_tts_cache_path,
    oss_prefix: str,
) -> dict:
    identity = f'{model}--{voice}'
    identity_segment = SAFE_OSS_SEGMENT_RE.sub('-', identity.lower()).strip('-') or 'default'
    prefix = oss_prefix.strip('/')
    base_prefix = f'{prefix}/{identity_segment}' if prefix else identity_segment
    entries: list[dict] = []

    for word in package_words:
        key = normalize_word_key(word)
        if not key:
            continue
        audio_path = word_tts_cache_path(cache_dir, key, model, voice)
        entries.append({
            'word': word,
            'normalized_word': key,
            'file_name': audio_path.name,
            'file_path': str(audio_path),
            'object_key': f'{base_prefix}/{audio_path.name}',
        })

    manifest_object_key = (
        f'{base_prefix}/packages/package-{int(package["index"]):04d}.json'
    )
    return {
        'package_index': int(package['index']),
        'package_start': int(package['start']),
        'package_end': int(package['end']),
        'package_count': int(package['count']),
        'cache_identity': identity,
        'manifest_object_key': manifest_object_key,
        'entries': entries,
    }


def verify_manifest_cache(
    words: list[str],
    *,
    cache_dir: Path,
    model: str,
    voice: str,
    count_cached_words,
    is_probably_valid_mp3_file,
    normalize_word_key,
    word_tts_cache_path,
    verification_path: Path,
) -> dict:
    verified_count = count_cached_words(words, cache_dir, model, voice)
    missing_words = []
    for word in words:
        key = normalize_word_key(word)
        if not key:
            continue
        path = word_tts_cache_path(cache_dir, key, model, voice)
        if not is_probably_valid_mp3_file(path):
            missing_words.append(word)
    payload = {
        'verified_at': utc_now_iso(),
        'expected_total': len(words),
        'verified_count': verified_count,
        'missing_count': len(missing_words),
        'missing_words': missing_words,
    }
    json_dump(verification_path, payload)
    return payload
