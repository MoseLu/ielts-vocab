from __future__ import annotations

from datetime import datetime

from platform_sdk.ai_vocab_catalog_application import resolve_unique_quick_memory_vocab_context
from platform_sdk.learning_repository_adapters import quick_memory_record_repository
from platform_sdk.local_time_support import resolve_local_day_window, utc_naive_to_epoch_ms, utc_now_naive
from platform_sdk.quick_memory_schedule_support import load_and_normalize_quick_memory_records
from services import learner_profile_repository
from services.learning_events import build_learning_activity_timeline
from services.learner_profile import (
    _build_focus_words,
    _build_memory_system,
    _build_mode_summary,
    _count_pending_wrong_words,
    _has_book_progress_today,
    _has_event_type_today,
    _has_session_mode_today,
    _pick_focus_book,
    _recommend_wrong_dimension,
)


SPEAKING_EVENT_TYPES = (
    'pronunciation_check',
    'speaking_simulation',
    'speaking_assessment_completed',
)
DIMENSION_EVENT_TYPES = (
    'meaning_review',
    'listening_review',
    'writing_review',
    *SPEAKING_EVENT_TYPES,
)


def _load_quick_memory_rows(user_id: int):
    return load_and_normalize_quick_memory_records(
        user_id,
        list_records=quick_memory_record_repository.list_user_quick_memory_records,
        commit=quick_memory_record_repository.commit,
        resolve_vocab_context=resolve_unique_quick_memory_vocab_context,
    )


def _session_started_in_window(session, *, start_dt: datetime, end_dt: datetime) -> bool:
    started_at = getattr(session, 'started_at', None)
    if started_at is None:
        return False
    return start_dt <= started_at < end_dt


def _session_words_studied(session) -> int:
    return max(0, int(getattr(session, 'words_studied', 0) or 0))


def _focus_book_words_today(book_id: str | None, day_sessions) -> int:
    if not book_id:
        return 0
    total = 0
    for session in day_sessions:
        if str(getattr(session, 'book_id', '') or '') != str(book_id):
            continue
        mode = str(getattr(session, 'mode', '') or '').strip().lower()
        if mode in {'quickmemory', 'errors'}:
            continue
        total += _session_words_studied(session)
    return total


def _extract_speaking_activity_flags(day_speaking_events) -> dict[str, bool]:
    has_pronunciation = False
    has_output = False
    has_assessment = False
    has_simulation = False

    for event in day_speaking_events:
        payload = event.payload_dict() if hasattr(event, 'payload_dict') else {}
        event_type = str(getattr(event, 'event_type', '') or '')
        sentence = str(payload.get('sentence') or '').strip()
        response_text = str(payload.get('response_text') or '').strip()
        transcript_excerpt = str(payload.get('transcript_excerpt') or '').strip()
        has_text_output = bool(sentence or response_text or transcript_excerpt)

        if event_type == 'pronunciation_check':
            has_pronunciation = True
            if has_text_output:
                has_output = True
            continue

        if event_type == 'speaking_simulation':
            has_simulation = True
            if has_text_output or int(getattr(event, 'item_count', 0) or 0) > 0:
                has_output = True
            continue

        if event_type == 'speaking_assessment_completed':
            has_assessment = True
            if has_text_output or int(getattr(event, 'item_count', 0) or 0) > 0:
                has_output = True

    return {
        'has_pronunciation_today': has_pronunciation,
        'has_output_today': has_output,
        'has_assessment_today': has_assessment,
        'has_simulation_today': has_simulation,
    }


