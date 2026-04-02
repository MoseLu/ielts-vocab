from flask import Blueprint, request, jsonify
from models import (
    db, User, UserProgress, UserBookProgress, UserChapterProgress,
    UserWrongWord, UserStudySession, UserAddedBook, UserLearningEvent
)
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from routes.middleware import admin_required
from routes.books import _serialize_effective_book_progress

admin_bp = Blueprint('admin', __name__)


def init_admin(app_instance):
    pass


def _get_effective_book_progress(user_id):
    book_rows = UserBookProgress.query.filter_by(user_id=user_id).all()
    chapter_rows = UserChapterProgress.query.filter_by(user_id=user_id).all()

    progress_by_book = {row.book_id: row for row in book_rows}
    chapters_by_book = {}
    for row in chapter_rows:
        chapters_by_book.setdefault(row.book_id, []).append(row)

    book_ids = set(progress_by_book) | set(chapters_by_book)
    effective_rows = []
    for book_id in book_ids:
        progress = _serialize_effective_book_progress(
            book_id,
            progress_record=progress_by_book.get(book_id),
            chapter_records=chapters_by_book.get(book_id, []),
        )
        if progress:
            effective_rows.append(progress)

    effective_rows.sort(key=lambda row: row.get('updated_at') or '', reverse=True)
    return effective_rows


def _iso_utc(dt):
    if dt is None:
        return None
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + '+00:00'


def _resolve_session_end(session):
    if session.ended_at:
        return session.ended_at
    if session.started_at and (session.duration_seconds or 0) > 0:
        return session.started_at + timedelta(seconds=int(session.duration_seconds or 0))
    return session.started_at


def _collect_session_word_samples(user_id, sessions, sample_limit=6):
    session_windows = []
    lower_bound = None
    upper_bound = None

    for session in sessions:
        start = session.started_at
        end = _resolve_session_end(session)
        if not start or not end:
            continue
        session_windows.append({
            'id': session.id,
            'start': start,
            'end': end,
            'seen': set(),
            'words': [],
            'total': 0,
        })
        lower_bound = start if lower_bound is None else min(lower_bound, start)
        upper_bound = end if upper_bound is None else max(upper_bound, end)

    if not session_windows or lower_bound is None or upper_bound is None:
        return {}

    events = (
        UserLearningEvent.query
        .filter(
            UserLearningEvent.user_id == user_id,
            UserLearningEvent.word.isnot(None),
            UserLearningEvent.event_type.in_(('quick_memory_review', 'wrong_word_recorded')),
            UserLearningEvent.occurred_at >= lower_bound - timedelta(seconds=5),
            UserLearningEvent.occurred_at <= upper_bound + timedelta(seconds=5),
        )
        .order_by(UserLearningEvent.occurred_at.asc(), UserLearningEvent.id.asc())
        .all()
    )

    sorted_windows = sorted(
        session_windows,
        key=lambda item: (item['start'], item['end'], item['id']),
        reverse=True,
    )

    for event in events:
        event_time = event.occurred_at
        word = (event.word or '').strip()
        if not event_time or not word:
            continue

        word_key = word.lower()
        for window in sorted_windows:
            if window['start'] <= event_time <= window['end']:
                if word_key not in window['seen']:
                    window['seen'].add(word_key)
                    window['total'] += 1
                    if len(window['words']) < sample_limit:
                        window['words'].append(word)
                break

    return {
        window['id']: {
            'studied_words': window['words'],
            'studied_words_total': window['total'],
        }
        for window in session_windows
    }


def _user_summary(user):
    """Build a summary dict for a user with aggregated stats."""
    # Book progress totals
    book_rows = _get_effective_book_progress(user.id)
    total_correct = sum(int(r.get('correct_count') or 0) for r in book_rows)
    total_wrong = sum(int(r.get('wrong_count') or 0) for r in book_rows)
    books_completed = sum(1 for r in book_rows if r.get('is_completed'))

    # Study sessions
    sessions = UserStudySession.query.filter_by(user_id=user.id).filter(
        UserStudySession.analytics_clause()
    ).all()
    total_study_seconds = sum(s.duration_seconds or 0 for s in sessions)
    total_words_studied = sum(s.words_studied or 0 for s in sessions)

    # Wrong words count
    wrong_words_count = UserWrongWord.query.filter_by(user_id=user.id).count()

    # Last active (latest session or progress update)
    last_session = (UserStudySession.query.filter_by(user_id=user.id)
                    .filter(UserStudySession.analytics_clause())
                    .order_by(desc(UserStudySession.started_at)).first())
    last_active = None
    if last_session and last_session.started_at:
        last_active = last_session.started_at.isoformat()

    # Session count last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_sessions = UserStudySession.query.filter(
        UserStudySession.user_id == user.id,
        UserStudySession.started_at >= seven_days_ago,
        UserStudySession.analytics_clause(),
    ).count()

    total = total_correct + total_wrong
    accuracy = round(total_correct / total * 100) if total > 0 else 0

    return {
        **user.to_dict(),
        'stats': {
            'total_correct': total_correct,
            'total_wrong': total_wrong,
            'accuracy': accuracy,
            'books_in_progress': len(book_rows),
            'books_completed': books_completed,
            'total_study_seconds': total_study_seconds,
            'total_words_studied': total_words_studied,
            'wrong_words_count': wrong_words_count,
            'session_count': len(sessions),
            'recent_sessions_7d': recent_sessions,
            'last_active': last_active,
        }
    }


# ── Overview stats ─────────────────────────────────────────────────────────────

