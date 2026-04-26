from __future__ import annotations

from datetime import datetime

from platform_sdk.learning_core_event_application import queue_study_session_logged_event
from platform_sdk.practice_mode_registry import normalize_practice_mode_or_custom
from platform_sdk.study_session_support import resolve_session_activity_capped_end
from service_models.learning_core_models import UserStudySession
from services import learning_event_repository
from services.learning_activity_service import record_learning_activity
from services import study_session_repository
from services.learning_events import record_learning_event


def normalize_client_duration_seconds(
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
    return normalize_practice_mode_or_custom(value, default=None)


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


def _has_direct_session_counts(*, words_studied: int, correct_count: int, wrong_count: int) -> bool:
    return words_studied > 0 or correct_count > 0 or wrong_count > 0


def _resolve_server_activity_capped_end(
    *,
    user_id: int,
    started_at: datetime | None,
    candidate_end: datetime,
    mode: str | None,
    book_id: str | None,
    chapter_id: str | None,
) -> tuple[datetime, bool, datetime | None]:
    if started_at is None or candidate_end <= started_at:
        return candidate_end, False, None

    last_activity_at = learning_event_repository.find_latest_session_activity_at(
        user_id=user_id,
        started_at=started_at,
        end_at=candidate_end,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
    )
    if last_activity_at is None:
        return candidate_end, False, None

    capped_end = resolve_session_activity_capped_end(
        started_at=started_at,
        candidate_end=candidate_end,
        last_activity_at=last_activity_at,
    )
    if capped_end is None or capped_end >= candidate_end:
        return candidate_end, False, last_activity_at
    return capped_end, True, last_activity_at


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


def _queue_study_session_logged_event_if_needed(session: UserStudySession) -> None:
    if session is None or not session.has_activity():
        return
    queue_study_session_logged_event(session)


def _record_study_session_rollups(*, user_id: int, session: UserStudySession, occurred_at: datetime | None) -> None:
    if session is None or not session.has_activity():
        return
    record_learning_activity(
        user_id=user_id,
        book_id=session.book_id,
        mode=session.mode,
        chapter_id=session.chapter_id,
        occurred_at=occurred_at,
        item_delta=session.words_studied or 0,
        duration_delta=session.duration_seconds or 0,
        session_delta=1,
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

    session = study_session_repository.get_user_study_session(user_id, session_id)
    if not session:
        return {'error': 'Session not found'}, 404

    if session.has_activity():
        return {'error': 'Session already contains learning data'}, 409

    study_session_repository.delete_study_session(session)
    study_session_repository.commit()
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
    duration_capped_by_activity = bool(body.get('durationCappedByActivity'))

    words_studied = _coerce_non_negative_int(body.get('wordsStudied', 0))
    correct_count = _coerce_non_negative_int(body.get('correctCount', 0))
    wrong_count = _coerce_non_negative_int(body.get('wrongCount', 0))
    has_direct_counts = _has_direct_session_counts(
        words_studied=words_studied,
        correct_count=correct_count,
        wrong_count=wrong_count,
    )

    if session_id:
        session = study_session_repository.get_user_study_session(user_id, session_id)
        if session:
            if session.ended_at is not None and session.has_activity():
                return {'id': session.id}, 200

            ended_at = _resolve_client_end(
                started_at=session.started_at,
                client_ended_at=client_ended_at,
            )
            activity_capped_end, activity_cap_applied, last_activity_at = _resolve_server_activity_capped_end(
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
            duration_seconds = normalize_client_duration_seconds(
                body.get('durationSeconds', 0),
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
            preserve_recovered_duration = (
                client_ended_at is not None
                and session.started_at is not None
                and client_ended_at > session.started_at
                and duration_seconds > 0
            )
            if not has_direct_counts and last_activity_at is None:
                session.duration_seconds = duration_seconds if preserve_recovered_duration else 0
            else:
                session.duration_seconds = 1 if duration_seconds == 0 and has_direct_counts else duration_seconds
            _record_study_session_event(
                user_id=user_id,
                session=session,
                occurred_at=session.ended_at or ended_at,
            )
            _record_study_session_rollups(
                user_id=user_id,
                session=session,
                occurred_at=session.ended_at or ended_at,
            )
            _queue_study_session_logged_event_if_needed(session)
            study_session_repository.commit()
            return {'id': session.id}, 200

    started_at = parse_client_epoch_ms(body.get('startedAt'))
    duration_seconds = normalize_client_duration_seconds(
        body.get('durationSeconds', 0),
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
        started_at=started_at,
    )
    if pending:
        pending.ended_at = _resolve_client_end(
            started_at=pending.started_at,
            client_ended_at=client_ended_at,
        )
        activity_capped_end, activity_cap_applied, last_activity_at = _resolve_server_activity_capped_end(
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
        preserve_recovered_duration = (
            client_ended_at is not None
            and pending.started_at is not None
            and client_ended_at > pending.started_at
            and computed_duration > 0
        )
        if not has_direct_counts and last_activity_at is None:
            pending.duration_seconds = computed_duration if preserve_recovered_duration else 0
        else:
            pending.duration_seconds = (
                min(duration_seconds, computed_duration)
                if duration_capped_by_activity and duration_seconds > 0
                else max(duration_seconds, computed_duration)
            )
        if pending.duration_seconds == 0 and has_direct_counts:
            pending.duration_seconds = 1
        _record_study_session_event(
            user_id=user_id,
            session=pending,
            occurred_at=pending.ended_at,
        )
        _record_study_session_rollups(
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
    if duration_seconds > 0 and not has_direct_counts and session.started_at is not None:
        last_activity_at = learning_event_repository.find_latest_session_activity_at(
            user_id=user_id,
            started_at=session.started_at,
            end_at=client_ended_at or datetime.utcnow(),
            mode=mode,
            book_id=book_id,
            chapter_id=chapter_id,
        )
        session.duration_seconds = duration_seconds if last_activity_at is not None else 0
    else:
        session.duration_seconds = duration_seconds
    if duration_seconds > 0:
        session.ended_at = _resolve_client_end(
            started_at=session.started_at,
            client_ended_at=client_ended_at,
        )
    study_session_repository.flush()
    _record_study_session_event(
        user_id=user_id,
        session=session,
        occurred_at=session.ended_at or session.started_at,
    )
    _record_study_session_rollups(
        user_id=user_id,
        session=session,
        occurred_at=session.ended_at or session.started_at,
    )
    _queue_study_session_logged_event_if_needed(session)
    study_session_repository.commit()
    return {'id': session.id}, 201


def persist_study_session_response(
    *,
    user_id: int,
    body: dict,
    parse_client_epoch_ms,
    normalize_chapter_id,
    find_pending_session,
) -> tuple[dict, int]:
    try:
        return persist_study_session(
            user_id=user_id,
            body=body,
            parse_client_epoch_ms=parse_client_epoch_ms,
            normalize_chapter_id=normalize_chapter_id,
            find_pending_session=find_pending_session,
        )
    except Exception as exc:
        study_session_repository.rollback()
        return {'error': str(exc)}, 500
