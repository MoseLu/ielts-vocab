from __future__ import annotations

from platform_sdk.notes_repository_adapters import daily_summary_repository, learning_note_repository


_DEFAULT_LIMIT = 80
_MAX_LIMIT = 200


def _parse_limit(raw_value) -> int:
    try:
        value = int(raw_value or _DEFAULT_LIMIT)
    except (TypeError, ValueError):
        return _DEFAULT_LIMIT
    return max(1, min(_MAX_LIMIT, value))


def _parse_descending(raw_value) -> bool:
    return str(raw_value or 'true').strip().lower() != 'false'


def list_internal_learning_notes_response(user_id: int, args) -> tuple[dict, int]:
    notes = learning_note_repository.list_learning_notes(
        user_id,
        limit=_parse_limit(args.get('limit')),
        descending=_parse_descending(args.get('descending')),
    )
    return {'notes': [note.to_dict() for note in notes]}, 200


def list_internal_daily_summaries_response(user_id: int, args) -> tuple[dict, int]:
    summaries = daily_summary_repository.list_daily_summaries(
        user_id,
        descending=_parse_descending(args.get('descending')),
    )
    limit = _parse_limit(args.get('limit'))
    return {'summaries': [summary.to_dict() for summary in summaries[:limit]]}, 200


def create_internal_learning_note_response(user_id: int, data: dict | None) -> tuple[dict, int]:
    payload = data or {}
    question = str(payload.get('question') or '').strip()
    answer = str(payload.get('answer') or '').strip()
    if not question:
        return {'error': 'question is required'}, 400
    if not answer:
        return {'error': 'answer is required'}, 400

    word_context = str(payload.get('word_context') or '').strip() or None
    try:
        note = learning_note_repository.create_learning_note(
            user_id,
            question=question,
            answer=answer,
            word_context=word_context,
        )
        learning_note_repository.commit()
    except Exception:
        learning_note_repository.rollback()
        raise
    return {'note': note.to_dict()}, 201
