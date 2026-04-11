from __future__ import annotations

import hashlib
from datetime import datetime

from platform_sdk.outbox_runtime import queue_outbox_event
from service_models.eventing_models import TTSMediaAsset, TTSMediaOutboxEvent


TTS_MEDIA_SERVICE_NAME = 'tts-media-service'
TTS_MEDIA_GENERATED_TOPIC = 'tts.media.generated'
_MAX_OUTBOX_AGGREGATE_ID_LENGTH = 160


def _query_session(model):
    return model.query.session


def _normalize_value(value):
    resolved = str(value or '').strip()
    return resolved or None


def _normalize_int(value):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_dt(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
    return datetime.utcnow()


def build_tts_media_aggregate_id(media_kind: str, media_id: str) -> str:
    aggregate_id = f'{media_kind}:{media_id}'
    if len(aggregate_id) <= _MAX_OUTBOX_AGGREGATE_ID_LENGTH:
        return aggregate_id
    digest = hashlib.sha1(aggregate_id.encode('utf-8')).hexdigest()
    return f'{media_kind}:sha1:{digest}'


def build_tts_media_generated_payload(asset: TTSMediaAsset) -> dict:
    return {
        'user_id': asset.user_id,
        'media_kind': asset.media_kind,
        'media_id': asset.media_id,
        'tts_provider': asset.tts_provider,
        'storage_provider': asset.storage_provider,
        'model': asset.model,
        'voice': asset.voice,
        'byte_length': int(asset.byte_length or 0),
        'generated_at': asset.generated_at.isoformat() if asset.generated_at else None,
    }


def _significant_change(
    asset: TTSMediaAsset,
    *,
    tts_provider: str | None,
    storage_provider: str | None,
    model: str | None,
    voice: str | None,
    byte_length: int,
) -> bool:
    return any((
        asset.tts_provider != tts_provider,
        asset.storage_provider != storage_provider,
        asset.model != model,
        asset.voice != voice,
        int(asset.byte_length or 0) != byte_length,
    ))


def record_tts_media_materialization(
    *,
    media_kind: str,
    media_id: str,
    tts_provider: str | None,
    storage_provider: str | None,
    model: str | None,
    voice: str | None,
    byte_length: int | None,
    user_id: int | str | None = None,
    generated_at: datetime | str | None = None,
    headers: dict | None = None,
    event_id: str | None = None,
    session=None,
) -> tuple[TTSMediaAsset, bool]:
    session = session or _query_session(TTSMediaAsset)
    resolved_media_kind = _normalize_value(media_kind)
    resolved_media_id = _normalize_value(media_id)
    resolved_tts_provider = _normalize_value(tts_provider)
    resolved_storage_provider = _normalize_value(storage_provider)
    resolved_model = _normalize_value(model)
    resolved_voice = _normalize_value(voice)
    resolved_byte_length = max(0, int(byte_length or 0))
    resolved_user_id = _normalize_int(user_id)
    resolved_generated_at = _normalize_dt(generated_at)

    if not resolved_media_kind:
        raise ValueError('tts media materialization must include media_kind')
    if not resolved_media_id:
        raise ValueError('tts media materialization must include media_id')

    asset = session.query(TTSMediaAsset).filter_by(
        media_kind=resolved_media_kind,
        media_id=resolved_media_id,
    ).first()
    created = asset is None
    changed = False

    if asset is None:
        asset = TTSMediaAsset(
            media_kind=resolved_media_kind,
            media_id=resolved_media_id,
            generated_at=resolved_generated_at,
        )
        changed = True
    else:
        changed = _significant_change(
            asset,
            tts_provider=resolved_tts_provider,
            storage_provider=resolved_storage_provider,
            model=resolved_model,
            voice=resolved_voice,
            byte_length=resolved_byte_length,
        )

    asset.media_kind = resolved_media_kind
    asset.media_id = resolved_media_id
    asset.tts_provider = resolved_tts_provider
    asset.storage_provider = resolved_storage_provider
    asset.model = resolved_model
    asset.voice = resolved_voice
    asset.byte_length = resolved_byte_length
    if asset.user_id is None and resolved_user_id is not None:
        asset.user_id = resolved_user_id
    if created or changed:
        asset.generated_at = resolved_generated_at
    session.add(asset)

    if changed:
        queue_outbox_event(
            TTSMediaOutboxEvent,
            producer_service=TTS_MEDIA_SERVICE_NAME,
            topic=TTS_MEDIA_GENERATED_TOPIC,
            aggregate_id=build_tts_media_aggregate_id(resolved_media_kind, resolved_media_id),
            payload=build_tts_media_generated_payload(asset),
            headers=headers,
            event_id=event_id,
            session=session,
        )

    session.commit()
    return asset, changed
