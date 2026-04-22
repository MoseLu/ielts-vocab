from __future__ import annotations

from platform_sdk.ai_vocab_catalog_application import (
    get_global_vocab_pool,
    resolve_quick_memory_vocab_entry,
)
from platform_sdk.learning_repository_adapters import quick_memory_record_repository
from platform_sdk.local_time_support import utc_naive_to_epoch_ms, utc_now_naive
from platform_sdk.quick_memory_schedule_support import load_and_normalize_quick_memory_records
from platform_sdk.study_session_support import normalize_chapter_id


def _parse_review_queue_options(args, *, now_ms: int) -> dict:
    try:
        raw_limit = int(args.get('limit', 20))
    except (TypeError, ValueError):
        raw_limit = 20

    try:
        offset = max(0, int(args.get('offset', 0)))
    except (TypeError, ValueError):
        offset = 0

    try:
        within_days = max(1, min(int(args.get('within_days', 1)), 30))
    except (TypeError, ValueError):
        within_days = 1

    return {
        'limit': raw_limit if raw_limit != 0 else None,
        'offset': offset,
        'within_days': within_days,
        'due_only': (args.get('scope') or 'window').strip().lower() == 'due',
        'book_id_filter': (args.get('book_id') or '').strip() or None,
        'chapter_id_filter': normalize_chapter_id(args.get('chapter_id')),
        'now_ms': now_ms,
    }


def _load_quick_memory_rows(user_id: int):
    return load_and_normalize_quick_memory_records(
        user_id,
        list_records=quick_memory_record_repository.list_user_quick_memory_records,
        commit=quick_memory_record_repository.commit,
    )


def build_learning_core_quick_memory_response(user_id: int) -> tuple[dict, int]:
    records = _load_quick_memory_rows(user_id)
    return {'records': [record.to_dict() for record in records]}, 200


def build_learning_core_quick_memory_review_queue_response(user_id: int, args) -> tuple[dict, int]:
    options = _parse_review_queue_options(
        args,
        now_ms=utc_naive_to_epoch_ms(utc_now_naive()),
    )
    return _build_review_queue_payload(user_id=user_id, **options), 200


def _build_review_queue_payload(
    *,
    user_id: int,
    limit: int | None,
    offset: int,
    within_days: int,
    due_only: bool,
    book_id_filter: str | None,
    chapter_id_filter: str | None,
    now_ms: int,
) -> dict:
    window_end_ms = now_ms + within_days * 86400000
    pool_by_word: dict[str, dict] | None = None
    due_words = []
    upcoming_words = []
    context_map: dict[tuple[str, str], dict] = {}
    rows = sorted(
        [row for row in _load_quick_memory_rows(user_id) if (row.next_review or 0) > 0],
        key=lambda row: row.next_review or 0,
    )

    for row in rows:
        word_key = (row.word or '').strip().lower()
        stored_book_id = (row.book_id or '').strip() or None
        stored_chapter_id = normalize_chapter_id(row.chapter_id)
        vocab_item = resolve_quick_memory_vocab_entry(
            word_key,
            book_id=stored_book_id,
            chapter_id=stored_chapter_id,
        )
        fallback_item = None
        if not vocab_item:
            if pool_by_word is None:
                pool_by_word = {
                    (item.get('word') or '').strip().lower(): item
                    for item in get_global_vocab_pool()
                    if (item.get('word') or '').strip()
                }
            fallback_item = pool_by_word.get(word_key)
        if not vocab_item and not fallback_item:
            continue
        item = _build_review_queue_item(
            row=row,
            vocab_item=vocab_item,
            fallback_item=fallback_item,
            stored_book_id=stored_book_id,
            stored_chapter_id=stored_chapter_id,
            now_ms=now_ms,
            window_end_ms=window_end_ms,
            due_only=due_only,
        )
        if item is None:
            continue
        if book_id_filter and item['book_id'] != book_id_filter:
            continue
        if chapter_id_filter and item['chapter_id'] != chapter_id_filter:
            continue

        (due_words if item['dueState'] == 'due' else upcoming_words).append(item)
        _update_context_map(context_map, item)

    return _serialize_review_queue(
        due_words=due_words,
        upcoming_words=upcoming_words,
        context_map=context_map,
        offset=offset,
        limit=limit,
        within_days=within_days,
        book_id_filter=book_id_filter,
        chapter_id_filter=chapter_id_filter,
        due_only=due_only,
    )


