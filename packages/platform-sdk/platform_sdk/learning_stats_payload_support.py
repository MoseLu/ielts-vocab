from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Callable

from models import UserChapterProgress, UserStudySession
from platform_sdk.local_time_support import (
    build_time_audit_report,
    collect_eligible_session_intervals,
    current_local_date,
    recent_local_day_range,
    resolve_local_day_window,
    utc_naive_to_local_date_key,
)
from platform_sdk.learning_repository_adapters import learning_stats_repository
from platform_sdk.learning_repository_adapters import learning_event_repository
from platform_sdk.study_session_support import (
    get_live_pending_session_snapshot,
    get_session_window_metrics,
)
from platform_sdk.learning_stats_breakdowns_support import (
    build_chapter_breakdowns,
    build_mode_breakdown,
    build_wrong_top_lists,
    resolve_trend_direction,
    resolve_weakest_mode,
)
from platform_sdk.learning_stats_modes_support import (
    normalize_stats_mode,
    stats_mode_candidates,
)
from platform_sdk.study_session_repository_adapter import (
    find_recent_open_placeholder_session,
    newer_analytics_session_exists,
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

    for date_key, (day_start, day_end) in day_windows.items():
        live_duration_seconds = get_live_pending_window_duration_seconds(
            live_pending,
            window_start=day_start,
            window_end=day_end,
        )
        if live_duration_seconds <= 0:
            continue
        daily[date_key]['duration_seconds'] += live_duration_seconds


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
        total_correct += period_metrics['correct_count']
        total_wrong += period_metrics['wrong_count']

    total_duration = build_time_audit_report(
        sessions=sessions,
        live_pending=filtered_live_pending,
        now=now_utc,
        window_start=since,
        window_end=range_end,
        find_latest_session_activity_at=learning_event_repository.find_latest_session_activity_at,
    ).audited_total_seconds

    return {
        'total_words': total_words,
        'total_duration_seconds': total_duration,
        'total_sessions': len(sessions),
        'accuracy': _accuracy(total_correct, total_wrong),
    }


def _get_live_pending_snapshot(
    user_id: int,
    *,
    mode: str | None = None,
    book_id: str | None = None,
    since: datetime | None = None,
    now_utc: datetime,
) -> dict | None:
    return get_live_pending_session_snapshot(
        user_id,
        find_recent_open_placeholder_session=find_recent_open_placeholder_session,
        newer_analytics_session_exists=newer_analytics_session_exists,
        find_latest_session_activity_at=learning_event_repository.find_latest_session_activity_at,
        mode=mode,
        book_id=book_id,
        since=since,
        now=now_utc,
    )


def build_learning_stats_payload(
    *,
    user_id: int,
    days: int,
    book_id_filter: str | None,
    mode_filter_raw: str | None,
    now_utc: datetime,
    book_title_map: dict[str, str],
    chapter_title_map_resolver: Callable[[str], dict],
    alltime_words_display_resolver: Callable[[int, int], int],
    quick_memory_word_stats_resolver: Callable[[int], dict],
    streak_days_resolver: Callable[[int], int],
) -> dict:
    days = min(int(days or 30), 90)
    mode_filter = normalize_stats_mode(mode_filter_raw) or mode_filter_raw
    mode_filter_candidates = stats_mode_candidates(mode_filter_raw)

    date_keys, since = recent_local_day_range(days, now_utc)
    _, _, range_end = resolve_local_day_window(date_keys[-1], now_utc)
    day_windows = _build_day_windows(date_keys, now_utc)

    session_candidates = learning_stats_repository.list_user_analytics_sessions(
        user_id,
        before=range_end,
        book_id=book_id_filter,
        mode_candidates=mode_filter_candidates,
    )
    sessions = list(collect_eligible_session_intervals(
        session_candidates,
        now=now_utc,
        window_start=since,
        window_end=range_end,
        find_latest_session_activity_at=learning_event_repository.find_latest_session_activity_at,
    ).reportable_sessions)
    daily = defaultdict(_empty_daily_bucket)

    for session in sessions:
        for date_key, (day_start, day_end) in day_windows.items():
            day_metrics = get_session_window_metrics(
                session,
                window_start=day_start,
                window_end=day_end,
                now=now_utc,
            )
            if not day_metrics:
                continue
            daily[date_key]['words_studied'] += day_metrics['words_studied']
            daily[date_key]['correct_count'] += day_metrics['correct_count']
            daily[date_key]['wrong_count'] += day_metrics['wrong_count']
            daily[date_key]['sessions'] += day_metrics['sessions']

    filtered_live_pending = _get_live_pending_snapshot(
        user_id,
        mode=mode_filter,
        book_id=book_id_filter,
        since=since,
        now_utc=now_utc,
    )
    global_live_pending = _get_live_pending_snapshot(
        user_id,
        now_utc=now_utc,
    )
    for date_key, (day_start, day_end) in day_windows.items():
        daily[date_key]['duration_seconds'] = build_time_audit_report(
            sessions=sessions,
            live_pending=filtered_live_pending,
            now=now_utc,
            window_start=day_start,
            window_end=day_end,
            find_latest_session_activity_at=learning_event_repository.find_latest_session_activity_at,
        ).audited_total_seconds

    result = _build_daily_series(date_keys=date_keys, daily=daily)
    fallback_result = _build_fallback_daily_series(
        user_id=user_id,
        date_keys=date_keys,
        since=since,
        book_id_filter=book_id_filter,
    )
    has_session_data = any(
        item['sessions'] > 0 or item['duration_seconds'] > 0
        for item in result
    )
    active_daily = result if has_session_data else fallback_result
    use_fallback = not has_session_data

    books, modes_used, all_user_sessions, all_chapter_progress = _build_filter_options(
        user_id=user_id,
        book_title_map=book_title_map,
        global_live_pending=global_live_pending,
    )
    all_user_sessions = list(collect_eligible_session_intervals(
        all_user_sessions,
        now=now_utc,
        find_latest_session_activity_at=learning_event_repository.find_latest_session_activity_at,
    ).reportable_sessions)

    if use_fallback:
        summary = {
            'total_words': sum(item['words_studied'] for item in active_daily),
            'total_duration_seconds': sum(item['duration_seconds'] for item in active_daily),
            'total_sessions': sum(item['sessions'] for item in active_daily),
            'accuracy': _accuracy(
                sum(item['correct_count'] for item in active_daily),
                sum(item['wrong_count'] for item in active_daily),
            ),
        }
    else:
        summary = _build_period_summary_from_sessions(
            sessions=sessions,
            since=since,
            range_end=range_end,
            now_utc=now_utc,
            filtered_live_pending=filtered_live_pending,
        )

    chapter_words_sum = sum(chapter.words_learned or 0 for chapter in all_chapter_progress)
    alltime_words = alltime_words_display_resolver(user_id, chapter_words_sum)
    alltime_correct = sum(chapter.correct_count or 0 for chapter in all_chapter_progress)
    alltime_wrong = sum(chapter.wrong_count or 0 for chapter in all_chapter_progress)
    alltime_accuracy = _accuracy(alltime_correct, alltime_wrong)

    session_alltime_correct = sum(session.correct_count or 0 for session in all_user_sessions)
    session_alltime_wrong = sum(session.wrong_count or 0 for session in all_user_sessions)
    if alltime_accuracy is None:
        alltime_accuracy = _accuracy(session_alltime_correct, session_alltime_wrong)

    today_str = current_local_date(now_utc).isoformat()
    today_start_dt, today_end_dt = resolve_local_day_window(today_str, now_utc)[1:]
    today_chapters = [
        chapter
        for chapter in all_chapter_progress
        if utc_naive_to_local_date_key(chapter.updated_at) == today_str
    ]
    today_correct = sum(chapter.correct_count or 0 for chapter in today_chapters)
    today_wrong = sum(chapter.wrong_count or 0 for chapter in today_chapters)

    session_today_correct = 0
    session_today_wrong = 0
    for session in all_user_sessions:
        today_metrics = get_session_window_metrics(
            session,
            window_start=today_start_dt,
            window_end=today_end_dt,
            now=now_utc,
        )
        if not today_metrics:
            continue
        session_today_correct += today_metrics['correct_count']
        session_today_wrong += today_metrics['wrong_count']

    today_accuracy = _accuracy(session_today_correct, session_today_wrong)
    if today_accuracy is None:
        today_accuracy = _accuracy(today_correct, today_wrong)

    today_duration = build_time_audit_report(
        sessions=all_user_sessions,
        live_pending=global_live_pending,
        now=now_utc,
        window_start=today_start_dt,
        window_end=today_end_dt,
        find_latest_session_activity_at=learning_event_repository.find_latest_session_activity_at,
    ).audited_total_seconds
    alltime_duration = build_time_audit_report(
        sessions=all_user_sessions,
        live_pending=global_live_pending,
        now=now_utc,
        find_latest_session_activity_at=learning_event_repository.find_latest_session_activity_at,
    ).audited_total_seconds

    mode_breakdown, qm_extra = build_mode_breakdown(
        user_id=user_id,
        all_user_sessions=all_user_sessions,
        global_live_pending=global_live_pending,
        quick_memory_word_stats_resolver=quick_memory_word_stats_resolver,
    )
    history_wrong_top10, pending_wrong_top10 = build_wrong_top_lists(user_id=user_id)
    chapter_breakdown, chapter_mode_stats = build_chapter_breakdowns(
        user_id=user_id,
        all_chapter_progress=all_chapter_progress,
        book_title_map=book_title_map,
        chapter_title_map_resolver=chapter_title_map_resolver,
    )
    weakest_mode = resolve_weakest_mode(mode_breakdown)

    return {
        'daily': active_daily,
        'books': books,
        'modes': modes_used,
        'use_fallback': use_fallback,
        'summary': summary,
        'alltime': {
            'total_words': alltime_words,
            'accuracy': alltime_accuracy,
            'duration_seconds': alltime_duration,
            'today_accuracy': today_accuracy,
            'today_duration_seconds': today_duration,
            'today_new_words': qm_extra['today_new_words'],
            'today_review_words': qm_extra['today_review_words'],
            'alltime_review_words': qm_extra['alltime_review_words'],
            'cumulative_review_events': qm_extra['cumulative_review_events'],
            'ebbinghaus_rate': qm_extra['ebbinghaus_rate'],
            'ebbinghaus_due_total': qm_extra['ebbinghaus_due_total'],
            'ebbinghaus_met': qm_extra['ebbinghaus_met'],
            'qm_word_total': qm_extra['qm_word_total'],
            'ebbinghaus_stages': qm_extra['ebbinghaus_stages'],
            'upcoming_reviews_3d': qm_extra.get('upcoming_reviews_3d', 0),
            'streak_days': streak_days_resolver(user_id),
            'weakest_mode': weakest_mode[0] if weakest_mode else None,
            'weakest_mode_accuracy': weakest_mode[1] if weakest_mode else None,
            'trend_direction': resolve_trend_direction(result),
        },
        'mode_breakdown': mode_breakdown,
        'pie_chart': [
            {'mode': item['mode'], 'value': item['words_studied'], 'sessions': item['sessions']}
            for item in mode_breakdown
        ],
        'wrong_top10': history_wrong_top10,
        'history_wrong_top10': history_wrong_top10,
        'pending_wrong_top10': pending_wrong_top10,
        'chapter_breakdown': chapter_breakdown,
        'chapter_mode_stats': chapter_mode_stats,
    }
