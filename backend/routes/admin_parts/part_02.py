@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_detail(current_user, user_id):
    """Detailed stats for a specific user.
    Query params (all optional):
      date_from  YYYY-MM-DD  filter sessions/daily from this date (inclusive)
      date_to    YYYY-MM-DD  filter sessions/daily to this date (inclusive)
      mode       practice mode filter (smart|listening|meaning|dictation|quickmemory|radio)
      book_id    book filter
    """
    user = User.query.get_or_404(user_id)

    # Parse optional filters
    date_from = request.args.get('date_from')   # YYYY-MM-DD string
    date_to   = request.args.get('date_to')     # YYYY-MM-DD string
    f_mode    = request.args.get('mode')
    f_book    = request.args.get('book_id')

    # ── Build filtered session query ──────────────────────────────────────────
    def _apply_filters(q):
        if date_from:
            q = q.filter(UserStudySession.started_at >= date_from)
        if date_to:
            q = q.filter(UserStudySession.started_at <= date_to + ' 23:59:59')
        if f_mode:
            q = q.filter(UserStudySession.mode == f_mode)
        if f_book:
            q = q.filter(UserStudySession.book_id == f_book)
        return q

    # Book progress
    book_progress = _get_effective_book_progress(user_id)

    # Chapter progress (latest 50)
    chapter_progress = [r.to_dict() for r in (
        UserChapterProgress.query.filter_by(user_id=user_id)
        .order_by(desc(UserChapterProgress.updated_at)).limit(50).all()
    )]

    # Wrong words (top by wrong_count)
    wrong_words = [r.to_dict() for r in (
        UserWrongWord.query.filter_by(user_id=user_id)
        .order_by(desc(UserWrongWord.wrong_count)).limit(50).all()
    )]

    # Study sessions — filtered, latest 100
    session_q = _apply_filters(
        UserStudySession.query.filter_by(user_id=user_id).filter(UserStudySession.analytics_clause())
    )
    raw_sessions = session_q.order_by(desc(UserStudySession.started_at)).limit(100).all()
    session_word_samples = _collect_session_word_samples(user_id, raw_sessions)
    sessions = []
    for s in raw_sessions:
        d = s.to_dict()
        derived_end = _resolve_session_end(s)
        d['chapter_id'] = s.chapter_id   # expose chapter for frontend
        d['ended_at'] = _iso_utc(derived_end) if derived_end and derived_end != s.started_at else None
        d.update(session_word_samples.get(s.id, {
            'studied_words': [],
            'studied_words_total': 0,
        }))
        sessions.append(d)

    # Daily aggregation — filtered, last 90 days by default unless date_from given
    daily_base = date_from if date_from else (datetime.utcnow() - timedelta(days=89)).strftime('%Y-%m-%d')
    daily_q = db.session.query(
        func.date(UserStudySession.started_at).label('day'),
        func.sum(UserStudySession.duration_seconds).label('seconds'),
        func.sum(UserStudySession.words_studied).label('words'),
        func.sum(UserStudySession.correct_count).label('correct'),
        func.sum(UserStudySession.wrong_count).label('wrong'),
    ).filter(
        UserStudySession.user_id == user_id,
        UserStudySession.started_at >= daily_base,
        UserStudySession.analytics_clause(),
    )
    if date_to:
        daily_q = daily_q.filter(UserStudySession.started_at <= date_to + ' 23:59:59')
    if f_mode:
        daily_q = daily_q.filter(UserStudySession.mode == f_mode)
    if f_book:
        daily_q = daily_q.filter(UserStudySession.book_id == f_book)
    daily_q = daily_q.group_by(func.date(UserStudySession.started_at)).order_by('day')

    daily_study = [
        {
            'day': str(row.day),
            'seconds': int(row.seconds or 0),
            'words': int(row.words or 0),
            'correct': int(row.correct or 0),
            'wrong': int(row.wrong or 0),
        }
        for row in daily_q.all()
    ]

    # Chapter×day×mode aggregation — multi-dimensional view
    # Groups: book_id, chapter_id, date, mode → correct/wrong/words/seconds/sessions
    chapter_daily_q = db.session.query(
        UserStudySession.book_id,
        UserStudySession.chapter_id,
        func.date(UserStudySession.started_at).label('day'),
        UserStudySession.mode,
        func.count(UserStudySession.id).label('sessions'),
        func.sum(UserStudySession.words_studied).label('words'),
        func.sum(UserStudySession.correct_count).label('correct'),
        func.sum(UserStudySession.wrong_count).label('wrong'),
        func.sum(UserStudySession.duration_seconds).label('seconds'),
    ).filter(
        UserStudySession.user_id == user_id,
        UserStudySession.chapter_id.isnot(None),
        UserStudySession.chapter_id != '',
        UserStudySession.analytics_clause(),
    )

    chapter_daily_q = _apply_filters(chapter_daily_q)
    if not date_from:
        chapter_daily_q = chapter_daily_q.filter(
            UserStudySession.started_at >= (datetime.utcnow() - timedelta(days=89)).strftime('%Y-%m-%d')
        )

    chapter_daily_q = chapter_daily_q.group_by(
        UserStudySession.book_id,
        UserStudySession.chapter_id,
        func.date(UserStudySession.started_at),
        UserStudySession.mode,
    ).order_by(desc(func.date(UserStudySession.started_at)))

    chapter_daily = [
        {
            'book_id': r.book_id or '',
            'chapter_id': r.chapter_id or '',
            'day': str(r.day),
            'mode': r.mode or '',
            'sessions': r.sessions,
            'words': int(r.words or 0),
            'correct': int(r.correct or 0),
            'wrong': int(r.wrong or 0),
            'seconds': int(r.seconds or 0),
        }
        for r in chapter_daily_q.limit(500).all()
    ]

    return jsonify({
        'user': _user_summary(user),
        'book_progress': book_progress,
        'chapter_progress': chapter_progress,
        'wrong_words': wrong_words,
        'sessions': sessions,
        'daily_study': daily_study,
        'chapter_daily': chapter_daily,
    }), 200


# ── Manage admin status ────────────────────────────────────────────────────────

@admin_bp.route('/users/<int:user_id>/set-admin', methods=['POST'])
@admin_required
def set_admin(current_user, user_id):
    """Grant or revoke admin privileges."""
    if current_user.id == user_id:
        return jsonify({'error': '不能修改自己的管理员状态'}), 400
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    user.is_admin = bool(data.get('is_admin', False))
    db.session.commit()
    return jsonify({'message': '已更新', 'user': user.to_dict()}), 200
