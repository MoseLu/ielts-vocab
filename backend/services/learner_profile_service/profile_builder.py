from __future__ import annotations

from services import learner_profile_repository, learning_event_repository
from services.local_time import build_time_audit_report, collect_eligible_session_intervals


def _build_daily_plan(
    *,
    summary: dict,
    wrong_words,
    day_sessions,
    activity_timeline: dict,
    day_start: datetime,
    day_end: datetime,
    user_id: int,
) -> dict:
    due_reviews = int(summary.get('due_reviews') or 0)
    pending_wrong_word_count = _count_pending_wrong_words(wrong_words)
    recommended_wrong_dimension, recommended_wrong_count = _recommend_wrong_dimension(wrong_words)
    focus_book = _pick_focus_book(user_id)

    due_review_done_today = (
        due_reviews <= 0
        and (
            _has_session_mode_today(day_sessions, 'quickmemory')
            or _has_event_type_today(activity_timeline, 'quick_memory_review')
        )
    )
    error_review_done_today = pending_wrong_word_count <= 0 and _has_session_mode_today(day_sessions, 'errors')
    focus_book_done_today = _has_book_progress_today(
        user_id=user_id,
        book_id=(focus_book or {}).get('book_id'),
        day_start=day_start,
        day_end=day_end,
        day_sessions=day_sessions,
    )

    latest_activity = (activity_timeline.get('recent_events') or [None])[0] or {}
    today_content = {
        'date': summary.get('date'),
        'studied_words': int(summary.get('today_words') or 0),
        'duration_seconds': int(summary.get('today_duration_seconds') or 0),
        'sessions': int(summary.get('today_sessions') or 0),
        'latest_activity_title': latest_activity.get('title') or None,
        'latest_activity_at': latest_activity.get('occurred_at') or None,
    }

    tasks = [
        {
            'id': 'due-review',
            'kind': 'due-review',
            'title': '到期复习',
            'description': (
                f'还有 {due_reviews} 个到期词需要先回顾。'
                if due_reviews > 0
                else '今天没有积压的到期复习。'
            ),
            'status': 'pending' if due_reviews > 0 else 'completed',
            'completion_source': (
                None
                if due_reviews > 0
                else ('completed_today' if due_review_done_today else 'already_clear')
            ),
            'badge': f'{due_reviews} 词到期' if due_reviews > 0 else '已清空',
            'action': {
                'kind': 'due-review',
                'cta_label': '去复习',
                'mode': 'quickmemory',
                'book_id': None,
                'dimension': None,
            },
        },
        {
            'id': 'error-review',
            'kind': 'error-review',
            'title': '清错词',
            'description': (
                f'还有 {pending_wrong_word_count} 个错词待处理。'
                if pending_wrong_word_count > 0
                else '当前没有待清理的错词。'
            ) if not recommended_wrong_dimension else (
                f'优先处理「{DIMENSION_LABELS.get(recommended_wrong_dimension, recommended_wrong_dimension)}」，还有 {recommended_wrong_count} 个词未过。'
                if pending_wrong_word_count > 0
                else '当前没有待清理的错词。'
            ),
            'status': 'pending' if pending_wrong_word_count > 0 else 'completed',
            'completion_source': (
                None
                if pending_wrong_word_count > 0
                else ('completed_today' if error_review_done_today else 'already_clear')
            ),
            'badge': (
                f'{pending_wrong_word_count} 个待清'
                if pending_wrong_word_count > 0
                else '已清空'
            ),
            'action': {
                'kind': 'error-review',
                'cta_label': '去清错词',
                'mode': _mode_from_wrong_dimension(recommended_wrong_dimension),
                'book_id': None,
                'dimension': recommended_wrong_dimension,
            },
        },
    ]

    if not focus_book:
        tasks.append({
            'id': 'focus-book',
            'kind': 'add-book',
            'title': '添加词书',
            'description': '先加入一本词书，首页才会生成今天的新词主线。',
            'status': 'pending',
            'completion_source': None,
            'badge': '缺少词书',
            'action': {
                'kind': 'add-book',
                'cta_label': '去选词书',
                'mode': None,
                'book_id': None,
                'dimension': None,
            },
        })
    else:
        book_completed = bool(focus_book.get('is_completed'))
        book_status = 'completed' if book_completed or focus_book_done_today else 'pending'
        completion_source = None
        if book_status == 'completed':
            completion_source = 'completed_today' if focus_book_done_today else 'already_clear'

        tasks.append({
            'id': 'focus-book',
            'kind': 'continue-book',
            'title': '推进词书',
            'description': (
                f"继续《{focus_book['title']}》，还剩 {focus_book['remaining_words']} 词。"
                if not book_completed
                else f"《{focus_book['title']}》的主线已经清空。"
            ),
            'status': book_status,
            'completion_source': completion_source,
            'badge': (
                f"{focus_book['progress_percent']}% 已完成"
                if not book_completed
                else '主线已清空'
            ),
            'action': {
                'kind': 'continue-book',
                'cta_label': '继续词书',
                'mode': None,
                'book_id': focus_book['book_id'],
                'dimension': None,
            },
        })

    return {
        'tasks': tasks,
        'today_content': today_content,
        'focus_book': focus_book,
    }


