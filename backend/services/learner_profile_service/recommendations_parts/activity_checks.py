from __future__ import annotations

from datetime import datetime

from services import learner_profile_repository


def _count_pending_wrong_words(wrong_words) -> int:
    pending_count = 0
    for row in wrong_words:
        payload = row.to_dict()
        if int(payload.get('pending_wrong_count') or 0) > 0:
            pending_count += 1
    return pending_count


def _recommend_wrong_dimension(wrong_words) -> tuple[str | None, int]:
    pending_by_dimension = {
        'recognition': 0,
        'listening': 0,
        'meaning': 0,
        'dictation': 0,
    }
    for row in wrong_words:
        payload = row.to_dict()
        for dimension in pending_by_dimension:
            if payload.get(f'{dimension}_pending'):
                pending_by_dimension[dimension] += 1

    top_dimension, top_count = max(
        pending_by_dimension.items(),
        key=lambda item: item[1],
    )
    if top_count <= 0:
        return None, 0
    return top_dimension, top_count


def _mode_from_wrong_dimension(dimension: str | None) -> str | None:
    if dimension == 'recognition':
        return 'quickmemory'
    if dimension == 'listening':
        return 'listening'
    if dimension == 'meaning':
        return 'meaning'
    if dimension == 'dictation':
        return 'dictation'
    return None


def _session_has_learning_progress(session) -> bool:
    return any([
        (session.words_studied or 0) > 0,
        (session.correct_count or 0) > 0,
        (session.wrong_count or 0) > 0,
    ])


def _event_has_learning_progress(event: dict) -> bool:
    payload = event.get('payload') or {}
    return any([
        int(event.get('item_count') or 0) > 0,
        int(event.get('correct_count') or 0) > 0,
        int(event.get('wrong_count') or 0) > 0,
        bool(payload.get('is_completed')),
    ])


def _mode_counts_as_focus_book_progress(mode: str | None) -> bool:
    normalized = (mode or '').strip().lower()
    if not normalized:
        return True
    return normalized not in {'quickmemory', 'errors'}


def _has_book_progress_today(
    *,
    user_id: int,
    book_id: str | None,
    day_start: datetime,
    day_end: datetime,
    day_sessions,
) -> bool:
    if not book_id:
        return False

    for session in day_sessions:
        if str(session.book_id or '') != str(book_id):
            continue
        if _mode_counts_as_focus_book_progress(getattr(session, 'mode', None)) and _session_has_learning_progress(session):
            return True

    book_events = learner_profile_repository.list_user_learning_events(
        user_id,
        book_id=book_id,
        after=day_start,
        before=day_end,
        event_types=('study_session', 'book_progress_updated'),
        descending=True,
    )
    for event in book_events:
        if event.event_type == 'study_session':
            if not _mode_counts_as_focus_book_progress(getattr(event, 'mode', None)):
                continue
            if any([
                (event.item_count or 0) > 0,
                (event.correct_count or 0) > 0,
                (event.wrong_count or 0) > 0,
            ]):
                return True
            continue

        if any([
            (event.correct_count or 0) > 0,
            (event.wrong_count or 0) > 0,
        ]):
            return True

    return False


def _has_book_activity_today(
    *,
    book_id: str | None,
    day_sessions,
    activity_timeline: dict,
) -> bool:
    if not book_id:
        return False

    for session in day_sessions:
        if str(session.book_id or '') != str(book_id):
            continue
        if _session_has_learning_progress(session):
            return True

    for event in activity_timeline.get('recent_events') or []:
        if str(event.get('book_id') or '') != str(book_id):
            continue
        if _event_has_learning_progress(event):
            return True
    return False


def _has_session_mode_today(day_sessions, target_mode: str) -> bool:
    return any(
        (session.mode or '').strip() == target_mode and _session_has_learning_progress(session)
        for session in day_sessions
    )


def _has_event_type_today(activity_timeline: dict, event_type: str) -> bool:
    return any(event.get('event_type') == event_type for event in (activity_timeline.get('recent_events') or []))
