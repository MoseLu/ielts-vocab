from flask import Blueprint, request, jsonify
from models import (
    db, User, UserProgress, UserBookProgress, UserChapterProgress,
    UserWrongWord, UserStudySession, UserAddedBook, UserLearningEvent
)
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from routes.middleware import admin_required
from routes.books import _favorite_words_query, _serialize_effective_book_progress

admin_bp = Blueprint('admin', __name__)
EXCLUDED_ADMIN_PROGRESS_BOOK_IDS = {'ielts_confusable_match'}


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
        if book_id in EXCLUDED_ADMIN_PROGRESS_BOOK_IDS:
            continue
        progress = _serialize_effective_book_progress(
            book_id,
            progress_record=progress_by_book.get(book_id),
            chapter_records=chapters_by_book.get(book_id, []),
            user_id=user_id,
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
