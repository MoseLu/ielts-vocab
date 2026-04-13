from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from platform_sdk.study_session_support import (
    _get_session_effective_end,
    get_live_pending_window_duration_seconds,
)


SESSION_ACTIVITY_SOURCES = (
    'practice',
    'quickmemory',
    'practice_reset',
    'wrong_words',
    'chapter_progress',
    'chapter_mode_progress',
    'book_progress',
)


@dataclass(frozen=True)
class TimeInterval:
    start: datetime
    end: datetime
    source: str
    session_id: int | None = None
    mode: str | None = None

    @property
    def duration_seconds(self) -> int:
        return max(0, int((self.end - self.start).total_seconds()))

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['start'] = self.start.isoformat()
        payload['end'] = self.end.isoformat()
        payload['duration_seconds'] = self.duration_seconds
        return payload


@dataclass
class SessionIntervalCollection:
    intervals: list[TimeInterval]
    reportable_sessions: list[Any]
    zero_activity_sessions: list[dict[str, Any]]
    event_backed_sessions: list[dict[str, Any]]


@dataclass
class TimeAuditReport:
    raw_session_seconds: int
    deduped_session_seconds: int
    live_pending_seconds: int
    audited_total_seconds: int
    excluded_session_seconds: int
    session_count: int
    merged_interval_count: int
    overlap_pairs: list[dict[str, Any]]
    zero_activity_sessions: list[dict[str, Any]]
    event_backed_sessions: list[dict[str, Any]]
    event_gaps: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def session_has_direct_activity(session) -> bool:
    return any(
        int(getattr(session, field, 0) or 0) > 0
        for field in ('words_studied', 'correct_count', 'wrong_count')
    )


