from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Callable

from models import (
    UserChapterProgress,
    UserStudySession,
)
from services import learning_stats_repository
from services.learning_stats_breakdowns import (
    build_chapter_breakdowns,
    build_mode_breakdown,
    build_wrong_top_lists,
    resolve_trend_direction,
    resolve_weakest_mode,
)
from services.learning_stats_modes import (
    normalize_stats_mode,
    sort_stats_modes,
    stats_mode_candidates,
)
from services.local_time import (
    current_local_date,
    recent_local_day_range,
    resolve_local_day_window,
    utc_naive_to_local_date_key,
)
from services.study_sessions import (
    get_live_pending_session_snapshot,
    get_session_window_metrics,
)


def _empty_daily_bucket() -> dict[str, int]:
    return {
        'words_studied': 0,
        'correct_count': 0,
        'wrong_count': 0,
        'duration_seconds': 0,
        'sessions': 0,
    }


def _build_day_windows(date_keys: list[str], now_utc: datetime) -> dict[str, tuple[datetime, datetime]]:
    return {
        date_key: resolve_local_day_window(date_key, now_utc)[1:]
        for date_key in date_keys
    }


def _accuracy(correct_count: int, wrong_count: int) -> int | None:
    attempted = correct_count + wrong_count
    return round(correct_count / attempted * 100) if attempted > 0 else None


def _append_live_pending_duration(
    *,
    live_pending: dict | None,
    daily: defaultdict,
    day_windows: dict[str, tuple[datetime, datetime]],
    now_utc: datetime,
) -> None:
    if not live_pending:
        return

    live_session = live_pending['session']
    for date_key, (day_start, day_end) in day_windows.items():
        live_metrics = get_session_window_metrics(
            live_session,
            window_start=day_start,
            window_end=day_end,
            now=now_utc,
        )
        if not live_metrics:
            continue
        daily[date_key]['duration_seconds'] += live_metrics['duration_seconds']


def _build_daily_series(
    *,
    date_keys: list[str],
    daily: defaultdict,
) -> list[dict]:
    result = []
    for date_key in date_keys:
        day_data = dict(daily.get(date_key, _empty_daily_bucket()))
        day_data['accuracy'] = _accuracy(
            day_data['correct_count'],
            day_data['wrong_count'],
        )
        result.append({'date': date_key, **day_data})
    return result


def _build_fallback_daily_series(
    *,
    user_id: int,
    date_keys: list[str],
    since: datetime,
    book_id_filter: str | None,
) -> list[dict]:
    chapter_rows = learning_stats_repository.list_user_chapter_progress_rows(
        user_id,
        book_id=book_id_filter,
        updated_since=since,
    )
    chapter_daily = defaultdict(lambda: {
        'words_studied': 0,
        'correct_count': 0,
        'wrong_count': 0,
    })

    for chapter_progress in chapter_rows:
        date_key = utc_naive_to_local_date_key(chapter_progress.updated_at)
        if not date_key:
            continue
        chapter_daily[date_key]['words_studied'] += chapter_progress.words_learned or 0
        chapter_daily[date_key]['correct_count'] += chapter_progress.correct_count or 0
        chapter_daily[date_key]['wrong_count'] += chapter_progress.wrong_count or 0

    fallback_result = []
    for date_key in date_keys:
        fallback_day = dict(chapter_daily.get(date_key, {
            'words_studied': 0,
            'correct_count': 0,
            'wrong_count': 0,
        }))
        fallback_day['accuracy'] = _accuracy(
            fallback_day['correct_count'],
            fallback_day['wrong_count'],
        )
        fallback_day['duration_seconds'] = 0
        fallback_day['sessions'] = 0
        fallback_result.append({'date': date_key, **fallback_day})
    return fallback_result


def _build_filter_options(
    *,
    user_id: int,
    book_title_map: dict[str, str],
    global_live_pending: dict | None,
) -> tuple[list[dict], list[str], list[UserStudySession], list[UserChapterProgress]]:
    all_sessions = learning_stats_repository.list_user_analytics_sessions(user_id)
    all_chapters = learning_stats_repository.list_user_chapter_progress_rows(user_id)

    book_ids_from_sessions = {session.book_id for session in all_sessions if session.book_id}
    book_ids_from_chapters = {chapter.book_id for chapter in all_chapters if chapter.book_id}

    live_session = global_live_pending['session'] if global_live_pending else None
    if live_session and live_session.book_id:
        book_ids_from_sessions.add(live_session.book_id)

    books = [
        {'id': book_id, 'title': book_title_map.get(book_id, book_id)}
        for book_id in (book_ids_from_sessions | book_ids_from_chapters)
    ]
    modes_used = sorted({
        normalized_mode
        for normalized_mode in (
            normalize_stats_mode(session.mode)
            for session in all_sessions
        )
        if normalized_mode
    } | ({
        normalize_stats_mode(live_session.mode)
    } if live_session and normalize_stats_mode(live_session.mode) else set()))

    return books, modes_used, all_sessions, all_chapters


def _build_period_summary_from_sessions(
    *,
    sessions: list[UserStudySession],
    since: datetime,
    range_end: datetime,
    now_utc: datetime,
    filtered_live_pending: dict | None,
) -> dict:
    total_words = 0
    total_duration = 0
    total_correct = 0
    total_wrong = 0

    for session in sessions:
        period_metrics = get_session_window_metrics(
            session,
            window_start=since,
            window_end=range_end,
            now=now_utc,
        )
        if not period_metrics:
            continue
        total_words += period_metrics['words_studied']
        total_duration += period_metrics['duration_seconds']
        total_correct += period_metrics['correct_count']
        total_wrong += period_metrics['wrong_count']

    if filtered_live_pending:
        live_period_metrics = get_session_window_metrics(
            filtered_live_pending['session'],
            window_start=since,
            window_end=range_end,
            now=now_utc,
        )
        if live_period_metrics:
            total_duration += live_period_metrics['duration_seconds']

    return {
        'total_words': total_words,
        'total_duration_seconds': total_duration,
        'total_sessions': len(sessions),
        'accuracy': _accuracy(total_correct, total_wrong),
    }