def _build_learner_profile_payload(
    *,
    view: str,
    date_str: str,
    summary: dict,
    dimensions: list[dict],
    focus_words: list[dict],
    repeated_topics: list[dict],
    next_actions: list[str],
    modes: list[dict],
    memory_system: dict | None = None,
    daily_plan: dict | None = None,
    activity_timeline: dict | None = None,
) -> dict:
    payload = {
        'date': date_str,
        'summary': summary,
        'dimensions': dimensions,
        'focus_words': focus_words,
        'repeated_topics': repeated_topics,
        'next_actions': next_actions,
        'mode_breakdown': modes,
    }

    if view == 'stats':
        return payload

    return {
        **payload,
        'memory_system': memory_system or {},
        'daily_plan': daily_plan,
        'activity_summary': (activity_timeline or {}).get('summary') or {},
        'activity_source_breakdown': (activity_timeline or {}).get('source_breakdown') or [],
        'activity_event_breakdown': (activity_timeline or {}).get('event_breakdown') or [],
        'recent_activity': (activity_timeline or {}).get('recent_events') or [],
    }


def build_learner_profile(user_id: int, target_date: str | None = None, view: str = 'full') -> dict:
    profile_view = 'stats' if view == 'stats' else 'full'
    date_str, start_dt, end_dt = _resolve_target_date(target_date)
    now_utc = utc_now_naive()

    all_sessions = learner_profile_repository.list_user_analytics_sessions(
        user_id,
        before=end_dt,
    )
    reportable_all_sessions = list(collect_eligible_session_intervals(
        all_sessions,
        now=now_utc,
        find_latest_session_activity_at=learning_event_repository.find_latest_session_activity_at,
    ).reportable_sessions)
    day_session_candidates = reportable_all_sessions
    day_sessions = []
    day_session_metrics = []
    for session in day_session_candidates:
        window_metrics = get_session_window_metrics(
            session,
            window_start=start_dt,
            window_end=end_dt,
            now=now_utc,
        )
        if not window_metrics:
            continue
        day_sessions.append(session)
        day_session_metrics.append(window_metrics)
    smart_rows = learner_profile_repository.list_user_smart_word_stats(user_id)
    wrong_words = learner_profile_repository.list_user_wrong_words_for_profile(user_id)
    qm_rows = load_user_quick_memory_records(user_id)
    dimension_events = []
    if profile_view != 'stats':
        dimension_events = learner_profile_repository.list_user_learning_events(
            user_id,
            before=end_dt,
            event_types=(
                'listening_review',
                'writing_review',
                'pronunciation_check',
                'speaking_simulation',
                'speaking_assessment_completed',
            ),
        )
    notes = learner_profile_repository.list_user_learning_notes(
        user_id,
        before=end_dt,
        limit=80,
    )

    now_ms = utc_naive_to_epoch_ms(now_utc)
    due_reviews = sum(
        1 for row in qm_rows
        if (row.next_review or 0) > 0 and (row.next_review or 0) <= now_ms
    )

    today_words = sum(item['words_studied'] for item in day_session_metrics)
    today_correct = sum(item['correct_count'] for item in day_session_metrics)
    today_wrong = sum(item['wrong_count'] for item in day_session_metrics)
    today_attempts = today_correct + today_wrong
    today_accuracy = round(today_correct / today_attempts * 100) if today_attempts > 0 else 0
    live_pending = None
    if start_dt <= now_utc < end_dt:
        live_pending = get_live_pending_session_snapshot(
            user_id,
            since=start_dt,
            now=now_utc,
        )
    today_duration = build_time_audit_report(
        sessions=reportable_all_sessions,
        live_pending=live_pending,
        now=now_utc,
        window_start=start_dt,
        window_end=end_dt,
        find_latest_session_activity_at=learning_event_repository.find_latest_session_activity_at,
    ).audited_total_seconds

    modes, weakest_mode = _build_mode_summary(reportable_all_sessions)
    dimensions = _build_dimension_breakdown(smart_rows, wrong_words)
    focus_words = _build_focus_words(wrong_words)
    memory_system = None
    if profile_view != 'stats':
        memory_system = _build_memory_system(
            smart_rows=smart_rows,
            wrong_words=wrong_words,
            focus_words=focus_words,
            qm_rows=qm_rows,
            dimension_events=dimension_events,
            now_ms=now_ms,
            now_utc=now_utc,
        )
    repeated_topics = build_memory_topics(notes, limit=5, include_singletons=False)
    next_actions = _build_next_actions(
        memory_system=memory_system,
        weakest_mode=weakest_mode,
        weak_dimensions=dimensions,
        focus_words=focus_words,
        due_reviews=due_reviews,
    )
    activity_timeline = None
    if profile_view != 'stats':
        activity_timeline = build_learning_activity_timeline(user_id, date_str)

    summary = {
        'date': date_str,
        'today_words': today_words,
        'today_accuracy': today_accuracy,
        'today_duration_seconds': today_duration,
        'today_sessions': len(day_sessions),
        'streak_days': _calc_streak_days(user_id, date_str),
        'weakest_mode': weakest_mode['mode'] if weakest_mode else None,
        'weakest_mode_label': weakest_mode['label'] if weakest_mode else None,
        'weakest_mode_accuracy': weakest_mode['accuracy'] if weakest_mode else None,
        'due_reviews': due_reviews,
        'trend_direction': _build_trend_direction(reportable_all_sessions),
    }
    daily_plan = None
    if profile_view != 'stats':
        daily_plan = _build_daily_plan(
            summary=summary,
            wrong_words=wrong_words,
            day_sessions=day_sessions,
            activity_timeline=activity_timeline or {},
            day_start=start_dt,
            day_end=end_dt,
            user_id=user_id,
        )

    return _build_learner_profile_payload(
        view=profile_view,
        date_str=date_str,
        summary=summary,
        dimensions=dimensions,
        focus_words=focus_words,
        repeated_topics=repeated_topics,
        next_actions=next_actions,
        modes=modes,
        memory_system=memory_system,
        daily_plan=daily_plan,
        activity_timeline=activity_timeline,
    )