def _clip_interval(
    *,
    start_at: datetime | None,
    end_at: datetime | None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> tuple[datetime, datetime] | None:
    if start_at is None or end_at is None or end_at <= start_at:
        return None
    clipped_start = max(start_at, window_start) if window_start is not None else start_at
    clipped_end = min(end_at, window_end) if window_end is not None else end_at
    if clipped_end <= clipped_start:
        return None
    return clipped_start, clipped_end


def _build_session_interval(
    session,
    *,
    now: datetime | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> TimeInterval | None:
    started_at = getattr(session, 'started_at', None)
    effective_end = _get_session_effective_end(session, now=now)
    clipped = _clip_interval(
        start_at=started_at,
        end_at=effective_end,
        window_start=window_start,
        window_end=window_end,
    )
    if clipped is None:
        return None
    start_at, end_at = clipped
    return TimeInterval(
        start=start_at,
        end=end_at,
        source='session',
        session_id=getattr(session, 'id', None),
        mode=getattr(session, 'mode', None),
    )


def _resolve_session_activity_evidence(
    session,
    *,
    now: datetime | None = None,
    find_latest_session_activity_at=None,
) -> datetime | None:
    if find_latest_session_activity_at is None:
        return None
    started_at = getattr(session, 'started_at', None)
    effective_end = _get_session_effective_end(session, now=now)
    if started_at is None or effective_end is None or effective_end <= started_at:
        return None
    return find_latest_session_activity_at(
        user_id=getattr(session, 'user_id'),
        started_at=started_at,
        end_at=effective_end,
        mode=getattr(session, 'mode', None),
        book_id=getattr(session, 'book_id', None),
        chapter_id=getattr(session, 'chapter_id', None),
    )


def _serialize_session_audit_row(
    session,
    *,
    interval: TimeInterval,
    event_activity_at: datetime | None,
) -> dict[str, Any]:
    return {
        'session_id': getattr(session, 'id', None),
        'mode': getattr(session, 'mode', None),
        'book_id': getattr(session, 'book_id', None),
        'chapter_id': getattr(session, 'chapter_id', None),
        'started_at': getattr(session, 'started_at', None).isoformat()
        if getattr(session, 'started_at', None) is not None else None,
        'ended_at': getattr(session, 'ended_at', None).isoformat()
        if getattr(session, 'ended_at', None) is not None else None,
        'effective_end': interval.end.isoformat(),
        'duration_seconds': int(getattr(session, 'duration_seconds', 0) or 0),
        'window_duration_seconds': interval.duration_seconds,
        'event_activity_at': event_activity_at.isoformat() if event_activity_at is not None else None,
    }


def collect_eligible_session_intervals(
    sessions,
    *,
    now: datetime | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    find_latest_session_activity_at=None,
) -> SessionIntervalCollection:
    intervals: list[TimeInterval] = []
    reportable_sessions: list[Any] = []
    zero_activity_sessions: list[dict[str, Any]] = []
    event_backed_sessions: list[dict[str, Any]] = []

    for session in sessions:
        interval = _build_session_interval(
            session,
            now=now,
            window_start=window_start,
            window_end=window_end,
        )
        if interval is None:
            continue
        if session_has_direct_activity(session):
            intervals.append(interval)
            reportable_sessions.append(session)
            continue

        event_activity_at = _resolve_session_activity_evidence(
            session,
            now=now,
            find_latest_session_activity_at=find_latest_session_activity_at,
        )
        audit_row = _serialize_session_audit_row(
            session,
            interval=interval,
            event_activity_at=event_activity_at,
        )
        if event_activity_at is None:
            zero_activity_sessions.append(audit_row)
            continue
        intervals.append(interval)
        reportable_sessions.append(session)
        event_backed_sessions.append(audit_row)

    return SessionIntervalCollection(
        intervals=intervals,
        reportable_sessions=reportable_sessions,
        zero_activity_sessions=zero_activity_sessions,
        event_backed_sessions=event_backed_sessions,
    )


def filter_reportable_sessions(
    sessions,
    *,
    now: datetime | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    find_latest_session_activity_at=None,
) -> list[Any]:
    return collect_eligible_session_intervals(
        sessions,
        now=now,
        window_start=window_start,
        window_end=window_end,
        find_latest_session_activity_at=find_latest_session_activity_at,
    ).reportable_sessions


def merge_overlapping_intervals(intervals: list[TimeInterval]) -> list[TimeInterval]:
    if not intervals:
        return []
    ordered = sorted(intervals, key=lambda item: (item.start, item.end, item.session_id or 0))
    merged: list[TimeInterval] = [ordered[0]]
    for interval in ordered[1:]:
        previous = merged[-1]
        if interval.start > previous.end:
            merged.append(interval)
            continue
        merged[-1] = TimeInterval(
            start=previous.start,
            end=max(previous.end, interval.end),
            source='merged',
        )
    return merged


def sum_interval_seconds(intervals: list[TimeInterval]) -> int:
    return sum(interval.duration_seconds for interval in intervals)


def audit_zero_activity_duration_sessions(
    sessions,
    *,
    now: datetime | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    find_latest_session_activity_at=None,
) -> list[dict[str, Any]]:
    return collect_eligible_session_intervals(
        sessions,
        now=now,
        window_start=window_start,
        window_end=window_end,
        find_latest_session_activity_at=find_latest_session_activity_at,
    ).zero_activity_sessions


def audit_live_pending_interval(
    live_pending: dict | None,
    *,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
) -> dict[str, Any] | None:
    if not live_pending:
        return None
    session = live_pending.get('session')
    started_at = getattr(session, 'started_at', None)
    effective_end = live_pending.get('effective_end')
    clipped = _clip_interval(
        start_at=started_at,
        end_at=effective_end,
        window_start=window_start,
        window_end=window_end,
    )
    if clipped is None:
        return None
    start_at, end_at = clipped
    interval = TimeInterval(
        start=start_at,
        end=end_at,
        source='live_pending',
        session_id=getattr(session, 'id', None),
        mode=getattr(session, 'mode', None),
    )
    return {
        'interval': interval,
        'duration_seconds': get_live_pending_window_duration_seconds(
            live_pending,
            window_start=start_at,
            window_end=end_at,
        ),
    }


def _build_overlap_pairs(intervals: list[TimeInterval]) -> list[dict[str, Any]]:
    overlap_pairs: list[dict[str, Any]] = []
    ordered = sorted(intervals, key=lambda item: (item.start, item.end, item.session_id or 0))
    for index, interval in enumerate(ordered):
        for other in ordered[index + 1:]:
            if other.start >= interval.end:
                break
            overlap_start = max(interval.start, other.start)
            overlap_end = min(interval.end, other.end)
            overlap_seconds = max(0, int((overlap_end - overlap_start).total_seconds()))
            if overlap_seconds <= 0:
                continue
            overlap_pairs.append({
                'left_session_id': interval.session_id,
                'right_session_id': other.session_id,
                'left_mode': interval.mode,
                'right_mode': other.mode,
                'overlap_seconds': overlap_seconds,
                'overlap_start': overlap_start.isoformat(),
                'overlap_end': overlap_end.isoformat(),
            })
    return overlap_pairs


def audit_event_reconciliation(
    *,
    user_id: int | None,
    merged_intervals: list[TimeInterval],
    window_start: datetime,
    window_end: datetime,
    list_learning_events_in_window=None,
) -> list[dict[str, Any]]:
    if user_id is None or list_learning_events_in_window is None:
        return []
    events = list_learning_events_in_window(
        user_id,
        start_at=window_start,
        end_at=window_end,
    )
    gaps: list[dict[str, Any]] = []
    for event in events:
        source = getattr(event, 'source', None)
        event_type = getattr(event, 'event_type', None)
        occurred_at = getattr(event, 'occurred_at', None)
        if source not in SESSION_ACTIVITY_SOURCES or event_type == 'study_session' or occurred_at is None:
            continue
        covered = any(interval.start <= occurred_at < interval.end for interval in merged_intervals)
        if covered:
            continue
        gaps.append({
            'event_type': event_type,
            'source': source,
            'mode': getattr(event, 'mode', None),
            'book_id': getattr(event, 'book_id', None),
            'chapter_id': getattr(event, 'chapter_id', None),
            'occurred_at': occurred_at.isoformat(),
        })
    return gaps


def build_time_audit_report(
    *,
    user_id: int | None = None,
    sessions,
    live_pending: dict | None = None,
    now: datetime | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    find_latest_session_activity_at=None,
    list_learning_events_in_window=None,
) -> TimeAuditReport:
    collection = collect_eligible_session_intervals(
        sessions,
        now=now,
        window_start=window_start,
        window_end=window_end,
        find_latest_session_activity_at=find_latest_session_activity_at,
    )
    raw_session_seconds = sum_interval_seconds(collection.intervals)
    merged_session_intervals = merge_overlapping_intervals(collection.intervals)
    deduped_session_seconds = sum_interval_seconds(merged_session_intervals)

    live_pending_row = audit_live_pending_interval(
        live_pending,
        window_start=window_start,
        window_end=window_end,
    )
    live_pending_seconds = int(live_pending_row['duration_seconds']) if live_pending_row else 0

    merged_total_intervals = merged_session_intervals
    if live_pending_row is not None:
        merged_total_intervals = merge_overlapping_intervals(
            [*collection.intervals, live_pending_row['interval']],
        )

    event_gaps: list[dict[str, Any]] = []
    if window_start is not None and window_end is not None:
        event_gaps = audit_event_reconciliation(
            user_id=user_id,
            merged_intervals=merged_total_intervals,
            window_start=window_start,
            window_end=window_end,
            list_learning_events_in_window=list_learning_events_in_window,
        )

    return TimeAuditReport(
        raw_session_seconds=raw_session_seconds,
        deduped_session_seconds=deduped_session_seconds,
        live_pending_seconds=live_pending_seconds,
        audited_total_seconds=sum_interval_seconds(merged_total_intervals),
        excluded_session_seconds=sum(
            int(item.get('window_duration_seconds') or 0)
            for item in collection.zero_activity_sessions
        ),
        session_count=len(collection.reportable_sessions),
        merged_interval_count=len(merged_total_intervals),
        overlap_pairs=_build_overlap_pairs(collection.intervals),
        zero_activity_sessions=collection.zero_activity_sessions,
        event_backed_sessions=collection.event_backed_sessions,
        event_gaps=event_gaps,
    )


__all__ = [
    'SESSION_ACTIVITY_SOURCES',
    'SessionIntervalCollection',
    'TimeAuditReport',
    'TimeInterval',
    'audit_event_reconciliation',
    'audit_live_pending_interval',
    'audit_zero_activity_duration_sessions',
    'build_time_audit_report',
    'collect_eligible_session_intervals',
    'filter_reportable_sessions',
    'merge_overlapping_intervals',
    'session_has_direct_activity',
    'sum_interval_seconds',
]
