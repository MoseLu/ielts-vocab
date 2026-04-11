from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
TTS_MEDIA_SERVICE_PATH = REPO_ROOT / 'services' / 'tts-media-service'
for candidate in (BACKEND_PATH, SDK_PATH, TTS_MEDIA_SERVICE_PATH):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from platform_sdk.runtime_env import load_split_service_env

load_split_service_env(service_name='tts-media-service')

import runtime_helpers as runtime
from services.books_catalog_service import load_book_vocabulary
from services.books_registry_service import VOCAB_BOOKS
from services.tts_batch_generation_service import get_book_examples


OSS_PRESENT = 'oss_present'
MISSING_IN_OSS = 'missing_in_oss'
SIZE_MISMATCH = 'size_mismatch'
CONTENT_TYPE_MISMATCH = 'content_type_mismatch'
MISSING_EVERYWHERE = 'missing_everywhere'
INVALID_LOCAL_MISSING_IN_OSS = 'invalid_local_missing_in_oss'


@dataclass(frozen=True)
class ExampleAudioRecord:
    index: int
    book_id: str
    sentence: str
    model: str
    voice: str
    cache_file: Path
    object_key: str


@dataclass(frozen=True)
class ExampleAudioAuditResult:
    record: ExampleAudioRecord
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


def resolve_book_ids(selected: list[str] | None) -> list[str]:
    available = {book['id'] for book in VOCAB_BOOKS}
    if not selected:
        return [book['id'] for book in VOCAB_BOOKS]
    missing = [book_id for book_id in selected if book_id not in available]
    if missing:
        raise ValueError(f'Unknown book ids: {missing}')
    return selected


def iter_example_audio_records(book_ids: list[str]):
    seen_object_keys: set[str] = set()
    processed = 0
    for book_id in book_ids:
        examples = get_book_examples(book_id, load_book_vocabulary=load_book_vocabulary)
        for example in examples:
            sentence = str(example.get('sentence') or '').strip()
            if not sentence:
                continue
            model, voice = runtime.example_tts_identity(sentence)
            cache_file = runtime.example_cache_file(sentence, model, voice)
            object_key = runtime.example_audio_object_key(sentence, model, voice)
            if object_key in seen_object_keys:
                continue
            seen_object_keys.add(object_key)
            processed += 1
            yield ExampleAudioRecord(
                index=processed,
                book_id=book_id,
                sentence=sentence,
                model=model,
                voice=voice,
                cache_file=cache_file,
                object_key=object_key,
            )


def classify_example_audio_drift(
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


def inspect_example_audio_record(record: ExampleAudioRecord) -> ExampleAudioAuditResult:
    cache_file = record.cache_file
    local_exists = cache_file.exists()
    local_byte_length = cache_file.stat().st_size if local_exists else None
    local_is_valid = local_exists and runtime.is_probably_valid_mp3_file(cache_file)
    expected_content_type = runtime.DEFAULT_EXAMPLE_AUDIO_CONTENT_TYPE
    oss_metadata = runtime.resolve_example_audio_oss_metadata(
        record.sentence,
        record.model,
        record.voice,
    )
    oss_byte_length = None if oss_metadata is None else int(oss_metadata.byte_length)
    oss_content_type = None if oss_metadata is None else oss_metadata.content_type
    status = classify_example_audio_drift(
        oss_byte_length=oss_byte_length,
        oss_content_type=oss_content_type,
        expected_content_type=expected_content_type,
        local_exists=local_exists,
        local_is_valid=local_is_valid,
        local_byte_length=local_byte_length,
    )
    return ExampleAudioAuditResult(
        record=record,
        status=status,
        local_byte_length=local_byte_length,
        oss_byte_length=oss_byte_length,
        oss_content_type=oss_content_type,
    )


def iter_example_audio_audit_results(book_ids: list[str]):
    for record in iter_example_audio_records(book_ids):
        yield inspect_example_audio_record(record)
