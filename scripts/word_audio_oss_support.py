from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
for candidate in (BACKEND_PATH, SDK_PATH):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from platform_sdk.runtime_env import load_split_service_env

load_split_service_env(service_name='tts-media-service')

from services.books_registry_service import VOCAB_BOOKS
from services.word_tts import (
    collect_unique_words,
    default_word_tts_identity,
    is_probably_valid_mp3_file,
    normalize_word_key,
    remove_invalid_cached_audio,
    word_tts_cache_path,
    word_tts_data_dir,
)
import services.word_tts_oss as runtime


OSS_PRESENT = 'oss_present'
MISSING_IN_OSS = 'missing_in_oss'
SIZE_MISMATCH = 'size_mismatch'
CONTENT_TYPE_MISMATCH = 'content_type_mismatch'
MISSING_EVERYWHERE = 'missing_everywhere'
INVALID_LOCAL_MISSING_IN_OSS = 'invalid_local_missing_in_oss'


@dataclass(frozen=True)
class WordAudioRecord:
    index: int
    word: str
    normalized_word: str
    model: str
    voice: str
    cache_file: Path
    object_key: str


@dataclass(frozen=True)
class WordAudioAuditResult:
    record: WordAudioRecord
    status: str
    local_byte_length: int | None
    oss_byte_length: int | None
    oss_content_type: str | None

    @property
    def has_drift(self) -> bool:
        return self.status != OSS_PRESENT

    @property
    def can_upload_repair(self) -> bool:
        return self.status in {MISSING_IN_OSS, SIZE_MISMATCH, CONTENT_TYPE_MISMATCH}


def resolve_book_ids(selected: list[str] | None) -> list[str] | None:
    available = {book['id'] for book in VOCAB_BOOKS}
    if not selected:
        return None
    missing = [book_id for book_id in selected if book_id not in available]
    if missing:
        raise ValueError(f'Unknown book ids: {missing}')
    return selected


def iter_word_audio_records(book_ids: list[str] | None):
    _, model, voice = default_word_tts_identity()
    cache_dir = word_tts_data_dir()
    for index, word in enumerate(collect_unique_words(book_ids), start=1):
        normalized_word = normalize_word_key(word)
        if not normalized_word:
            continue
        cache_file = word_tts_cache_path(cache_dir, normalized_word, model, voice)
        yield WordAudioRecord(
            index=index,
            word=word,
            normalized_word=normalized_word,
            model=model,
            voice=voice,
            cache_file=cache_file,
            object_key=runtime.word_audio_oss_object_key(
                file_name=cache_file.name,
                model=model,
                voice=voice,
            ),
        )


def classify_word_audio_drift(
    *,
    oss_byte_length: int | None,
    oss_content_type: str | None,
    expected_content_type: str,
    local_exists: bool,
    local_is_valid: bool,
    local_byte_length: int | None,
) -> str:
    if oss_byte_length is not None:
        if local_exists and local_is_valid and local_byte_length is not None:
            if local_byte_length != oss_byte_length:
                return SIZE_MISMATCH
        if (oss_content_type or '').strip().lower() != expected_content_type.strip().lower():
            return CONTENT_TYPE_MISMATCH
        return OSS_PRESENT

    if not local_exists:
        return MISSING_EVERYWHERE

    if not local_is_valid:
        return INVALID_LOCAL_MISSING_IN_OSS

    return MISSING_IN_OSS


def inspect_word_audio_record(record: WordAudioRecord) -> WordAudioAuditResult:
    cache_file = record.cache_file
    local_exists = cache_file.exists()
    local_byte_length = cache_file.stat().st_size if local_exists else None
    local_is_valid = local_exists and is_probably_valid_mp3_file(cache_file)
    expected_content_type = runtime.DEFAULT_WORD_AUDIO_CONTENT_TYPE
    oss_metadata = runtime.resolve_word_audio_oss_metadata(
        file_name=record.cache_file.name,
        model=record.model,
        voice=record.voice,
    )
    oss_byte_length = None if oss_metadata is None else int(oss_metadata.byte_length)
    oss_content_type = None if oss_metadata is None else oss_metadata.content_type
    status = classify_word_audio_drift(
        oss_byte_length=oss_byte_length,
        oss_content_type=oss_content_type,
        expected_content_type=expected_content_type,
        local_exists=local_exists,
        local_is_valid=local_is_valid,
        local_byte_length=local_byte_length,
    )
    return WordAudioAuditResult(
        record=record,
        status=status,
        local_byte_length=local_byte_length,
        oss_byte_length=oss_byte_length,
        oss_content_type=oss_content_type,
    )


def iter_word_audio_audit_results(book_ids: list[str] | None):
    for record in iter_word_audio_records(book_ids):
        yield inspect_word_audio_record(record)


__all__ = [
    'CONTENT_TYPE_MISMATCH',
    'INVALID_LOCAL_MISSING_IN_OSS',
    'MISSING_EVERYWHERE',
    'MISSING_IN_OSS',
    'OSS_PRESENT',
    'SIZE_MISMATCH',
    'WordAudioAuditResult',
    'WordAudioRecord',
    'classify_word_audio_drift',
    'inspect_word_audio_record',
    'iter_word_audio_audit_results',
    'iter_word_audio_records',
    'remove_invalid_cached_audio',
    'resolve_book_ids',
    'runtime',
]
