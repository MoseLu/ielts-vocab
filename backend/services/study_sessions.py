from __future__ import annotations

from datetime import datetime, timedelta

from models import UserStudySession

_LIVE_PENDING_SESSION_WINDOW = timedelta(hours=3)


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
