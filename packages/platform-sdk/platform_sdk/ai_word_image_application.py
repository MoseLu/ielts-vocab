from __future__ import annotations

import hashlib
import logging
import os
import re
from collections.abc import Iterable, Sequence
from datetime import datetime

from platform_sdk.storage.aliyun_oss import (
    join_object_key,
    resolve_object_metadata,
    sanitize_segment,
)
from service_models.ai_execution_models import AIWordImageAsset, db


WORD_IMAGE_STATUS_QUEUED = 'queued'
WORD_IMAGE_STATUS_GENERATING = 'generating'
WORD_IMAGE_STATUS_READY = 'ready'
WORD_IMAGE_STATUS_FAILED = 'failed'
WORD_IMAGE_STATUSES = (
    WORD_IMAGE_STATUS_QUEUED,
    WORD_IMAGE_STATUS_GENERATING,
    WORD_IMAGE_STATUS_READY,
    WORD_IMAGE_STATUS_FAILED,
)
DEFAULT_GAME_WORD_IMAGE_PROVIDER = 'dashscope'
DEFAULT_GAME_WORD_IMAGE_MODEL = 'wanx-v1'
DEFAULT_GAME_WORD_IMAGE_MODEL_CANDIDATES = (
    'wanx-v1',
    'wanx2.1-t2i-plus',
    'wanx2.1-t2i-turbo',
    'wanx2.0-t2i-turbo',
    'wan2.2-t2i-plus',
    'wan2.2-t2i-flash',
    'wan2.5-t2i-preview',
    'wan2.6-t2i',
)
DEFAULT_GAME_WORD_IMAGE_STYLE_VERSION = 'edu-illustration-v1'
DEFAULT_GAME_WORD_IMAGE_PROMPT_VERSION = 'v1'
DEFAULT_GAME_WORD_IMAGE_SIZE = '1024*1024'
DEFAULT_GAME_WORD_IMAGE_STYLE = '<flat illustration>'
DEFAULT_GAME_WORD_IMAGE_BOOK_IDS = (
    'ielts_reading_premium',
    'ielts_listening_premium',
)
GAME_WORD_IMAGE_RUN_KIND = 'game_word_image'
GAME_WORD_IMAGE_STORAGE_PROVIDER = 'aliyun-oss'
GAME_WORD_IMAGE_OBJECT_PREFIX = 'projects/ielts-vocab'
GAME_WORD_IMAGE_ASYNC_ENDPOINT = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis'
GAME_WORD_IMAGE_TASK_ENDPOINT = 'https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}'
GAME_WORD_IMAGE_REQUEST_TIMEOUT_SECONDS = 30
GAME_WORD_IMAGE_RESULT_TIMEOUT_SECONDS = 60
GAME_WORD_IMAGE_POLL_INTERVAL_SECONDS = 2
GAME_WORD_IMAGE_MAX_POLL_ATTEMPTS = 45
GAME_WORD_IMAGE_MAX_ATTEMPTS = 3
GAME_WORD_IMAGE_FAILED_RETRY_COOLDOWN_SECONDS = 900
_SENSE_SEGMENT_RE = re.compile(r'[^a-z0-9]+')
_WHITESPACE_RE = re.compile(r'\s+')
_WORD_IMAGE_TABLE_READY = False


def utc_now() -> datetime:
    return datetime.utcnow()


def _clean_text(value) -> str:
    return _WHITESPACE_RE.sub(' ', str(value or '').strip())


def _truncate_text(value, *, limit: int = 500) -> str | None:
    text = _clean_text(value)
    if not text:
        return None
    return text[:limit]


def _read_game_word_image_model_candidates() -> tuple[str, ...]:
    raw_value = _clean_text(os.environ.get('GAME_WORD_IMAGE_MODEL_CANDIDATES'))
    if not raw_value:
        return DEFAULT_GAME_WORD_IMAGE_MODEL_CANDIDATES
    candidates = []
    seen: set[str] = set()
    for item in raw_value.split(','):
        model = _clean_text(item)
        if not model or model in seen:
            continue
        seen.add(model)
        candidates.append(model)
    return tuple(candidates) or DEFAULT_GAME_WORD_IMAGE_MODEL_CANDIDATES


