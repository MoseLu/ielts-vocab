@ai_bp.route('/learning-stats', methods=['GET'])
@token_required
def get_learning_stats(current_user: User):
    """Return daily aggregated learning stats from study sessions, with optional filters."""
    from collections import defaultdict

    days = min(int(request.args.get('days', 30)), 90)
    book_id_filter = request.args.get('book_id') or None
    mode_filter = request.args.get('mode') or None

    now_utc = utc_now_naive()
    date_keys, since = recent_local_day_range(days, now_utc)
    _, _, range_end = resolve_local_day_window(date_keys[-1], now_utc)
    day_windows = {
        date_key: resolve_local_day_window(date_key, now_utc)[1:]
        for date_key in date_keys
    }
    query = UserStudySession.query.filter(
        UserStudySession.user_id == current_user.id,
        UserStudySession.started_at < range_end,
        UserStudySession.analytics_clause(),
    )
    if book_id_filter:
        query = query.filter(UserStudySession.book_id == book_id_filter)
    if mode_filter:
        query = query.filter(UserStudySession.mode == mode_filter)

    session_candidates = query.all()
    sessions = []
    filtered_live_pending = get_live_pending_session_snapshot(
        current_user.id,
        mode=mode_filter,
        book_id=book_id_filter,
        since=since,
        now=now_utc,
    )
    global_live_pending = get_live_pending_session_snapshot(
        current_user.id,
        now=now_utc,
    )

    # Aggregate by calendar date
    daily = defaultdict(lambda: {
        'words_studied': 0, 'correct_count': 0,
        'wrong_count': 0, 'duration_seconds': 0, 'sessions': 0
    })
    for s in session_candidates:
        period_metrics = get_session_window_metrics(
            s,
            window_start=since,
            window_end=range_end,
            now=now_utc,
        )
        if not period_metrics:
            continue
        sessions.append(s)
        for date_key, (day_start, day_end) in day_windows.items():
            day_metrics = get_session_window_metrics(
                s,
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

    if filtered_live_pending:
        live_session = filtered_live_pending['session']
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

    # Build full date range (oldest → newest)
    result = []
    for d in date_keys:
        day_data = dict(daily.get(d, {
            'words_studied': 0, 'correct_count': 0,
            'wrong_count': 0, 'duration_seconds': 0, 'sessions': 0
        }))
        total = day_data['correct_count'] + day_data['wrong_count']
        day_data['accuracy'] = round(day_data['correct_count'] / total * 100) if total > 0 else None
        result.append({'date': d, **day_data})

    # ── Chapter-progress fallback (when UserStudySession is sparse/empty) ──────
    # Group UserChapterProgress by updated_at date; use words_learned as proxy
    # for words studied that day. Not perfect for multi-day chapters, but much
    # better than showing zeros when the user has real learning history.
    chapter_q = UserChapterProgress.query.filter(
        UserChapterProgress.user_id == current_user.id,
        UserChapterProgress.updated_at >= since,
    )
    if book_id_filter:
        chapter_q = chapter_q.filter(UserChapterProgress.book_id == book_id_filter)
    chapter_rows = chapter_q.all()

    ch_daily: dict = defaultdict(lambda: {'words_studied': 0, 'correct_count': 0, 'wrong_count': 0})
    for cp in chapter_rows:
        dk = utc_naive_to_local_date_key(cp.updated_at)
        if not dk:
            continue
        ch_daily[dk]['words_studied'] += cp.words_learned or 0
        ch_daily[dk]['correct_count'] += cp.correct_count or 0
        ch_daily[dk]['wrong_count'] += cp.wrong_count or 0

    fallback_result = []
    for d in date_keys:
        fd = dict(ch_daily.get(d, {'words_studied': 0, 'correct_count': 0, 'wrong_count': 0}))
        t = fd['correct_count'] + fd['wrong_count']
        fd['accuracy'] = round(fd['correct_count'] / t * 100) if t > 0 else None
        fd['duration_seconds'] = 0
        fd['sessions'] = 0
        fallback_result.append({'date': d, **fd})

    # Decide which daily series to return (sessions preferred)
    has_session_data = any((d['sessions'] > 0 or d['duration_seconds'] > 0) for d in result)
    active_daily = result if has_session_data else fallback_result
    use_fallback = not has_session_data

    # Books and modes the user has ever studied (for filter dropdowns)
    all_sessions = UserStudySession.query.filter_by(user_id=current_user.id).filter(
        UserStudySession.analytics_clause()
    ).all()
    book_ids_from_sessions = {s.book_id for s in all_sessions if s.book_id}
    # Also include books from chapter progress (covers users with no sessions yet)
    all_chapters = UserChapterProgress.query.filter_by(user_id=current_user.id).all()
    book_ids_from_chapters = {cp.book_id for cp in all_chapters if cp.book_id}
    live_session = global_live_pending['session'] if global_live_pending else None
    if live_session and live_session.book_id:
        book_ids_from_sessions.add(live_session.book_id)
    book_ids = list(book_ids_from_sessions | book_ids_from_chapters)
    modes_used = sorted({s.mode for s in all_sessions if s.mode} | ({live_session.mode} if live_session and live_session.mode else set()))

    try:
        from routes.books import VOCAB_BOOKS
        book_title_map = {b['id']: b['title'] for b in VOCAB_BOOKS}
    except Exception:
        book_title_map = {}

    books = [{'id': bid, 'title': book_title_map.get(bid, bid)} for bid in book_ids]

    # Overall summary for the period (use fallback totals when no sessions)
    if use_fallback:
        total_words = sum(d['words_studied'] for d in active_daily)
        total_duration = sum(d['duration_seconds'] for d in active_daily)
        total_correct = sum(d['correct_count'] for d in active_daily)
        total_wrong = sum(d['wrong_count'] for d in active_daily)
        total_sessions = sum(d['sessions'] for d in active_daily)
    else:
        total_words = 0
        total_duration = 0
        total_correct = 0
        total_wrong = 0
        for s in sessions:
            period_metrics = get_session_window_metrics(
                s,
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
        total_sessions = len(sessions)
    total_attempted = total_correct + total_wrong
    period_accuracy = round(total_correct / total_attempted * 100) if total_attempted > 0 else None

    # All-time totals from chapter progress（words_learned 按章相加可能与「全局不重复词」不一致）
    all_chapter_progress = UserChapterProgress.query.filter_by(user_id=current_user.id).all()
    chapter_words_sum = sum(cp.words_learned or 0 for cp in all_chapter_progress)
    alltime_words = _alltime_words_display(current_user.id, chapter_words_sum)
    alltime_correct = sum(cp.correct_count or 0 for cp in all_chapter_progress)
    alltime_wrong = sum(cp.wrong_count or 0 for cp in all_chapter_progress)
    alltime_attempted = alltime_correct + alltime_wrong
    # Session-based duration (only meaningful when sessions exist)
    all_user_sessions = UserStudySession.query.filter_by(user_id=current_user.id).filter(
        UserStudySession.analytics_clause()
    ).all()
    session_alltime_correct = sum(s.correct_count or 0 for s in all_user_sessions)
    session_alltime_wrong = sum(s.wrong_count or 0 for s in all_user_sessions)
    session_alltime_attempted = session_alltime_correct + session_alltime_wrong
    alltime_accuracy = (
        round(alltime_correct / alltime_attempted * 100)
        if alltime_attempted > 0
        else (
            round(session_alltime_correct / session_alltime_attempted * 100)
            if session_alltime_attempted > 0 else None
        )
    )

    # Today's accuracy prefers real session data. Chapter progress can lag behind
    # or reflect only one completed chapter, which can incorrectly pin the day
    # at 100% while same-day practice sessions include mistakes.
    today_str = current_local_date(now_utc).isoformat()
    today_start_dt, today_end_dt = resolve_local_day_window(today_str, now_utc)[1:]
    today_chapters = [cp for cp in all_chapter_progress
                      if utc_naive_to_local_date_key(cp.updated_at) == today_str]
    today_correct = sum(cp.correct_count or 0 for cp in today_chapters)
    today_wrong = sum(cp.wrong_count or 0 for cp in today_chapters)
    today_attempted = today_correct + today_wrong
    session_today_correct = 0
    session_today_wrong = 0
    today_duration = 0
    for s in all_user_sessions:
        today_metrics = get_session_window_metrics(
            s,
            window_start=today_start_dt,
            window_end=today_end_dt,
            now=now_utc,
        )
        if not today_metrics:
            continue
        session_today_correct += today_metrics['correct_count']
        session_today_wrong += today_metrics['wrong_count']
        today_duration += today_metrics['duration_seconds']
    session_today_attempted = session_today_correct + session_today_wrong
    today_accuracy = (
        round(session_today_correct / session_today_attempted * 100)
        if session_today_attempted > 0
        else (
            round(today_correct / today_attempted * 100)
            if today_attempted > 0 else None
        )
    )

    alltime_duration = sum(s.duration_seconds or 0 for s in all_user_sessions)
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

    # ── Per-mode breakdown (all-time, from UserStudySession) ──────────────────
    # 默认 words_studied 按会话累加：同一词在不同模式练习会重复计入；各模式相加通常 > 全局「累计学习新词数」。
    # 速记模式单独用 user_quick_memory_records 行数（每词一行）覆盖，与会话累加口径区分。
    # 跳过 mode 为空的记录：start-session 创建时未写 mode，若 log-session 未带 mode 会一直是 NULL，不应显示为 unknown
    mode_stats: dict = {}
    for s in all_user_sessions:
        m = (s.mode or '').strip()
        if not m:
            continue
        if m not in mode_stats:
            mode_stats[m] = {
                'mode': m,
                'words_studied': 0, 'correct_count': 0,
                'wrong_count': 0, 'duration_seconds': 0, 'sessions': 0,
            }
        mode_stats[m]['words_studied'] += s.words_studied or 0
        mode_stats[m]['correct_count'] += s.correct_count or 0
        mode_stats[m]['wrong_count'] += s.wrong_count or 0
        mode_stats[m]['duration_seconds'] += s.duration_seconds or 0
        mode_stats[m]['sessions'] += 1

    if global_live_pending:
        live_session = global_live_pending['session']
        live_mode = (live_session.mode or '').strip()
        if live_mode:
            bucket = mode_stats.setdefault(live_mode, {
                'mode': live_mode,
                'words_studied': 0,
                'correct_count': 0,
                'wrong_count': 0,
                'duration_seconds': 0,
                'sessions': 0,
            })
            bucket['duration_seconds'] += global_live_pending['elapsed_seconds']

    for md in mode_stats.values():
        attempted = md['correct_count'] + md['wrong_count']
        md['attempts'] = attempted
        md['accuracy'] = round(md['correct_count'] / attempted * 100) if attempted > 0 else None
        sess = md['sessions'] or 0
        md['avg_words_per_session'] = round(md['words_studied'] / sess, 1) if sess else 0.0

    qm_extra = _quick_memory_word_stats(current_user.id)
    qm_total = int(qm_extra.get('qm_word_total') or 0)
    if qm_total > 0:
        if 'quickmemory' not in mode_stats:
            mode_stats['quickmemory'] = {
                'mode': 'quickmemory',
                'words_studied': 0,
                'correct_count': 0,
                'wrong_count': 0,
                'duration_seconds': 0,
                'sessions': 0,
            }
        mode_stats['quickmemory']['words_studied'] = qm_total
        qm_sess = mode_stats['quickmemory']['sessions'] or 0
        mode_stats['quickmemory']['avg_words_per_session'] = (
            round(qm_total / qm_sess, 1) if qm_sess else 0.0
        )

    mode_breakdown = sorted(mode_stats.values(), key=lambda x: x['words_studied'], reverse=True)

    wrong_top = UserWrongWord.query.filter_by(user_id=current_user.id).order_by(
        UserWrongWord.wrong_count.desc()
    ).limit(10).all()
    wrong_top10 = [
        {
            'word': w.word,
            'wrong_count': w.wrong_count or 0,
            'phonetic': w.phonetic or '',
            'pos': w.pos or '',
            'listening_wrong': w.listening_wrong or 0,
            'meaning_wrong': w.meaning_wrong or 0,
            'dictation_wrong': w.dictation_wrong or 0,
        }
        for w in wrong_top
    ]

    chapter_title_cache: dict = {}
    chapter_breakdown = []
    for cp in all_chapter_progress:
        if (cp.correct_count or 0) + (cp.wrong_count or 0) == 0 and (cp.words_learned or 0) == 0:
            continue
        bid = cp.book_id
        if bid not in chapter_title_cache:
            chapter_title_cache[bid] = _chapter_title_map(bid)
        ch_titles = chapter_title_cache[bid]
        ch_key = str(cp.chapter_id)
        tot = (cp.correct_count or 0) + (cp.wrong_count or 0)
        chapter_breakdown.append({
            'book_id': bid,
            'book_title': book_title_map.get(bid, bid),
            'chapter_id': cp.chapter_id,
            'chapter_title': ch_titles.get(ch_key, f'Chapter {cp.chapter_id}'),
            'words_learned': cp.words_learned or 0,
            'correct': cp.correct_count or 0,
            'wrong': cp.wrong_count or 0,
            'accuracy': round((cp.correct_count or 0) / tot * 100) if tot > 0 else None,
        })
    chapter_breakdown.sort(key=lambda x: (x['book_id'], x['chapter_id']))

    chapter_mode_stats = []
    for mp in UserChapterModeProgress.query.filter_by(user_id=current_user.id).all():
        t = (mp.correct_count or 0) + (mp.wrong_count or 0)
        if t == 0:
            continue
        mb = mp.book_id
        if mb not in chapter_title_cache:
            chapter_title_cache[mb] = _chapter_title_map(mb)
        ch_tmap = chapter_title_cache[mb]
        chapter_mode_stats.append({
            'book_id': mb,
            'book_title': book_title_map.get(mb, mb),
            'chapter_id': mp.chapter_id,
            'chapter_title': ch_tmap.get(str(mp.chapter_id), f'Chapter {mp.chapter_id}'),
            'mode': mp.mode,
            'correct': mp.correct_count or 0,
            'wrong': mp.wrong_count or 0,
            'accuracy': round((mp.correct_count or 0) / t * 100),
        })
    chapter_mode_stats.sort(key=lambda x: (x['book_id'], x['chapter_id'], x['mode']))

    pie_chart = [
        {'mode': m['mode'], 'value': m['words_studied'], 'sessions': m['sessions']}
        for m in mode_breakdown
    ]

    # 计算 streak_days
    streak_days = _calc_streak_days(current_user.id)

    # 计算最弱模式（正确率最低且有足够样本的）
    weakest_mode = None
    for md in mode_breakdown:
        acc = md.get('accuracy')
        if acc is not None and md.get('attempts', 0) >= 5:
            if weakest_mode is None or acc < (weakest_mode[1] or 100):
                weakest_mode = (md['mode'], acc)

    # 计算 trend_direction（基于最近14天 vs 前14天对比）
    trend_direction = 'stable'
    if len(result) >= 14:
        recent = result[-7:] if len(result) >= 7 else result[-len(result):]
        older = result[-14:-7] if len(result) >= 14 else result[:-7]
        if older:
            recent_acc = [d['accuracy'] for d in recent if d.get('accuracy') is not None]
            older_acc = [d['accuracy'] for d in older if d.get('accuracy') is not None]
            if recent_acc and older_acc:
                avg_recent = sum(recent_acc) / len(recent_acc)
                avg_older = sum(older_acc) / len(older_acc)
                if avg_recent > avg_older + 5:
                    trend_direction = 'improving'
                elif avg_recent < avg_older - 5:
                    trend_direction = 'declining'

    return jsonify({
        'daily': active_daily,
        'books': books,
        'modes': modes_used,
        'use_fallback': use_fallback,
        'summary': {
            'total_words': total_words,
            'total_duration_seconds': total_duration,
            'total_sessions': total_sessions,
            'accuracy': period_accuracy,
        },
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
            'streak_days': streak_days,
            'weakest_mode': weakest_mode[0] if weakest_mode else None,
            'weakest_mode_accuracy': weakest_mode[1] if weakest_mode else None,
            'trend_direction': trend_direction,
        },
        'mode_breakdown': mode_breakdown,
        'pie_chart': pie_chart,
        'wrong_top10': wrong_top10,
        'chapter_breakdown': chapter_breakdown,
        'chapter_mode_stats': chapter_mode_stats,
    })


@ai_bp.route('/start-session', methods=['POST'])
@token_required
def start_session(current_user: User):
    """Create a session record with server-side start time; returns sessionId for later completion.

    Client should send mode + optional bookId/chapterId so rows are not left with NULL mode
    (vocabulary source: book chapter API, whole book, 30-day plan, or wrong-words list — see PracticePage).
    """
    body = request.get_json() or {}
    mode_raw = (body.get('mode') or 'smart')
    if isinstance(mode_raw, str):
        mode = mode_raw.strip()[:30] or 'smart'
    else:
        mode = 'smart'
    book_id = body.get('bookId') or None
    chapter_id = _normalize_chapter_id(body.get('chapterId'))

    existing = _find_pending_session(
        user_id=current_user.id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        window_seconds=_PENDING_SESSION_REUSE_WINDOW_SECONDS,
    )
    if existing:
        return jsonify({'sessionId': existing.id}), 201

    session = UserStudySession(
        user_id=current_user.id,
        mode=mode,
        book_id=book_id,
        chapter_id=chapter_id,
        started_at=datetime.utcnow(),
    )
    db.session.add(session)
    db.session.commit()
    return jsonify({'sessionId': session.id}), 201