@admin_bp.route('/overview', methods=['GET'])
@admin_required
def get_overview(current_user):
    """Platform-wide statistics."""
    total_users = User.query.count()

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    active_users_7d = db.session.query(func.count(func.distinct(UserStudySession.user_id))).filter(
        UserStudySession.started_at >= seven_days_ago,
        UserStudySession.analytics_clause(),
    ).scalar() or 0

    today = datetime.utcnow().date()
    active_users_today = db.session.query(func.count(func.distinct(UserStudySession.user_id))).filter(
        func.date(UserStudySession.started_at) == today,
        UserStudySession.analytics_clause(),
    ).scalar() or 0

    total_sessions = UserStudySession.query.filter(UserStudySession.analytics_clause()).count()
    total_study_seconds = db.session.query(func.sum(UserStudySession.duration_seconds)).filter(
        UserStudySession.analytics_clause()
    ).scalar() or 0
    total_words_studied = db.session.query(func.sum(UserStudySession.words_studied)).filter(
        UserStudySession.analytics_clause()
    ).scalar() or 0

    total_correct = db.session.query(func.sum(UserStudySession.correct_count)).filter(
        UserStudySession.analytics_clause()
    ).scalar() or 0
    total_wrong = db.session.query(func.sum(UserStudySession.wrong_count)).filter(
        UserStudySession.analytics_clause()
    ).scalar() or 0
    total_answered = total_correct + total_wrong
    avg_accuracy = round(total_correct / total_answered * 100) if total_answered > 0 else 0

    # New users today / this week
    new_users_today = User.query.filter(func.date(User.created_at) == today).count()
    new_users_7d = User.query.filter(User.created_at >= seven_days_ago).count()

    # Daily activity for last 14 days (sessions per day)
    fourteen_days_ago = datetime.utcnow() - timedelta(days=13)
    daily_rows = db.session.query(
        func.date(UserStudySession.started_at).label('day'),
        func.count(UserStudySession.id).label('sessions'),
        func.count(func.distinct(UserStudySession.user_id)).label('users'),
        func.sum(UserStudySession.duration_seconds).label('study_seconds'),
        func.sum(UserStudySession.words_studied).label('words')
    ).filter(
        UserStudySession.started_at >= fourteen_days_ago,
        UserStudySession.analytics_clause(),
    ).group_by(func.date(UserStudySession.started_at)).order_by('day').all()

    daily_activity = [
        {
            'day': str(row.day),
            'sessions': row.sessions,
            'users': row.users,
            'study_seconds': int(row.study_seconds or 0),
            'words': int(row.words or 0),
        }
        for row in daily_rows
    ]

    # Mode distribution
    mode_rows = db.session.query(
        UserStudySession.mode,
        func.count(UserStudySession.id).label('count'),
        func.sum(UserStudySession.words_studied).label('words')
    ).filter(UserStudySession.analytics_clause()).group_by(UserStudySession.mode).all()

    mode_stats = [
        {'mode': row.mode or '未标注', 'count': row.count, 'words': int(row.words or 0)}
        for row in mode_rows
    ]

    # Top books
    book_rows = db.session.query(
        UserStudySession.book_id,
        func.count(UserStudySession.id).label('sessions'),
        func.count(func.distinct(UserStudySession.user_id)).label('users')
    ).filter(
        UserStudySession.book_id.isnot(None),
        UserStudySession.analytics_clause(),
    ).group_by(
        UserStudySession.book_id
    ).order_by(desc('sessions')).limit(5).all()

    top_books = [
        {'book_id': row.book_id, 'sessions': row.sessions, 'users': row.users}
        for row in book_rows
    ]

    return jsonify({
        'total_users': total_users,
        'active_users_today': active_users_today,
        'active_users_7d': active_users_7d,
        'new_users_today': new_users_today,
        'new_users_7d': new_users_7d,
        'total_sessions': total_sessions,
        'total_study_seconds': int(total_study_seconds),
        'total_words_studied': int(total_words_studied),
        'avg_accuracy': avg_accuracy,
        'daily_activity': daily_activity,
        'mode_stats': mode_stats,
        'top_books': top_books,
    }), 200


# ── Users list ─────────────────────────────────────────────────────────────────

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users(current_user):
    """Paginated user list with summary stats.
    Query params: page, per_page, search, sort (username|created_at|study_time|accuracy), order (asc|desc)
    """
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 20)), 100)
    search = request.args.get('search', '').strip()
    sort = request.args.get('sort', 'created_at')
    order = request.args.get('order', 'desc')

    query = User.query
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) | (User.email.ilike(f'%{search}%'))
        )

    total = query.count()
    users = query.order_by(desc(User.created_at) if order == 'desc' else User.created_at).all()

    # Build summaries (done in Python so we can sort by stats)
    summaries = [_user_summary(u) for u in users]

    # Sort by stat fields if requested
    stat_sort_keys = {
        'study_time': lambda s: s['stats']['total_study_seconds'],
        'accuracy': lambda s: s['stats']['accuracy'],
        'words_studied': lambda s: s['stats']['total_words_studied'],
        'last_active': lambda s: s['stats']['last_active'] or '',
    }
    if sort in stat_sort_keys:
        summaries.sort(key=stat_sort_keys[sort], reverse=(order == 'desc'))
    elif sort == 'username':
        summaries.sort(key=lambda s: s['username'] or '', reverse=(order == 'desc'))

    # Paginate after sort
    start = (page - 1) * per_page
    page_data = summaries[start:start + per_page]

    return jsonify({
        'users': page_data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
    }), 200


# ── Single user detail ─────────────────────────────────────────────────────────

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