def list_game_word_image_model_candidates(*, preferred_model: str | None = None) -> tuple[str, ...]:
    ordered: list[str] = []
    seen: set[str] = set()
    for model in (_clean_text(preferred_model), *_read_game_word_image_model_candidates()):
        if not model or model in seen:
            continue
        seen.add(model)
        ordered.append(model)
    if DEFAULT_GAME_WORD_IMAGE_MODEL not in seen:
        ordered.insert(0, DEFAULT_GAME_WORD_IMAGE_MODEL)
    return tuple(ordered)


def _normalize_sense_segment(value: str, *, fallback: str) -> str:
    cleaned = _SENSE_SEGMENT_RE.sub('-', _clean_text(value).lower()).strip('-')
    return cleaned or fallback


def build_game_word_image_sense_key(
    *,
    word: str,
    pos: str | None,
    definition: str,
    style_version: str = DEFAULT_GAME_WORD_IMAGE_STYLE_VERSION,
) -> str:
    normalized_word = _normalize_sense_segment(word, fallback='word')
    normalized_pos = _normalize_sense_segment(pos or 'general', fallback='general')
    definition_hash = hashlib.sha1(_clean_text(definition).encode('utf-8')).hexdigest()[:12]
    style_segment = _normalize_sense_segment(style_version, fallback='style')
    return f'{normalized_word}-{normalized_pos}-{definition_hash}-{style_segment}'


def build_game_word_image_object_key(
    *,
    sense_key: str,
    style_version: str = DEFAULT_GAME_WORD_IMAGE_STYLE_VERSION,
) -> str:
    return join_object_key(
        prefix=GAME_WORD_IMAGE_OBJECT_PREFIX,
        segments=('game-word-images', sanitize_segment(style_version)),
        file_name=f'{sense_key}.png',
    )


def extract_game_word_example_text(word_payload: dict | None) -> str | None:
    examples = word_payload.get('examples') if isinstance(word_payload, dict) else None
    if not isinstance(examples, list):
        return None
    for item in examples:
        if not isinstance(item, dict):
            continue
        text = _clean_text(item.get('en') or item.get('zh'))
        if text:
            return text[:240]
    return None


def build_game_word_image_prompt(
    *,
    word: str,
    pos: str | None,
    definition: str,
    example_text: str | None,
) -> str:
    parts = [
        'Create a clean educational illustration for an IELTS vocabulary flashcard.',
        f'Word: "{_clean_text(word)}".',
    ]
    if _clean_text(pos):
        parts.append(f'Part of speech: "{_clean_text(pos)}".')
    parts.append(f'Sense: "{_clean_text(definition)}".')
    if _clean_text(example_text):
        parts.append(f'Example context: "{_clean_text(example_text)}".')
    parts.extend((
        'Show one clear scene or visual metaphor that helps a learner remember this exact sense.',
        'Use a calm, premium educational illustration style with a single dominant subject and a simple background.',
        'No text, no letters, no subtitles, no watermark, no logo, no collage, no split panels, square composition.',
    ))
    return ' '.join(parts)[:780]


def ensure_ai_word_image_asset_table() -> None:
    global _WORD_IMAGE_TABLE_READY
    if _WORD_IMAGE_TABLE_READY:
        return
    AIWordImageAsset.__table__.create(bind=db.engine, checkfirst=True)
    _WORD_IMAGE_TABLE_READY = True


def _asset_book_ids(asset: AIWordImageAsset, extra_book_ids: Iterable[str] | None = None) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for value in (*asset.book_ids(), *(extra_book_ids or ())):
        text = str(value or '').strip()
        if not text or text in seen:
            continue
        seen.add(text)
        merged.append(text)
    return merged


