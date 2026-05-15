from __future__ import annotations

from services import ai_quick_memory_repository, scoped_quick_memory_repository
from services.learning_scope_support import LearningScope
from services.study_sessions import normalize_chapter_id


def safe_non_negative_int(value, default: int = 0) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return default


def quick_memory_snapshot(record) -> dict:
    return {
        'status': record.status,
        'book_id': record.book_id,
        'chapter_id': normalize_chapter_id(record.chapter_id),
        'last_seen': record.last_seen or 0,
        'known_count': record.known_count or 0,
        'unknown_count': record.unknown_count or 0,
        'next_review': record.next_review or 0,
        'fuzzy_count': record.fuzzy_count or 0,
        'scope_key': getattr(record, 'scope_key', None),
        'scope_type': getattr(record, 'scope_type', None),
    }


def _status(value, fallback: str = 'unknown') -> str:
    normalized = str(value or fallback).strip()
    return normalized if normalized in {'known', 'unknown'} else fallback


def _apply_quick_memory_fields(
    record,
    record_payload: dict,
    *,
    scope: LearningScope,
    record_last_seen: int,
    record_known_count: int,
    canonical_next_review: int,
) -> None:
    record.book_id = scope.book_id
    record.chapter_id = scope.chapter_id
    if hasattr(record, 'day'):
        record.day = scope.day
    if hasattr(record, 'scope_key'):
        record.scope_key = scope.scope_key
        record.scope_type = scope.scope_type
        record.origin_scope = scope.origin_scope_json
    record.status = _status(record_payload.get('status'), getattr(record, 'status', 'unknown'))
    record.first_seen = record_payload.get('firstSeen', getattr(record, 'first_seen', 0))
    record.last_seen = record_last_seen
    record.known_count = record_known_count
    record.unknown_count = safe_non_negative_int(
        record_payload.get('unknownCount'),
        getattr(record, 'unknown_count', 0) or 0,
    )
    record.next_review = canonical_next_review
    if record_payload.get('fuzzyCount') is not None:
        record.fuzzy_count = max(
            getattr(record, 'fuzzy_count', 0) or 0,
            safe_non_negative_int(record_payload.get('fuzzyCount')),
        )


def upsert_scoped_quick_memory_record(
    *,
    user_id: int,
    word: str,
    scope: LearningScope,
    record_payload: dict,
    record_last_seen: int,
    record_known_count: int,
    canonical_next_review: int,
):
    record = scoped_quick_memory_repository.get_user_scoped_quick_memory_record(
        user_id,
        scope_key=scope.scope_key,
        word=word,
    )
    previous_snapshot = quick_memory_snapshot(record) if record else None
    if record is None:
        record = scoped_quick_memory_repository.create_user_scoped_quick_memory_record(
            user_id,
            word,
            scope=scope,
            status=_status(record_payload.get('status')),
            first_seen=safe_non_negative_int(record_payload.get('firstSeen')),
            last_seen=record_last_seen,
            known_count=record_known_count,
            unknown_count=safe_non_negative_int(record_payload.get('unknownCount')),
            next_review=canonical_next_review,
            fuzzy_count=safe_non_negative_int(record_payload.get('fuzzyCount')),
        )
    elif record_last_seen >= (record.last_seen or 0):
        _apply_quick_memory_fields(
            record,
            record_payload,
            scope=scope,
            record_last_seen=record_last_seen,
            record_known_count=record_known_count,
            canonical_next_review=canonical_next_review,
        )
    return record, previous_snapshot, quick_memory_snapshot(record)


def upsert_global_quick_memory_projection(
    *,
    user_id: int,
    word: str,
    scope: LearningScope,
    record_payload: dict,
    record_last_seen: int,
    record_known_count: int,
    canonical_next_review: int,
):
    record = ai_quick_memory_repository.get_user_quick_memory_record(user_id, word)
    if record is None:
        return ai_quick_memory_repository.create_user_quick_memory_record(
            user_id,
            word,
            book_id=scope.book_id,
            chapter_id=scope.chapter_id,
            status=_status(record_payload.get('status')),
            first_seen=safe_non_negative_int(record_payload.get('firstSeen')),
            last_seen=record_last_seen,
            known_count=record_known_count,
            unknown_count=safe_non_negative_int(record_payload.get('unknownCount')),
            next_review=canonical_next_review,
            fuzzy_count=safe_non_negative_int(record_payload.get('fuzzyCount')),
        )
    if record_last_seen < (record.last_seen or 0):
        return record
    record.status = _status(record_payload.get('status'), record.status)
    record.first_seen = record_payload.get('firstSeen', record.first_seen)
    record.last_seen = record_last_seen
    record.known_count = record_known_count
    record.unknown_count = safe_non_negative_int(record_payload.get('unknownCount'), record.unknown_count or 0)
    record.next_review = canonical_next_review
    if not (record.book_id or '').strip():
        record.book_id = scope.book_id
    if normalize_chapter_id(record.chapter_id) is None:
        record.chapter_id = scope.chapter_id
    if record_payload.get('fuzzyCount') is not None:
        record.fuzzy_count = max(record.fuzzy_count or 0, safe_non_negative_int(record_payload.get('fuzzyCount')))
    return record
