from __future__ import annotations

from datetime import datetime

from platform_sdk.learning_event_support import record_learning_event
from platform_sdk.learning_repository_adapters import learning_event_repository


def _parse_optional_datetime(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError as exc:
            raise ValueError('occurred_at must be ISO-8601 datetime') from exc
    raise ValueError('occurred_at must be ISO-8601 datetime')


def record_internal_learning_event_response(user_id: int, data: dict | None) -> tuple[dict, int]:
    payload = data if isinstance(data, dict) else {}
    event_type = str(payload.get('event_type') or '').strip()
    source = str(payload.get('source') or '').strip()
    if not event_type:
        return {'error': 'event_type is required'}, 400
    if not source:
        return {'error': 'source is required'}, 400

    try:
        event = record_learning_event(
            add_learning_event=learning_event_repository.add_learning_event,
            user_id=user_id,
            event_type=event_type,
            source=source,
            mode=payload.get('mode'),
            book_id=payload.get('book_id'),
            chapter_id=payload.get('chapter_id'),
            word=payload.get('word'),
            item_count=payload.get('item_count') or 0,
            correct_count=payload.get('correct_count') or 0,
            wrong_count=payload.get('wrong_count') or 0,
            duration_seconds=payload.get('duration_seconds') or 0,
            payload=payload.get('payload') if isinstance(payload.get('payload'), dict) else None,
            occurred_at=_parse_optional_datetime(payload.get('occurred_at')),
        )
        learning_event_repository.commit()
    except ValueError as error:
        return {'error': str(error)}, 400
    except Exception:
        learning_event_repository.rollback()
        raise
    return {'event': event.to_dict()}, 201
