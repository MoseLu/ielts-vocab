from __future__ import annotations

from datetime import datetime

from platform_sdk.ai_text_support import parse_client_epoch_ms
from platform_sdk.learning_core_event_application import queue_study_session_logged_event
from platform_sdk.learning_core_service_repositories import (
    learning_event_repository,
    study_session_repository,
)
from platform_sdk.learning_event_support import record_learning_event
from platform_sdk.study_session_support import (
    find_pending_session,
    normalize_chapter_id,
    resolve_session_activity_capped_end,
    start_or_reuse_study_session,
)

_PENDING_SESSION_REUSE_WINDOW_SECONDS = 5


def _normalize_start_session_mode(value) -> str:
    if isinstance(value, str):
        return value.strip()[:30] or 'smart'
    return 'smart'


def _normalize_client_duration_seconds(
    raw_duration,
    *,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    trust_client_activity_cap: bool = False,
) -> int:
    try:
        duration_seconds = max(0, int(raw_duration or 0))
    except (TypeError, ValueError):
        duration_seconds = 0

    if started_at is not None and ended_at is not None and ended_at >= started_at:
        elapsed_seconds = max(0, int((ended_at - started_at).total_seconds()))
        if duration_seconds <= 0:
            return elapsed_seconds
        if trust_client_activity_cap:
            return min(duration_seconds, elapsed_seconds)
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


def _resolve_server_activity_capped_end(
    *,
    user_id: int,
    started_at: datetime | None,
    candidate_end: datetime,
    mode: str | None,
    book_id: str | None,
    chapter_id: str | None,
) -> tuple[datetime, bool]:
    if started_at is None or candidate_end <= started_at:
        return candidate_end, False

    last_activity_at = learning_event_repository.find_latest_session_activity_at(
        user_id=user_id,
        started_at=started_at,
        end_at=candidate_end,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
    )
    if last_activity_at is None:
        return candidate_end, False

    capped_end = resolve_session_activity_capped_end(
        started_at=started_at,
        candidate_end=candidate_end,
        last_activity_at=last_activity_at,
    )
    if capped_end is None or capped_end >= candidate_end:
        return candidate_end, False
    return capped_end, True


