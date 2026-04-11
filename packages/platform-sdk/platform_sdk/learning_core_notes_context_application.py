from __future__ import annotations

from datetime import datetime

from service_models.learning_core_models import UserStudySession, UserWrongWord


def _parse_optional_datetime(raw_value, *, field_name: str) -> tuple[datetime | None, str | None]:
    text_value = str(raw_value or '').strip()
    if not text_value:
        return None, None
    try:
        return datetime.fromisoformat(text_value.replace('Z', '+00:00')), None
    except ValueError:
        return None, f'{field_name} must be a valid ISO datetime'


def _parse_bool(raw_value, *, default: bool = False) -> bool:
    if raw_value is None:
        return default
    return str(raw_value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _parse_limit(raw_value, *, maximum: int = 1000) -> int | None:
    if raw_value in (None, ''):
        return None
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return None
    return max(1, min(maximum, parsed))


def _serialize_study_session(row: UserStudySession) -> dict[str, object]:
    total = int(row.correct_count or 0) + int(row.wrong_count or 0)
    return {
        'id': row.id,
        'user_id': row.user_id,
        'mode': row.mode,
        'book_id': row.book_id,
        'chapter_id': row.chapter_id,
        'words_studied': int(row.words_studied or 0),
        'correct_count': int(row.correct_count or 0),
        'wrong_count': int(row.wrong_count or 0),
        'accuracy': round((row.correct_count or 0) / total * 100) if total > 0 else 0,
        'duration_seconds': int(row.duration_seconds or 0),
        'started_at': row.started_at.isoformat() if row.started_at else None,
        'ended_at': row.ended_at.isoformat() if row.ended_at else None,
    }


def list_internal_notes_study_sessions_response(user_id: int, args) -> tuple[dict, int]:
    start_at, start_at_error = _parse_optional_datetime(args.get('start_at'), field_name='start_at')
    if start_at_error:
        return {'error': start_at_error}, 400

    end_before, end_before_error = _parse_optional_datetime(
        args.get('end_before'),
        field_name='end_before',
    )
    if end_before_error:
        return {'error': end_before_error}, 400

    query = UserStudySession.query.filter_by(user_id=user_id)
    if start_at is not None:
        query = query.filter(UserStudySession.started_at >= start_at)
    if end_before is not None:
        query = query.filter(UserStudySession.started_at < end_before)
    if _parse_bool(args.get('require_words_studied')):
        query = query.filter(UserStudySession.words_studied > 0)

    order_clause = (
        UserStudySession.started_at.desc()
        if _parse_bool(args.get('descending'))
        else UserStudySession.started_at.asc()
    )
    query = query.order_by(order_clause)

    limit = _parse_limit(args.get('limit'))
    if limit is not None:
        query = query.limit(limit)

    return {
        'sessions': [_serialize_study_session(row) for row in query.all()],
    }, 200


def list_internal_notes_wrong_words_response(user_id: int, args) -> tuple[dict, int]:
    query = (
        UserWrongWord.query
        .filter_by(user_id=user_id)
        .order_by(
            UserWrongWord.updated_at.desc(),
            UserWrongWord.wrong_count.desc(),
            UserWrongWord.word.asc(),
        )
    )
    limit = _parse_limit(args.get('limit'), maximum=500)
    if limit is not None:
        query = query.limit(limit)
    return {
        'wrong_words': [row.to_dict() for row in query.all()],
    }, 200