def build_learning_core_home_todo_signals_payload(
    user_id: int,
    *,
    target_date: str | None = None,
) -> dict:
    now_utc = utc_now_naive()
    date_str, start_dt, end_dt = resolve_local_day_window(target_date, now_utc)
    now_ms = utc_naive_to_epoch_ms(now_utc)

    all_sessions = learner_profile_repository.list_user_analytics_sessions(user_id, before=end_dt)
    day_sessions = [
        session
        for session in all_sessions
        if _session_started_in_window(session, start_dt=start_dt, end_dt=end_dt)
    ]
    wrong_words = learner_profile_repository.list_user_wrong_words_for_profile(user_id)
    smart_rows = learner_profile_repository.list_user_smart_word_stats(user_id)
    quick_memory_rows = _load_quick_memory_rows(user_id)
    focus_words = _build_focus_words(wrong_words)
    focus_book = _pick_focus_book(user_id)
    dimension_events = learner_profile_repository.list_user_learning_events(
        user_id,
        before=end_dt,
        event_types=DIMENSION_EVENT_TYPES,
    )
    day_speaking_events = learner_profile_repository.list_user_learning_events(
        user_id,
        after=start_dt,
        before=end_dt,
        event_types=SPEAKING_EVENT_TYPES,
    )
    activity_timeline = build_learning_activity_timeline(user_id, date_str)
    modes, weakest_mode = _build_mode_summary(all_sessions)
    memory_system = _build_memory_system(
        smart_rows=smart_rows,
        wrong_words=wrong_words,
        focus_words=focus_words,
        qm_rows=quick_memory_rows,
        dimension_events=dimension_events,
        now_ms=now_ms,
        now_utc=now_utc,
    )
    speaking_dimension = next(
        (item for item in (memory_system.get('dimensions') or []) if item.get('key') == 'speaking'),
        None,
    ) or {}

    due_reviews = sum(
        1
        for row in quick_memory_rows
        if (row.next_review or 0) > 0 and (row.next_review or 0) <= now_ms
    )
    pending_wrong_words = _count_pending_wrong_words(wrong_words)
    recommended_dimension, recommended_count = _recommend_wrong_dimension(wrong_words)
    due_review_done_today = (
        due_reviews <= 0
        and (
            _has_session_mode_today(day_sessions, 'quickmemory')
            or _has_event_type_today(activity_timeline, 'quick_memory_review')
        )
    )
    error_review_done_today = pending_wrong_words <= 0 and _has_session_mode_today(day_sessions, 'errors')
    focus_book_done_today = _has_book_progress_today(
        user_id=user_id,
        book_id=(focus_book or {}).get('book_id'),
        day_start=start_dt,
        day_end=end_dt,
        day_sessions=day_sessions,
    )
    focus_book_words_today = _focus_book_words_today((focus_book or {}).get('book_id'), day_sessions)
    speaking_flags = _extract_speaking_activity_flags(day_speaking_events)
    latest_activity = ((activity_timeline.get('recent_events') or [None])[0] or {})

    return {
        'date': date_str,
        'due_review': {
            'pending_count': due_reviews,
            'done_today': due_review_done_today,
        },
        'error_review': {
            'pending_count': pending_wrong_words,
            'recommended_dimension': recommended_dimension,
            'recommended_count': recommended_count,
            'done_today': error_review_done_today,
        },
        'focus_book': None if not focus_book else {
            **focus_book,
            'done_today': focus_book_done_today,
            'words_today': focus_book_words_today,
        },
        'activity': {
            'studied_words': sum(_session_words_studied(session) for session in day_sessions),
            'duration_seconds': int((activity_timeline.get('summary') or {}).get('total_duration_seconds') or 0),
            'sessions': len(day_sessions),
            'latest_activity_title': latest_activity.get('title') or None,
            'latest_activity_at': latest_activity.get('occurred_at') or None,
        },
        'weakest_mode': None if not weakest_mode else {
            'mode': weakest_mode.get('mode'),
            'label': weakest_mode.get('label'),
            'accuracy': weakest_mode.get('accuracy'),
        },
        'speaking': {
            'status': speaking_dimension.get('status') or 'needs_setup',
            'status_label': speaking_dimension.get('status_label') or '待建立',
            'tracked_words': int(speaking_dimension.get('tracked_words') or 0),
            'due_words': int(speaking_dimension.get('due_words') or 0),
            'backlog_words': int(speaking_dimension.get('backlog_words') or 0),
            'accuracy': speaking_dimension.get('accuracy'),
            'focus_words': speaking_dimension.get('focus_words') or [],
            'next_action': speaking_dimension.get('next_action') or '',
            **speaking_flags,
        },
        'modes': modes,
    }


def build_learning_core_home_todo_signals_response(
    user_id: int,
    *,
    target_date: str | None = None,
) -> tuple[dict, int]:
    if target_date:
        try:
            datetime.strptime(target_date, '%Y-%m-%d')
        except ValueError:
            return {'error': 'date must be YYYY-MM-DD'}, 400
    return build_learning_core_home_todo_signals_payload(user_id, target_date=target_date), 200
