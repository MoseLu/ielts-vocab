from __future__ import annotations


def parse_review_queue_options(args, *, normalize_chapter_id, now_ms: int) -> dict:
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


def build_review_queue_payload(
    *,
    user_id: int,
    limit: int | None,
    offset: int,
    within_days: int,
    due_only: bool,
    book_id_filter: str | None,
    chapter_id_filter: str | None,
    now_ms: int,
    normalize_chapter_id,
    load_user_quick_memory_records,
    resolve_quick_memory_vocab_entry,
    get_global_vocab_pool,
) -> dict:
    window_end_ms = now_ms + within_days * 86400000
    pool_by_word: dict[str, dict] | None = None

    due_words = []
    upcoming_words = []
    context_map: dict[tuple[str, str], dict] = {}
    rows = sorted(
        [row for row in load_user_quick_memory_records(user_id) if (row.next_review or 0) > 0],
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

        effective_book_id = stored_book_id or (vocab_item or {}).get('book_id')
        effective_chapter_id = stored_chapter_id or normalize_chapter_id((vocab_item or {}).get('chapter_id'))
        if book_id_filter and effective_book_id != book_id_filter:
            continue
        if chapter_id_filter and effective_chapter_id != chapter_id_filter:
            continue

        next_review = row.next_review or 0
        if next_review <= now_ms:
            due_state = 'due'
        elif next_review <= window_end_ms:
            if due_only:
                continue
            due_state = 'upcoming'
        else:
            continue

        book_title = (vocab_item or {}).get('book_title') or effective_book_id or ''
        chapter_title = (vocab_item or {}).get('chapter_title') or (
            f"第{effective_chapter_id}章" if effective_chapter_id is not None else ''
        )
        item = {
            **(fallback_item or {}),
            **(vocab_item or {}),
            'status': row.status,
            'knownCount': row.known_count or 0,
            'unknownCount': row.unknown_count or 0,
            'nextReview': next_review,
            'dueState': due_state,
            'book_id': effective_book_id,
            'book_title': book_title,
            'chapter_id': effective_chapter_id,
            'chapter_title': chapter_title,
        }
        if due_state == 'due':
            due_words.append(item)
        else:
            upcoming_words.append(item)

        if effective_book_id and effective_chapter_id is not None:
            context_key = (effective_book_id, effective_chapter_id)
            context = context_map.get(context_key)
            if context is None:
                context = {
                    'book_id': effective_book_id,
                    'book_title': book_title,
                    'chapter_id': effective_chapter_id,
                    'chapter_title': chapter_title,
                    'due_count': 0,
                    'upcoming_count': 0,
                    'total_count': 0,
                    'next_review': next_review,
                }
                context_map[context_key] = context

            context['total_count'] += 1
            context['next_review'] = min(context['next_review'], next_review)
            if due_state == 'due':
                context['due_count'] += 1
            else:
                context['upcoming_count'] += 1

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

    selected_context = None
    if book_id_filter and chapter_id_filter is not None:
        selected_context = context_map.get((book_id_filter, chapter_id_filter))
    elif book_id_filter:
        selected_context = next(
            (context for context in contexts if context['book_id'] == book_id_filter),
            None,
        )
    elif contexts:
        selected_context = contexts[0]

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
            'selected_context': selected_context,
        },
    }