def _build_review_queue_item(
    *,
    row,
    vocab_item: dict | None,
    fallback_item: dict | None,
    stored_book_id: str | None,
    stored_chapter_id: str | None,
    now_ms: int,
    window_end_ms: int,
    due_only: bool,
) -> dict | None:
    next_review = row.next_review or 0
    if next_review <= now_ms:
        due_state = 'due'
    elif next_review <= window_end_ms:
        if due_only:
            return None
        due_state = 'upcoming'
    else:
        return None

    effective_book_id = stored_book_id or (vocab_item or {}).get('book_id')
    effective_chapter_id = stored_chapter_id or normalize_chapter_id((vocab_item or {}).get('chapter_id'))
    return {
        **(fallback_item or {}),
        **(vocab_item or {}),
        'status': row.status,
        'knownCount': row.known_count or 0,
        'unknownCount': row.unknown_count or 0,
        'nextReview': next_review,
        'dueState': due_state,
        'book_id': effective_book_id,
        'book_title': (vocab_item or {}).get('book_title') or effective_book_id or '',
        'chapter_id': effective_chapter_id,
        'chapter_title': (vocab_item or {}).get('chapter_title') or (
            f'第{effective_chapter_id}章' if effective_chapter_id is not None else ''
        ),
    }


def _update_context_map(context_map: dict, item: dict) -> None:
    if not item.get('book_id') or item.get('chapter_id') is None:
        return
    context_key = (item['book_id'], item['chapter_id'])
    context = context_map.get(context_key)
    if context is None:
        context = {
            'book_id': item['book_id'],
            'book_title': item['book_title'],
            'chapter_id': item['chapter_id'],
            'chapter_title': item['chapter_title'],
            'due_count': 0,
            'upcoming_count': 0,
            'total_count': 0,
            'next_review': item['nextReview'],
        }
        context_map[context_key] = context
    context['total_count'] += 1
    context['next_review'] = min(context['next_review'], item['nextReview'])
    context['due_count' if item['dueState'] == 'due' else 'upcoming_count'] += 1


def _serialize_review_queue(
    *,
    due_words: list[dict],
    upcoming_words: list[dict],
    context_map: dict,
    offset: int,
    limit: int | None,
    within_days: int,
    book_id_filter: str | None,
    chapter_id_filter: str | None,
    due_only: bool,
) -> dict:
    combined_words = due_words + upcoming_words
    selected = combined_words[offset:offset + limit] if limit is not None else combined_words[offset:]
    total_count = len(combined_words)
    next_offset = offset + len(selected)
    has_more = next_offset < total_count
    contexts = sorted(
        context_map.values(),
        key=lambda context: (
            0 if context['due_count'] > 0 else 1,
            context['next_review'],
            context['book_title'],
            context['chapter_title'],
        ),
    )
    return {
        'words': selected,
        'summary': {
            'due_count': len(due_words),
            'upcoming_count': len(upcoming_words),
            'returned_count': len(selected),
            'review_window_days': within_days,
            'offset': offset,
            'limit': limit,
            'total_count': total_count,
            'has_more': has_more,
            'next_offset': 0 if due_only and has_more else (next_offset if has_more else None),
            'contexts': contexts,
            'selected_context': _select_review_context(
                context_map,
                contexts,
                book_id_filter=book_id_filter,
                chapter_id_filter=chapter_id_filter,
            ),
        },
    }


def _select_review_context(
    context_map: dict,
    contexts: list[dict],
    *,
    book_id_filter: str | None,
    chapter_id_filter: str | None,
) -> dict | None:
    if book_id_filter and chapter_id_filter is not None:
        return context_map.get((book_id_filter, chapter_id_filter))
    if book_id_filter:
        return next((context for context in contexts if context['book_id'] == book_id_filter), None)
    return contexts[0] if contexts else None
