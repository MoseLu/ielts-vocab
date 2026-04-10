from __future__ import annotations

from datetime import datetime

from platform_sdk.local_time_support import utc_naive_to_epoch_ms, utc_now_naive
from platform_sdk.quick_memory_schedule_support import load_and_normalize_quick_memory_records
from platform_sdk.study_session_repository_adapter import (
    commit as commit_study_session,
    create_study_session,
    delete_study_session,
    find_pending_session_in_window,
    flush as flush_study_session,
    get_user_study_session,
    rollback as rollback_study_session,
)

from platform_sdk.ai_text_support import parse_client_epoch_ms
from platform_sdk.learning_event_support import record_learning_event as queue_learning_event
from platform_sdk.learning_repository_adapters import (
    learning_event_repository,
    quick_memory_record_repository,
)
from platform_sdk.study_session_support import find_pending_session, normalize_chapter_id
from platform_sdk.ai_vocab_catalog_application import (
    get_global_vocab_pool,
    resolve_quick_memory_vocab_entry,
)


def _normalize_client_duration_seconds(
    raw_duration,
    *,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> int:
    try:
        duration_seconds = max(0, int(raw_duration or 0))
    except (TypeError, ValueError):
        duration_seconds = 0

    if started_at is not None and ended_at is not None and ended_at >= started_at:
        elapsed_seconds = max(0, int((ended_at - started_at).total_seconds()))
        if duration_seconds <= 0:
            return elapsed_seconds
        if duration_seconds > 86400 and elapsed_seconds <= 86400:
            return elapsed_seconds
        return max(duration_seconds, elapsed_seconds)

    return 0 if duration_seconds > 86400 else duration_seconds


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
    pool = get_global_vocab_pool()
    pool_by_word = {
        (item.get('word') or '').strip().lower(): item
        for item in pool
        if (item.get('word') or '').strip()
    }

    due_words = []
    upcoming_words = []
    context_map: dict[tuple[str, str], dict] = {}
    rows = sorted(
        [
            row
            for row in load_and_normalize_quick_memory_records(
                user_id,
                list_records=quick_memory_record_repository.list_user_quick_memory_records,
                commit=quick_memory_record_repository.commit,
            )
            if (row.next_review or 0) > 0
        ],
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
            'next_offset': next_offset if has_more else None,
            'contexts': contexts,
            'selected_context': selected_context,
        },
    }


def _normalize_mode(value) -> str | None:
    if isinstance(value, str):
        return value.strip()[:30] or None
    return None


def _resolve_client_end(
    *,
    started_at: datetime | None,
    client_ended_at: datetime | None,
    now_utc: datetime | None = None,
) -> datetime:
    resolved_now = now_utc or datetime.utcnow()
    if (
        client_ended_at is not None
        and started_at is not None
        and client_ended_at >= started_at
        and client_ended_at <= resolved_now
    ):
        return client_ended_at
    return resolved_now


def _coerce_non_negative_int(value) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _record_study_session_event(*, user_id: int, session, occurred_at: datetime | None) -> None:
    queue_learning_event(
        add_learning_event=learning_event_repository.add_learning_event,
        user_id=user_id,
        event_type='study_session',
        source='practice',
        mode=session.mode,
        book_id=session.book_id,
        chapter_id=session.chapter_id,
        item_count=session.words_studied or 0,
        correct_count=session.correct_count or 0,
        wrong_count=session.wrong_count or 0,
        duration_seconds=session.duration_seconds or 0,
        occurred_at=occurred_at,
        payload={
            'session_id': session.id,
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'ended_at': session.ended_at.isoformat() if session.ended_at else None,
        },
    )


def _apply_session_stats(
    session,
    *,
    mode: str | None,
    book_id: str | None,
    chapter_id: str | None,
    words_studied: int,
    correct_count: int,
    wrong_count: int,
) -> None:
    if mode:
        session.mode = mode
    if book_id is not None:
        session.book_id = book_id
    if chapter_id is not None:
        session.chapter_id = chapter_id
    session.words_studied = words_studied
    session.correct_count = correct_count
    session.wrong_count = wrong_count


def cancel_session_response(user_id: int, session_id) -> tuple[dict, int]:
    if not session_id:
        return {'error': 'sessionId is required'}, 400

    session = get_user_study_session(user_id, session_id)
    if not session:
        return {'error': 'Session not found'}, 404
    if session.has_activity():
        return {'error': 'Session already contains learning data'}, 409

    delete_study_session(session)
    commit_study_session()
    return {'deleted': True}, 200


