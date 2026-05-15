from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from services.study_sessions import normalize_chapter_id


@dataclass(frozen=True)
class LearningScope:
    scope_key: str
    scope_type: str
    origin_scope: dict[str, Any]
    origin_scope_json: str
    book_id: str | None
    chapter_id: str | None
    day: int | None


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _positive_day(value) -> int | None:
    try:
        day = int(value)
    except (TypeError, ValueError):
        return None
    return day if day > 0 else None


def _pick(mapping: dict | None, *names: str):
    if not isinstance(mapping, dict):
        return None
    for name in names:
        if name in mapping and mapping[name] is not None:
            return mapping[name]
    return None


def build_scope_key(
    *,
    book_id: str | None = None,
    chapter_id: str | None = None,
    day: int | None = None,
    scope_key: str | None = None,
) -> str:
    explicit_scope_key = _text(scope_key)
    if explicit_scope_key:
        if explicit_scope_key == 'global':
            return 'user'
        return explicit_scope_key
    if book_id and chapter_id:
        return f'chapter:{book_id}:{chapter_id}'
    if book_id:
        return f'book:{book_id}'
    if day is not None:
        return f'day:{day}'
    return 'user'


def infer_scope_type(
    *,
    book_id: str | None = None,
    chapter_id: str | None = None,
    day: int | None = None,
    scope_key: str | None = None,
    scope_type: str | None = None,
) -> str:
    explicit = _text(scope_type)
    if explicit in {'chapter', 'book', 'day', 'user', 'wrong_words', 'favorites'}:
        return explicit
    normalized_key = _text(scope_key) or ''
    if normalized_key.startswith('chapter:') or (book_id and chapter_id):
        return 'chapter'
    if normalized_key.startswith('book:') or book_id:
        return 'book'
    if normalized_key.startswith('day:') or day is not None:
        return 'day'
    return 'user'


def _normalize_origin_scope(
    *,
    origin_scope,
    scope_key: str,
    scope_type: str,
    book_id: str | None,
    chapter_id: str | None,
    day: int | None,
) -> dict[str, Any]:
    source = origin_scope if isinstance(origin_scope, dict) else {}
    result = {
        'scopeKey': _text(source.get('scopeKey') or source.get('scope_key')) or scope_key,
        'scopeType': _text(source.get('scopeType') or source.get('scope_type')) or scope_type,
    }
    result_book_id = _text(source.get('bookId') or source.get('book_id')) or book_id
    result_chapter_id = normalize_chapter_id(source.get('chapterId', source.get('chapter_id'))) or chapter_id
    result_day = _positive_day(source.get('day')) or day
    if result_book_id:
        result['bookId'] = result_book_id
    if result_chapter_id:
        result['chapterId'] = result_chapter_id
    if result_day is not None:
        result['day'] = result_day
    return result


def resolve_learning_scope(
    payload: dict | None = None,
    record_payload: dict | None = None,
    *,
    book_id: str | None = None,
    chapter_id: str | None = None,
    day: int | None = None,
    scope_key: str | None = None,
    scope_type: str | None = None,
    origin_scope=None,
) -> LearningScope:
    data = payload if isinstance(payload, dict) else {}
    record = record_payload if isinstance(record_payload, dict) else {}
    normalized_book_id = (
        _text(book_id)
        or _text(_pick(record, 'bookId', 'book_id'))
        or _text(_pick(data, 'bookId', 'book_id'))
    )
    normalized_chapter_id = (
        normalize_chapter_id(chapter_id)
        or normalize_chapter_id(_pick(record, 'chapterId', 'chapter_id'))
        or normalize_chapter_id(_pick(data, 'chapterId', 'chapter_id'))
    )
    normalized_day = (
        _positive_day(day)
        or _positive_day(_pick(record, 'day'))
        or _positive_day(_pick(data, 'day'))
    )
    resolved_scope_key = build_scope_key(
        book_id=normalized_book_id,
        chapter_id=normalized_chapter_id,
        day=normalized_day,
        scope_key=(
            scope_key
            or _pick(record, 'scopeKey', 'scope_key')
            or _pick(data, 'scopeKey', 'scope_key')
        ),
    )
    resolved_scope_type = infer_scope_type(
        book_id=normalized_book_id,
        chapter_id=normalized_chapter_id,
        day=normalized_day,
        scope_key=resolved_scope_key,
        scope_type=(
            scope_type
            or _pick(record, 'scopeType', 'scope_type')
            or _pick(data, 'scopeType', 'scope_type')
        ),
    )
    resolved_origin_scope = _normalize_origin_scope(
        origin_scope=(
            origin_scope
            or _pick(record, 'originScope', 'origin_scope')
            or _pick(data, 'originScope', 'origin_scope')
        ),
        scope_key=resolved_scope_key,
        scope_type=resolved_scope_type,
        book_id=normalized_book_id,
        chapter_id=normalized_chapter_id,
        day=normalized_day,
    )
    return LearningScope(
        scope_key=resolved_scope_key,
        scope_type=resolved_scope_type,
        origin_scope=resolved_origin_scope,
        origin_scope_json=json.dumps(resolved_origin_scope, ensure_ascii=False, sort_keys=True),
        book_id=normalized_book_id,
        chapter_id=normalized_chapter_id,
        day=normalized_day,
    )
