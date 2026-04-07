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

    query = UserStudySession.query.filter(
        UserStudySession.user_id == user_id,
        UserStudySession.started_at < range_end,
        UserStudySession.analytics_clause(),
    )
    if book_id_filter:
        query = query.filter(UserStudySession.book_id == book_id_filter)
    if mode_filter_candidates:
        query = query.filter(UserStudySession.mode.in_(mode_filter_candidates))

    session_candidates = query.all()
    sessions: list[UserStudySession] = []
    daily = defaultdict(_empty_daily_bucket)

    for session in session_candidates:
        period_metrics = get_session_window_metrics(
            session,
            window_start=since,
            window_end=range_end,
            now=now_utc,
        )
        if not period_metrics:
            continue
        sessions.append(session)
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
            daily[date_key]['duration_seconds'] += day_metrics['duration_seconds']
            daily[date_key]['sessions'] += day_metrics['sessions']

    filtered_live_pending = get_live_pending_session_snapshot(
        user_id,
        mode=mode_filter,
        book_id=book_id_filter,
        since=since,
        now=now_utc,
    )
    global_live_pending = get_live_pending_session_snapshot(
        user_id,
        now=now_utc,
    )
    _append_live_pending_duration(
        live_pending=filtered_live_pending,
        daily=daily,
        day_windows=day_windows,
        now_utc=now_utc,
    )

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
    today_duration = 0
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
        today_duration += today_metrics['duration_seconds']

    today_accuracy = _accuracy(session_today_correct, session_today_wrong)
    if today_accuracy is None:
        today_accuracy = _accuracy(today_correct, today_wrong)

    alltime_duration = sum(session.duration_seconds or 0 for session in all_user_sessions)
    if global_live_pending:
        alltime_duration += global_live_pending['elapsed_seconds']
        live_today_metrics = get_session_window_metrics(
            global_live_pending['session'],
            window_start=today_start_dt,
            window_end=today_end_dt,
            now=now_utc,
        )
        if live_today_metrics:
            today_duration += live_today_metrics['duration_seconds']

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
