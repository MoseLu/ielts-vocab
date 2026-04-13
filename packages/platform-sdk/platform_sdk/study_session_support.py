from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import UserStudySession

_LIVE_PENDING_SESSION_WINDOW = timedelta(hours=3)
_DEFAULT_PENDING_SESSION_MATCH_WINDOW_SECONDS = 15
_STUDY_SESSION_IDLE_GRACE = timedelta(minutes=5)
STUDY_SESSION_IDLE_GRACE_SECONDS = int(_STUDY_SESSION_IDLE_GRACE.total_seconds())


def _get_session_effective_end(session: UserStudySession, *, now: datetime | None = None) -> datetime | None:
    started_at = session.started_at
    if started_at is None:
        return None

    duration_seconds = max(0, int(session.duration_seconds or 0))
    ended_at = session.ended_at
    if ended_at is not None:
        effective_end = ended_at
        if duration_seconds > 0:
            effective_end = max(effective_end, started_at + timedelta(seconds=duration_seconds))
        if effective_end >= started_at:
            return effective_end

    if duration_seconds > 0:
        return started_at + timedelta(seconds=duration_seconds)

    if now is not None and now > started_at:
        return now

    return started_at


def _get_session_total_duration_seconds(
    session: UserStudySession,
    *,
    now: datetime | None = None,
) -> int:
    started_at = session.started_at
    effective_end = _get_session_effective_end(session, now=now)
    if started_at is None or effective_end is None:
        return 0

    span_seconds = max(0, int((effective_end - started_at).total_seconds()))
    return max(max(0, int(session.duration_seconds or 0)), span_seconds)


def resolve_session_activity_capped_end(
    *,
    started_at: datetime | None,
    candidate_end: datetime | None,
    last_activity_at: datetime | None = None,
    fallback_to_started_at: bool = False,
) -> datetime | None:
    if started_at is None or candidate_end is None:
        return candidate_end

    anchor = None
    if last_activity_at is not None and last_activity_at >= started_at:
        anchor = last_activity_at
    elif fallback_to_started_at:
        anchor = started_at

    if anchor is None:
        return candidate_end

    capped_end = min(candidate_end, anchor + _STUDY_SESSION_IDLE_GRACE)
    return max(started_at, capped_end)


def get_session_window_metrics(
    session: UserStudySession,
    *,
    window_start: datetime,
    window_end: datetime,
    now: datetime | None = None,
) -> dict | None:
    """Project a session onto a UTC window, splitting cross-midnight sessions proportionally."""
    started_at = session.started_at
    effective_end = _get_session_effective_end(session, now=now)
    if started_at is None or effective_end is None:
        return None

    overlap_start = max(started_at, window_start)
    overlap_end = min(effective_end, window_end)
    overlap_seconds = max(0, int((overlap_end - overlap_start).total_seconds()))
    if overlap_seconds <= 0:
        return None

    total_duration_seconds = _get_session_total_duration_seconds(session, now=now)
    ratio = 1.0 if total_duration_seconds <= 0 else min(1.0, overlap_seconds / total_duration_seconds)

    def _allocate(total: int | None) -> int:
        normalized = max(0, int(total or 0))
        if normalized <= 0:
            return 0
        if ratio >= 1.0:
            return normalized
        return min(normalized, max(0, round(normalized * ratio)))

    return {
        'words_studied': _allocate(session.words_studied),
        'correct_count': _allocate(session.correct_count),
        'wrong_count': _allocate(session.wrong_count),
        'duration_seconds': overlap_seconds,
        'sessions': 1,
    }


def get_live_pending_session_snapshot(
    user_id: int,
    *,
    find_recent_open_placeholder_session,
    newer_analytics_session_exists,
    find_latest_session_activity_at=None,
    mode: str | None = None,
    book_id: str | None = None,
    chapter_id: str | None = None,
    since: datetime | None = None,
    now: datetime | None = None,
) -> dict | None:
    """Return the latest recent open placeholder session plus its live elapsed time."""
    now = now or datetime.utcnow()
    threshold = now - _LIVE_PENDING_SESSION_WINDOW
    if since is not None and since > threshold:
        threshold = since

    session = find_recent_open_placeholder_session(
        user_id=user_id,
        threshold=threshold,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
    )
    if session is None or session.started_at is None:
        return None

    newer_analytics_exists = newer_analytics_session_exists(
        user_id=user_id,
        exclude_session_id=session.id,
        started_after=session.started_at,
    )
    if newer_analytics_exists:
        return None

    last_activity_at = None
    if find_latest_session_activity_at is not None:
        last_activity_at = find_latest_session_activity_at(
            user_id=user_id,
            started_at=session.started_at,
            end_at=now,
            mode=session.mode,
            book_id=session.book_id,
            chapter_id=session.chapter_id,
        )

    effective_end = resolve_session_activity_capped_end(
        started_at=session.started_at,
        candidate_end=now,
        last_activity_at=last_activity_at,
        fallback_to_started_at=True,
    )
    if effective_end is None:
        return None

    elapsed_seconds = max(0, int((effective_end - session.started_at).total_seconds()))
    if elapsed_seconds <= 0:
        return None

    return {
        'session': session,
        'elapsed_seconds': elapsed_seconds,
        'effective_end': effective_end,
        'last_activity_at': last_activity_at,
    }


def get_live_pending_window_duration_seconds(
    live_pending: dict | None,
    *,
    window_start: datetime,
    window_end: datetime,
) -> int:
    if not live_pending:
        return 0

    session = live_pending.get('session')
    started_at = getattr(session, 'started_at', None)
    effective_end = live_pending.get('effective_end')
    if started_at is None or effective_end is None:
        return 0

    overlap_start = max(started_at, window_start)
    overlap_end = min(effective_end, window_end)
    return max(0, int((overlap_end - overlap_start).total_seconds()))


def normalize_chapter_id(value) -> str | None:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def find_pending_session(
    *,
    user_id: int,
    mode: str | None,
    book_id: str | None,
    chapter_id: str | None,
    find_pending_session_in_window,
    started_at: datetime | None = None,
    window_seconds: int = _DEFAULT_PENDING_SESSION_MATCH_WINDOW_SECONDS,
):
    now_utc = datetime.utcnow()
    if started_at is not None:
        session = find_pending_session_in_window(
            user_id=user_id,
            mode=mode,
            book_id=book_id,
            chapter_id=chapter_id,
            started_after=started_at - timedelta(seconds=window_seconds),
            started_before=started_at + timedelta(seconds=window_seconds),
        )
    else:
        session = find_pending_session_in_window(
            user_id=user_id,
            mode=mode,
            book_id=book_id,
            chapter_id=chapter_id,
            started_after=now_utc - timedelta(seconds=window_seconds),
        )
    if session or started_at is None:
        return session

    return find_pending_session_in_window(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        started_after=now_utc - timedelta(minutes=30),
    )


def start_or_reuse_study_session(
    *,
    user_id: int,
    mode: str,
    book_id: str | None,
    chapter_id: str | None,
    reuse_window_seconds: int,
    find_pending_session_in_window,
    create_study_session,
    commit,
):
    existing = find_pending_session(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        find_pending_session_in_window=find_pending_session_in_window,
        window_seconds=reuse_window_seconds,
    )
    if existing:
        return existing

    session = create_study_session(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        started_at=datetime.utcnow(),
    )
    commit()
    return session