def log_session_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    try:
        mode = _normalize_mode(payload.get('mode'))
        book_id = payload.get('bookId') or None
        chapter_id = normalize_chapter_id(payload.get('chapterId'))
        session_id = payload.get('sessionId')
        client_ended_at = parse_client_epoch_ms(payload.get('endedAt'))

        words_studied = _coerce_non_negative_int(payload.get('wordsStudied', 0))
        correct_count = _coerce_non_negative_int(payload.get('correctCount', 0))
        wrong_count = _coerce_non_negative_int(payload.get('wrongCount', 0))

        if session_id:
            session = get_user_study_session(user_id, session_id)
            if session:
                if session.ended_at is not None and session.has_activity():
                    return {'id': session.id}, 200

                ended_at = _resolve_client_end(
                    started_at=session.started_at,
                    client_ended_at=client_ended_at,
                )
                session.ended_at = ended_at
                computed_duration = max(0, int((ended_at - session.started_at).total_seconds()))
                _apply_session_stats(
                    session,
                    mode=mode,
                    book_id=book_id,
                    chapter_id=chapter_id,
                    words_studied=words_studied,
                    correct_count=correct_count,
                    wrong_count=wrong_count,
                )
                session.duration_seconds = 1 if computed_duration == 0 and session.has_activity() else computed_duration
                _record_study_session_event(
                    user_id=user_id,
                    session=session,
                    occurred_at=session.ended_at or ended_at,
                )
                commit_study_session()
                return {'id': session.id}, 200

        started_at = parse_client_epoch_ms(payload.get('startedAt'))
        duration_seconds = _normalize_client_duration_seconds(
            payload.get('durationSeconds', 0),
            started_at=started_at,
            ended_at=client_ended_at,
        )
        if duration_seconds == 0 and (words_studied > 0 or correct_count > 0 or wrong_count > 0):
            duration_seconds = 1

        pending = find_pending_session(
            user_id=user_id,
            mode=mode,
            book_id=book_id,
            chapter_id=chapter_id,
            find_pending_session_in_window=find_pending_session_in_window,
            started_at=started_at,
        )
        if pending:
            pending.ended_at = _resolve_client_end(
                started_at=pending.started_at,
                client_ended_at=client_ended_at,
            )
            _apply_session_stats(
                pending,
                mode=mode,
                book_id=book_id,
                chapter_id=chapter_id,
                words_studied=words_studied,
                correct_count=correct_count,
                wrong_count=wrong_count,
            )
            computed_duration = max(0, int((pending.ended_at - pending.started_at).total_seconds()))
            pending.duration_seconds = max(duration_seconds, computed_duration)
            if pending.duration_seconds == 0 and pending.has_activity():
                pending.duration_seconds = 1
            _record_study_session_event(
                user_id=user_id,
                session=pending,
                occurred_at=pending.ended_at,
            )
            commit_study_session()
            return {'id': pending.id}, 200

        session = create_study_session(
            user_id=user_id,
            mode=mode,
            book_id=book_id,
            chapter_id=chapter_id,
            started_at=started_at or datetime.utcnow(),
        )
        session.words_studied = words_studied
        session.correct_count = correct_count
        session.wrong_count = wrong_count
        session.duration_seconds = duration_seconds
        if duration_seconds > 0:
            session.ended_at = _resolve_client_end(
                started_at=session.started_at,
                client_ended_at=client_ended_at,
            )
        flush_study_session()
        _record_study_session_event(
            user_id=user_id,
            session=session,
            occurred_at=session.ended_at or session.started_at,
        )
        commit_study_session()
        return {'id': session.id}, 201
    except Exception as exc:
        rollback_study_session()
        return {'error': str(exc)}, 500


def build_quick_memory_response(user_id: int) -> tuple[dict, int]:
    records = load_and_normalize_quick_memory_records(
        user_id,
        list_records=quick_memory_record_repository.list_user_quick_memory_records,
        commit=quick_memory_record_repository.commit,
    )
    return {'records': [record.to_dict() for record in records]}, 200


def build_quick_memory_review_queue_response(user_id: int, args) -> tuple[dict, int]:
    options = _parse_review_queue_options(
        args,
        now_ms=utc_naive_to_epoch_ms(utc_now_naive()),
    )
    payload = _build_review_queue_payload(user_id=user_id, **options)
    return payload, 200
