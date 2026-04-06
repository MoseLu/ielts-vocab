from __future__ import annotations

from datetime import datetime

from models import UserStudySession, db
from services.learning_events import record_learning_event


def normalize_client_duration_seconds(
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


def _record_study_session_event(*, user_id: int, session: UserStudySession, occurred_at: datetime | None) -> None:
    record_learning_event(
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
    session: UserStudySession,
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


def cancel_empty_session(*, user_id: int, session_id) -> tuple[dict, int]:
    if not session_id:
        return {'error': 'sessionId is required'}, 400

    session = UserStudySession.query.filter_by(
        id=session_id,
        user_id=user_id,
    ).first()
    if not session:
        return {'error': 'Session not found'}, 404

    if session.has_activity():
        return {'error': 'Session already contains learning data'}, 409

    db.session.delete(session)
    db.session.commit()
    return {'deleted': True}, 200


def persist_study_session(
    *,
    user_id: int,
    body: dict,
    parse_client_epoch_ms,
    normalize_chapter_id,
    find_pending_session,
) -> tuple[dict, int]:
    mode = _normalize_mode(body.get('mode'))
    book_id = body.get('bookId') or None
    chapter_id = normalize_chapter_id(body.get('chapterId'))
    session_id = body.get('sessionId')
    client_ended_at = parse_client_epoch_ms(body.get('endedAt'))

    words_studied = _coerce_non_negative_int(body.get('wordsStudied', 0))
    correct_count = _coerce_non_negative_int(body.get('correctCount', 0))
    wrong_count = _coerce_non_negative_int(body.get('wrongCount', 0))

    if session_id:
        session = UserStudySession.query.filter_by(id=session_id, user_id=user_id).first()
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
            if computed_duration == 0 and session.has_activity():
                session.duration_seconds = 1
            else:
                session.duration_seconds = computed_duration
            _record_study_session_event(
                user_id=user_id,
                session=session,
                occurred_at=session.ended_at or ended_at,
            )
            db.session.commit()
            return {'id': session.id}, 200

    started_at = parse_client_epoch_ms(body.get('startedAt'))
    duration_seconds = normalize_client_duration_seconds(
        body.get('durationSeconds', 0),
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
        db.session.commit()
        return {'id': pending.id}, 200

    session = UserStudySession(
        user_id=user_id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        words_studied=words_studied,
        correct_count=correct_count,
        wrong_count=wrong_count,
        duration_seconds=duration_seconds,
    )
    if started_at:
        session.started_at = started_at
    if duration_seconds > 0:
        session.ended_at = _resolve_client_end(
            started_at=session.started_at,
            client_ended_at=client_ended_at,
        )
    db.session.add(session)
    db.session.flush()
    _record_study_session_event(
        user_id=user_id,
        session=session,
        occurred_at=session.ended_at or session.started_at,
    )
    db.session.commit()
    return {'id': session.id}, 201