def _record_study_session_event_locally(*, user_id: int, session, occurred_at: datetime | None) -> None:
    try:
        record_learning_event(
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
    except Exception:
        pass


def _queue_study_session_logged_event_if_needed(session) -> None:
    if session is None or not session.has_activity():
        return
    queue_study_session_logged_event(session)


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


def start_learning_core_session_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    session = start_or_reuse_study_session(
        user_id=user_id,
        mode=_normalize_start_session_mode(payload.get('mode') or 'smart'),
        book_id=payload.get('bookId') or None,
        chapter_id=normalize_chapter_id(payload.get('chapterId')),
        reuse_window_seconds=_PENDING_SESSION_REUSE_WINDOW_SECONDS,
        find_pending_session_in_window=study_session_repository.find_pending_session_in_window,
        create_study_session=study_session_repository.create_study_session,
        commit=study_session_repository.commit,
    )
    return {'sessionId': session.id}, 201


def cancel_learning_core_session_response(user_id: int, session_id) -> tuple[dict, int]:
    if not session_id:
        return {'error': 'sessionId is required'}, 400

    session = study_session_repository.get_user_study_session(user_id, session_id)
    if not session:
        return {'error': 'Session not found'}, 404
    if session.has_activity():
        return {'error': 'Session already contains learning data'}, 409

    study_session_repository.delete_study_session(session)
    study_session_repository.commit()
    return {'deleted': True}, 200


def log_learning_core_session_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    try:
        mode = _normalize_mode(payload.get('mode'))
        book_id = payload.get('bookId') or None
        chapter_id = normalize_chapter_id(payload.get('chapterId'))
        session_id = payload.get('sessionId')
        client_ended_at = parse_client_epoch_ms(payload.get('endedAt'))
        duration_capped_by_activity = bool(payload.get('durationCappedByActivity'))

        words_studied = _coerce_non_negative_int(payload.get('wordsStudied', 0))
        correct_count = _coerce_non_negative_int(payload.get('correctCount', 0))
        wrong_count = _coerce_non_negative_int(payload.get('wrongCount', 0))

        if session_id:
            session = study_session_repository.get_user_study_session(user_id, session_id)
            if session:
                if session.ended_at is not None and session.has_activity():
                    return {'id': session.id}, 200

                ended_at = _resolve_client_end(
                    started_at=session.started_at,
                    client_ended_at=client_ended_at,
                )
                activity_capped_end, activity_cap_applied = _resolve_server_activity_capped_end(
                    user_id=user_id,
                    started_at=session.started_at,
                    candidate_end=ended_at,
                    mode=mode or session.mode,
                    book_id=book_id if book_id is not None else session.book_id,
                    chapter_id=chapter_id if chapter_id is not None else session.chapter_id,
                )
                if activity_cap_applied:
                    ended_at = activity_capped_end
                    duration_capped_by_activity = True
                session.ended_at = ended_at
                duration_seconds = _normalize_client_duration_seconds(
                    payload.get('durationSeconds', 0),
                    started_at=session.started_at,
                    ended_at=ended_at,
                    trust_client_activity_cap=duration_capped_by_activity,
                )
                _apply_session_stats(
                    session,
                    mode=mode,
                    book_id=book_id,
                    chapter_id=chapter_id,
                    words_studied=words_studied,
                    correct_count=correct_count,
                    wrong_count=wrong_count,
                )
                session.duration_seconds = (
                    1 if duration_seconds == 0 and session.has_activity() else duration_seconds
                )
                _record_study_session_event_locally(
                    user_id=user_id,
                    session=session,
                    occurred_at=session.ended_at or ended_at,
                )
                _queue_study_session_logged_event_if_needed(session)
                study_session_repository.commit()
                return {'id': session.id}, 200

        started_at = parse_client_epoch_ms(payload.get('startedAt'))
        duration_seconds = _normalize_client_duration_seconds(
            payload.get('durationSeconds', 0),
            started_at=started_at,
            ended_at=client_ended_at,
            trust_client_activity_cap=duration_capped_by_activity,
        )
        if duration_seconds == 0 and (words_studied > 0 or correct_count > 0 or wrong_count > 0):
            duration_seconds = 1

        pending = find_pending_session(
            user_id=user_id,
            mode=mode,
            book_id=book_id,
            chapter_id=chapter_id,
            find_pending_session_in_window=study_session_repository.find_pending_session_in_window,
            started_at=started_at,
        )
        if pending:
            pending.ended_at = _resolve_client_end(
                started_at=pending.started_at,
                client_ended_at=client_ended_at,
            )
            activity_capped_end, activity_cap_applied = _resolve_server_activity_capped_end(
                user_id=user_id,
                started_at=pending.started_at,
                candidate_end=pending.ended_at,
                mode=mode or pending.mode,
                book_id=book_id if book_id is not None else pending.book_id,
                chapter_id=chapter_id if chapter_id is not None else pending.chapter_id,
            )
            if activity_cap_applied:
                pending.ended_at = activity_capped_end
                duration_capped_by_activity = True
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
            pending.duration_seconds = (
                min(duration_seconds, computed_duration)
                if duration_capped_by_activity and duration_seconds > 0
                else max(duration_seconds, computed_duration)
            )
            if pending.duration_seconds == 0 and pending.has_activity():
                pending.duration_seconds = 1
            _record_study_session_event_locally(
                user_id=user_id,
                session=pending,
                occurred_at=pending.ended_at,
            )
            _queue_study_session_logged_event_if_needed(pending)
            study_session_repository.commit()
            return {'id': pending.id}, 200

        session = study_session_repository.create_study_session(
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
        study_session_repository.flush()
        _record_study_session_event_locally(
            user_id=user_id,
            session=session,
            occurred_at=session.ended_at or session.started_at,
        )
        _queue_study_session_logged_event_if_needed(session)
        study_session_repository.commit()
        return {'id': session.id}, 201
    except Exception as exc:
        study_session_repository.rollback()
        return {'error': str(exc)}, 500