def _failed_retry_cooldown_seconds() -> int:
    raw = str(os.environ.get('GAME_WORD_IMAGE_FAILED_RETRY_COOLDOWN_SECONDS') or '').strip()
    try:
        return max(60, int(raw))
    except ValueError:
        return GAME_WORD_IMAGE_FAILED_RETRY_COOLDOWN_SECONDS


def _should_requeue_failed_asset(asset: AIWordImageAsset, *, now_utc: datetime) -> bool:
    if int(asset.attempt_count or 0) >= GAME_WORD_IMAGE_MAX_ATTEMPTS:
        return False
    if asset.last_requested_at is None:
        return True
    elapsed_seconds = max(0.0, (now_utc - asset.last_requested_at).total_seconds())
    return elapsed_seconds >= _failed_retry_cooldown_seconds()


def _serialize_game_word_image(
    *,
    asset: AIWordImageAsset | None,
    word: str,
    sense_key: str,
    status: str,
    url: str | None = None,
) -> dict:
    return {
        'status': status,
        'senseKey': sense_key,
        'url': url,
        'alt': f'{word} 词义配图',
        'styleVersion': asset.style_version if asset is not None else DEFAULT_GAME_WORD_IMAGE_STYLE_VERSION,
        'model': asset.model if asset is not None else DEFAULT_GAME_WORD_IMAGE_MODEL,
        'generatedAt': asset.generated_at.isoformat() if asset is not None and asset.generated_at else None,
    }


def _word_seed_from_payload(word_payload: dict, *, fallback_book_id: str | None = None) -> dict | None:
    if not isinstance(word_payload, dict):
        return None
    word = _clean_text(word_payload.get('word'))
    definition = _clean_text(word_payload.get('definition'))
    if not word or not definition:
        return None
    pos = _clean_text(word_payload.get('pos'))
    example_text = extract_game_word_example_text(word_payload)
    sense_key = build_game_word_image_sense_key(word=word, pos=pos, definition=definition)
    book_id = _clean_text(word_payload.get('book_id') or word_payload.get('bookId') or fallback_book_id) or None
    return {
        'sense_key': sense_key,
        'word': word,
        'pos': pos or None,
        'definition': definition,
        'example_text': example_text,
        'prompt_text': build_game_word_image_prompt(
            word=word,
            pos=pos,
            definition=definition,
            example_text=example_text,
        ),
        'book_ids': [book_id] if book_id else [],
    }


def _upsert_word_image_asset(seed: dict, *, now_utc: datetime) -> AIWordImageAsset:
    asset = AIWordImageAsset.query.filter_by(sense_key=seed['sense_key']).first()
    if asset is None:
        asset = AIWordImageAsset(
            sense_key=seed['sense_key'],
            word=seed['word'],
            pos=seed['pos'],
            definition=seed['definition'],
            example_text=seed['example_text'],
            prompt_text=seed['prompt_text'],
            prompt_version=DEFAULT_GAME_WORD_IMAGE_PROMPT_VERSION,
            style_version=DEFAULT_GAME_WORD_IMAGE_STYLE_VERSION,
            provider=DEFAULT_GAME_WORD_IMAGE_PROVIDER,
            model=DEFAULT_GAME_WORD_IMAGE_MODEL,
            storage_provider=GAME_WORD_IMAGE_STORAGE_PROVIDER,
            object_key=build_game_word_image_object_key(sense_key=seed['sense_key']),
            status=WORD_IMAGE_STATUS_QUEUED,
            attempt_count=0,
            last_requested_at=now_utc,
        )
        asset.set_book_ids(seed['book_ids'])
        db.session.add(asset)
        db.session.commit()
        return asset

    asset.word = seed['word']
    asset.pos = seed['pos']
    asset.definition = seed['definition']
    asset.example_text = seed['example_text']
    asset.prompt_text = seed['prompt_text']
    asset.prompt_version = DEFAULT_GAME_WORD_IMAGE_PROMPT_VERSION
    asset.style_version = DEFAULT_GAME_WORD_IMAGE_STYLE_VERSION
    asset.provider = DEFAULT_GAME_WORD_IMAGE_PROVIDER
    asset.model = DEFAULT_GAME_WORD_IMAGE_MODEL
    asset.storage_provider = GAME_WORD_IMAGE_STORAGE_PROVIDER
    asset.object_key = asset.object_key or build_game_word_image_object_key(sense_key=seed['sense_key'])
    asset.set_book_ids(_asset_book_ids(asset, seed['book_ids']))
    asset.last_requested_at = now_utc
    if asset.status == WORD_IMAGE_STATUS_FAILED and _should_requeue_failed_asset(asset, now_utc=now_utc):
        asset.status = WORD_IMAGE_STATUS_QUEUED
        asset.last_error = None
    db.session.commit()
    return asset


