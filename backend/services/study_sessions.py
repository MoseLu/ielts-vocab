from __future__ import annotations

from datetime import datetime, timedelta

from models import UserStudySession, db

_LIVE_PENDING_SESSION_WINDOW = timedelta(hours=3)
_DEFAULT_PENDING_SESSION_MATCH_WINDOW_SECONDS = 15


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
    mode: str | None = None,
    book_id: str | None = None,
    chapter_id: str | None = None,
    since: datetime | None = None,
    now: datetime | None = None,
) -> dict | None:
    """Return the latest recent open placeholder session plus its live elapsed time.

    Sessions created by `/start-session` are written immediately with zero counters and
    only become meaningful after `/log-session`. For reporting, we surface at most one
    recent open placeholder so dashboards can reflect the current active study timer
    without also reviving older abandoned placeholders.
    """
    now = now or datetime.utcnow()
    threshold = now - _LIVE_PENDING_SESSION_WINDOW
    if since is not None and since > threshold:
        threshold = since

    query = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(
            UserStudySession.started_at >= threshold,
            UserStudySession.ended_at.is_(None),
            UserStudySession.words_studied == 0,
            UserStudySession.correct_count == 0,
            UserStudySession.wrong_count == 0,
            UserStudySession.duration_seconds == 0,
        )
    )
    if mode is not None:
        query = query.filter(UserStudySession.mode == mode)
    if book_id is not None:
        query = query.filter(UserStudySession.book_id == book_id)
    if chapter_id is not None:
        query = query.filter(UserStudySession.chapter_id == chapter_id)

    session = query.order_by(UserStudySession.started_at.desc(), UserStudySession.id.desc()).first()
    if session is None or session.started_at is None:
        return None

    # If newer finished analytics rows exist, this open placeholder is stale.
    newer_analytics_exists = (
        UserStudySession.query
        .filter(
            UserStudySession.user_id == user_id,
            UserStudySession.id != session.id,
            UserStudySession.started_at > session.started_at,
            UserStudySession.analytics_clause(),
        )
        .first()
        is not None
    )
    if newer_analytics_exists:
        return None

    elapsed_seconds = max(0, int((now - session.started_at).total_seconds()))
    if elapsed_seconds <= 0:
        return None

    return {
        'session': session,
        'elapsed_seconds': elapsed_seconds,
    }


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
    started_at: datetime | None = None,
    window_seconds: int = _DEFAULT_PENDING_SESSION_MATCH_WINDOW_SECONDS,
) -> UserStudySession | None:
    base_query = UserStudySession.query.filter_by(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
    ).filter(
        UserStudySession.ended_at.is_(None),
        UserStudySession.words_studied == 0,
        UserStudySession.correct_count == 0,
        UserStudySession.wrong_count == 0,
        UserStudySession.duration_seconds == 0,
    )

    if started_at is not None:
        query = base_query.filter(
            UserStudySession.started_at >= started_at - timedelta(seconds=window_seconds),
            UserStudySession.started_at <= started_at + timedelta(seconds=window_seconds),
        )
    else:
        query = base_query.filter(
            UserStudySession.started_at >= datetime.utcnow() - timedelta(seconds=window_seconds),
        )

    session = query.order_by(UserStudySession.started_at.desc()).first()
    if session or started_at is None:
        return session

    return base_query.filter(
        UserStudySession.started_at >= datetime.utcnow() - timedelta(minutes=30),
    ).order_by(UserStudySession.started_at.desc()).first()


def start_or_reuse_study_session(
    *,
    user_id: int,
    mode: str,
    book_id: str | None,
    chapter_id: str | None,
    reuse_window_seconds: int,
) -> UserStudySession:
    existing = find_pending_session(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        window_seconds=reuse_window_seconds,
    )
    if existing:
        return existing

    session = UserStudySession(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        started_at=datetime.utcnow(),
    )
    db.session.add(session)
    db.session.commit()
    return session
