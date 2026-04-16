from __future__ import annotations

import logging
import os
import time
from collections.abc import Sequence

import requests

from platform_sdk.ai_prompt_run_event_application import record_ai_prompt_run_completion
from platform_sdk.asr_runtime import get_dashscope_api_key
from platform_sdk.storage.aliyun_oss import put_object_bytes
from service_models.ai_execution_models import AIWordImageAsset, db
from services.books_catalog_query_service import load_book_vocabulary

from .ai_word_image_application import (
    DEFAULT_GAME_WORD_IMAGE_BOOK_IDS,
    DEFAULT_GAME_WORD_IMAGE_MODEL,
    DEFAULT_GAME_WORD_IMAGE_PROMPT_VERSION,
    DEFAULT_GAME_WORD_IMAGE_PROVIDER,
    DEFAULT_GAME_WORD_IMAGE_SIZE,
    DEFAULT_GAME_WORD_IMAGE_STYLE,
    DEFAULT_GAME_WORD_IMAGE_STYLE_VERSION,
    GAME_WORD_IMAGE_ASYNC_ENDPOINT,
    GAME_WORD_IMAGE_MAX_POLL_ATTEMPTS,
    GAME_WORD_IMAGE_POLL_INTERVAL_SECONDS,
    GAME_WORD_IMAGE_REQUEST_TIMEOUT_SECONDS,
    GAME_WORD_IMAGE_RESULT_TIMEOUT_SECONDS,
    GAME_WORD_IMAGE_RUN_KIND,
    GAME_WORD_IMAGE_STORAGE_PROVIDER,
    GAME_WORD_IMAGE_TASK_ENDPOINT,
    WORD_IMAGE_STATUS_FAILED,
    WORD_IMAGE_STATUS_GENERATING,
    WORD_IMAGE_STATUS_QUEUED,
    WORD_IMAGE_STATUS_READY,
    _asset_book_ids,
    list_game_word_image_model_candidates,
    _truncate_text,
    _upsert_word_image_asset,
    _word_seed_from_payload,
    build_game_word_image_object_key,
    ensure_ai_word_image_asset_table,
    utc_now,
)


_MODEL_FALLBACK_STATUS_CODES = {400, 403, 404, 409, 429}
_MODEL_FALLBACK_MESSAGE_TOKENS = (
    'quota',
    'balance',
    'exceed',
    'exhaust',
    'unsupported model',
    'invalid model',
    'not enabled',
    'not activated',
    'forbidden',
    'permission denied',
    'insufficient',
)
_MODEL_COOLDOWN_UNTIL: dict[str, float] = {}


def _task_headers(*, async_mode: bool) -> dict[str, str]:
    api_key = get_dashscope_api_key()
    if not api_key:
        raise RuntimeError('DashScope API key is not configured')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    if async_mode:
        headers['X-DashScope-Async'] = 'enable'
    workspace = str(
        os.environ.get('DASHSCOPE_WORKSPACE_ID')
        or os.environ.get('DASHSCOPE_WORKSPACE')
        or ''
    ).strip()
    if workspace:
        headers['X-DashScope-WorkSpace'] = workspace
    return headers


def _dashscope_generation_payload(prompt_text: str, *, model: str) -> dict:
    return {
        'model': model,
        'input': {
            'prompt': prompt_text,
            'negative_prompt': 'text, letters, logo, watermark, subtitles, collage, split panels, blurry, low quality',
        },
        'parameters': {
            'style': DEFAULT_GAME_WORD_IMAGE_STYLE,
            'size': DEFAULT_GAME_WORD_IMAGE_SIZE,
            'n': 1,
        },
    }