def resolve_game_word_image_payload(word_payload: dict, *, fallback_book_id: str | None = None) -> dict:
    ensure_ai_word_image_asset_table()
    seed = _word_seed_from_payload(word_payload, fallback_book_id=fallback_book_id)
    if seed is None:
        return _serialize_game_word_image(
            asset=None,
            word=_clean_text((word_payload or {}).get('word')) or 'word',
            sense_key='',
            status=WORD_IMAGE_STATUS_FAILED,
        )

    asset = _upsert_word_image_asset(seed, now_utc=utc_now())
    if asset.status == WORD_IMAGE_STATUS_READY and asset.object_key:
        metadata = resolve_object_metadata(object_key=asset.object_key)
        if metadata is not None:
            return _serialize_game_word_image(
                asset=asset,
                word=seed['word'],
                sense_key=seed['sense_key'],
                status=WORD_IMAGE_STATUS_READY,
                url=metadata.signed_url,
            )
        asset.status = WORD_IMAGE_STATUS_QUEUED
        asset.last_error = 'image object missing from storage'
        db.session.commit()

    return _serialize_game_word_image(
        asset=asset,
        word=seed['word'],
        sense_key=seed['sense_key'],
        status=asset.status if asset.status in WORD_IMAGE_STATUSES else WORD_IMAGE_STATUS_FAILED,
    )


def enrich_game_state_with_word_image(payload: dict | None) -> dict | None:
    if not isinstance(payload, dict):
        return payload
    active_word = payload.get('activeWord')
    if not isinstance(active_word, dict):
        return payload
    scope = payload.get('scope') if isinstance(payload.get('scope'), dict) else {}
    fallback_book_id = _clean_text(scope.get('bookId')) or _clean_text(active_word.get('book_id')) or None
    try:
        image = resolve_game_word_image_payload(active_word, fallback_book_id=fallback_book_id)
    except Exception as exc:
        logging.warning('[AI] Failed to resolve game word image for %s: %s', active_word.get('word'), exc)
        seed = _word_seed_from_payload(active_word, fallback_book_id=fallback_book_id)
        image = _serialize_game_word_image(
            asset=None,
            word=_clean_text(active_word.get('word')) or 'word',
            sense_key=seed['sense_key'] if seed else '',
            status=WORD_IMAGE_STATUS_FAILED,
        )
    return {
        **payload,
        'activeWord': {
            **active_word,
            'image': image,
        },
    }


def drain_game_word_image_generation_queue(*, limit: int = 10) -> int:
    from platform_sdk.ai_word_image_worker_application import drain_game_word_image_generation_queue as drain_impl

    return drain_impl(limit=limit)


def queue_game_word_images_for_books(
    *,
    book_ids: Sequence[str] | None = None,
    limit: int = 0,
    resume: bool = False,
) -> dict[str, int]:
    from platform_sdk.ai_word_image_worker_application import queue_game_word_images_for_books as queue_impl

    return queue_impl(book_ids=book_ids, limit=limit, resume=resume)