def _poll_dashscope_task(task_id: str) -> dict:
    for _ in range(GAME_WORD_IMAGE_MAX_POLL_ATTEMPTS):
        response = requests.get(
            GAME_WORD_IMAGE_TASK_ENDPOINT.format(task_id=task_id),
            headers=_task_headers(async_mode=False),
            timeout=GAME_WORD_IMAGE_REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        output = payload.get('output') if isinstance(payload, dict) else {}
        status = str((output or {}).get('task_status') or '').upper()
        if status in {'SUCCEEDED', 'FAILED', 'CANCELED'}:
            return payload
        time.sleep(GAME_WORD_IMAGE_POLL_INTERVAL_SECONDS)
    raise RuntimeError(f'word-image task {task_id} timed out')


def _download_generated_image(url: str) -> tuple[bytes, str]:
    response = requests.get(url, timeout=GAME_WORD_IMAGE_RESULT_TIMEOUT_SECONDS)
    response.raise_for_status()
    content_type = str(response.headers.get('Content-Type') or 'image/png').split(';', 1)[0].strip() or 'image/png'
    if not response.content:
        raise RuntimeError('generated image payload is empty')
    return response.content, content_type


def _run_dashscope_word_image_generation(*, prompt_text: str, model: str) -> tuple[bytes, str, dict]:
    response = requests.post(
        GAME_WORD_IMAGE_ASYNC_ENDPOINT,
        headers=_task_headers(async_mode=True),
        json=_dashscope_generation_payload(prompt_text, model=model),
        timeout=GAME_WORD_IMAGE_REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    payload = response.json()
    output = payload.get('output') if isinstance(payload, dict) else {}
    task_id = str((output or {}).get('task_id') or '').strip()
    if not task_id:
        raise RuntimeError('word-image task creation did not return task_id')
    result_payload = _poll_dashscope_task(task_id)
    result_output = result_payload.get('output') if isinstance(result_payload, dict) else {}
    task_status = str((result_output or {}).get('task_status') or '').upper()
    if task_status != 'SUCCEEDED':
        message = _truncate_text((result_output or {}).get('message') or 'word-image task failed', limit=240)
        raise RuntimeError(message or 'word-image task failed')
    results = (result_output or {}).get('results') or []
    for item in results:
        if not isinstance(item, dict):
            continue
        url = str(item.get('url') or '').strip()
        if not url:
            continue
        body, content_type = _download_generated_image(url)
        return body, content_type, {'task_id': task_id, 'url': url}
    raise RuntimeError('word-image task finished without a downloadable result')


def _should_try_next_model(exc: Exception) -> bool:
    if isinstance(exc, requests.HTTPError):
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code in _MODEL_FALLBACK_STATUS_CODES:
            return True
    lowered = str(exc).lower()
    return any(token in lowered for token in _MODEL_FALLBACK_MESSAGE_TOKENS)


def _should_cooldown_model(exc: Exception) -> bool:
    if isinstance(exc, requests.HTTPError):
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 429:
            return True
    lowered = str(exc).lower()
    return any(token in lowered for token in ('quota', 'balance', 'exceed', 'exhaust', 'limit'))


def _model_cooldown_seconds() -> int:
    raw_value = str(os.environ.get('GAME_WORD_IMAGE_MODEL_COOLDOWN_SECONDS') or '').strip()
    try:
        return max(60, int(raw_value))
    except ValueError:
        return 900


def _mark_model_cooldown(model: str, exc: Exception) -> None:
    if not _should_cooldown_model(exc):
        return
    _MODEL_COOLDOWN_UNTIL[model] = time.time() + float(_model_cooldown_seconds())


def _is_model_on_cooldown(model: str) -> bool:
    expires_at = _MODEL_COOLDOWN_UNTIL.get(model)
    if expires_at is None:
        return False
    if expires_at <= time.time():
        _MODEL_COOLDOWN_UNTIL.pop(model, None)
        return False
    return True


def _generate_word_image_with_model_fallback(asset: AIWordImageAsset) -> tuple[bytes, str, dict]:
    attempted_models: list[str] = []
    last_error: Exception | None = None
    for candidate_model in list_game_word_image_model_candidates(preferred_model=asset.model):
        if _is_model_on_cooldown(candidate_model):
            continue
        attempted_models.append(candidate_model)
        try:
            image_bytes, content_type, runtime_metadata = _run_dashscope_word_image_generation(
                prompt_text=asset.prompt_text,
                model=candidate_model,
            )
            return image_bytes, content_type, {
                **runtime_metadata,
                'attempted_models': attempted_models,
                'selected_model': candidate_model,
            }
        except Exception as exc:
            last_error = exc
            logging.warning(
                '[AI] Game word image model %s failed for %s: %s',
                candidate_model,
                asset.sense_key,
                exc,
            )
            _mark_model_cooldown(candidate_model, exc)
            if not _should_try_next_model(exc):
                break

    attempted = ', '.join(attempted_models) or DEFAULT_GAME_WORD_IMAGE_MODEL
    message = _truncate_text(last_error, limit=180) if last_error is not None else None
    raise RuntimeError(f'word-image generation failed after trying [{attempted}]: {message or "unknown error"}')


def _claim_next_queued_asset() -> AIWordImageAsset | None:
    ensure_ai_word_image_asset_table()
    candidate = (
        AIWordImageAsset.query
        .filter_by(status=WORD_IMAGE_STATUS_QUEUED)
        .order_by(AIWordImageAsset.last_requested_at.asc(), AIWordImageAsset.created_at.asc(), AIWordImageAsset.id.asc())
        .first()
    )
    if candidate is None:
        return None
    updated = (
        AIWordImageAsset.query
        .filter_by(id=candidate.id, status=WORD_IMAGE_STATUS_QUEUED)
        .update(
            {
                'status': WORD_IMAGE_STATUS_GENERATING,
                'attempt_count': int(candidate.attempt_count or 0) + 1,
                'updated_at': utc_now(),
            },
            synchronize_session=False,
        )
    )
    db.session.commit()
    if updated == 0:
        return None
    return AIWordImageAsset.query.filter_by(id=candidate.id).first()


def _record_word_image_prompt_run(*, asset: AIWordImageAsset, response_excerpt: str | None, metadata: dict) -> None:
    try:
        record_ai_prompt_run_completion(
            user_id=None,
            run_kind=GAME_WORD_IMAGE_RUN_KIND,
            prompt_excerpt=asset.prompt_text,
            response_excerpt=response_excerpt,
            result_ref=asset.sense_key,
            provider=asset.provider,
            model=asset.model,
            metadata=metadata,
        )
    except Exception as exc:
        logging.warning('[AI] Failed to record game word image prompt run for %s: %s', asset.sense_key, exc)


def drain_game_word_image_generation_queue(*, limit: int = 10) -> int:
    processed = 0
    for _ in range(max(1, int(limit or 1))):
        asset = _claim_next_queued_asset()
        if asset is None:
            break
        try:
            image_bytes, content_type, runtime_metadata = _generate_word_image_with_model_fallback(asset)
            object_key = asset.object_key or build_game_word_image_object_key(sense_key=asset.sense_key)
            stored = put_object_bytes(
                object_key=object_key,
                body=image_bytes,
                content_type=content_type or 'image/png',
            )
            if stored is None:
                raise RuntimeError('failed to upload generated image to OSS')
            asset.status = WORD_IMAGE_STATUS_READY
            asset.model = str(runtime_metadata.get('selected_model') or asset.model or DEFAULT_GAME_WORD_IMAGE_MODEL)
            asset.storage_provider = stored.provider
            asset.object_key = stored.object_key
            asset.generated_at = utc_now()
            asset.last_error = None
            db.session.commit()
            _record_word_image_prompt_run(
                asset=asset,
                response_excerpt=stored.object_key,
                metadata={
                    'status': WORD_IMAGE_STATUS_READY,
                    'object_key': stored.object_key,
                    'task_id': runtime_metadata.get('task_id'),
                    'source_url': runtime_metadata.get('url'),
                    'attempted_models': runtime_metadata.get('attempted_models') or [asset.model],
                    'selected_model': asset.model,
                    'attempt_count': int(asset.attempt_count or 0),
                    'style_version': asset.style_version,
                },
            )
        except Exception as exc:
            error_message = _truncate_text(exc, limit=240) or 'word-image generation failed'
            asset.status = WORD_IMAGE_STATUS_FAILED
            asset.last_error = error_message
            db.session.commit()
            _record_word_image_prompt_run(
                asset=asset,
                response_excerpt=error_message,
                metadata={
                    'status': WORD_IMAGE_STATUS_FAILED,
                    'attempt_count': int(asset.attempt_count or 0),
                    'style_version': asset.style_version,
                    'error': error_message,
                },
            )
        processed += 1
    return processed


def queue_game_word_images_for_books(
    *,
    book_ids: Sequence[str] | None = None,
    limit: int = 0,
    resume: bool = False,
) -> dict[str, int]:
    ensure_ai_word_image_asset_table()
    ordered_book_ids = [book_id for book_id in (book_ids or DEFAULT_GAME_WORD_IMAGE_BOOK_IDS) if str(book_id or '').strip()]
    candidate_map: dict[str, dict] = {}
    ordered_keys: list[str] = []
    for book_id in ordered_book_ids:
        vocabulary = load_book_vocabulary(book_id) or []
        for entry in vocabulary:
            seed = _word_seed_from_payload(entry, fallback_book_id=book_id)
            if seed is None:
                continue
            sense_key = seed['sense_key']
            existing = candidate_map.get(sense_key)
            if existing is None:
                candidate_map[sense_key] = seed
                ordered_keys.append(sense_key)
                continue
            existing['book_ids'] = _asset_book_ids(
                AIWordImageAsset(book_ids_json=None),
                [*existing['book_ids'], *seed['book_ids']],
            )

    summary = {
        'queued': 0,
        'skipped_ready': 0,
        'skipped_existing': 0,
        'updated_existing': 0,
        'seen_candidates': 0,
    }
    for index, sense_key in enumerate(ordered_keys, start=1):
        if limit > 0 and index > limit:
            break
        seed = candidate_map[sense_key]
        summary['seen_candidates'] += 1
        asset = AIWordImageAsset.query.filter_by(sense_key=sense_key).first()
        if asset is None:
            _upsert_word_image_asset(seed, now_utc=utc_now())
            summary['queued'] += 1
            continue
        asset.set_book_ids(_asset_book_ids(asset, seed['book_ids']))
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
        asset.object_key = asset.object_key or build_game_word_image_object_key(sense_key=sense_key)
        asset.last_requested_at = utc_now()
        if asset.status == WORD_IMAGE_STATUS_READY:
            summary['skipped_ready'] += 1
        elif resume or asset.status in {WORD_IMAGE_STATUS_QUEUED, WORD_IMAGE_STATUS_GENERATING}:
            summary['skipped_existing'] += 1
        else:
            asset.status = WORD_IMAGE_STATUS_QUEUED
            asset.last_error = None
            summary['updated_existing'] += 1
        db.session.commit()
    return summary
