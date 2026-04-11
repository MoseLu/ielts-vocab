from __future__ import annotations

from datetime import datetime, timedelta

from services import (
    admin_overview_repository,
    admin_user_detail_repository,
    admin_user_directory_repository,
    admin_user_session_repository,
)
from services.books_catalog_service import serialize_effective_book_progress


EXCLUDED_ADMIN_PROGRESS_BOOK_IDS = {'ielts_confusable_match'}


def get_effective_book_progress(user_id: int) -> list[dict]:
    book_rows = admin_user_detail_repository.list_user_book_progress_rows(user_id)
    chapter_rows = admin_user_detail_repository.list_user_chapter_progress_rows(user_id)

    progress_by_book = {row.book_id: row for row in book_rows}
    chapters_by_book: dict[str, list] = {}
    for row in chapter_rows:
        chapters_by_book.setdefault(row.book_id, []).append(row)

    book_ids = set(progress_by_book) | set(chapters_by_book)
    effective_rows = []
    for book_id in book_ids:
        if book_id in EXCLUDED_ADMIN_PROGRESS_BOOK_IDS:
            continue
        progress = serialize_effective_book_progress(
            book_id,
            progress_record=progress_by_book.get(book_id),
            chapter_records=chapters_by_book.get(book_id, []),
            user_id=user_id,
        )
        if progress:
            effective_rows.append(progress)

    effective_rows.sort(key=lambda row: row.get('updated_at') or '', reverse=True)
    return effective_rows


def iso_utc(dt) -> str | None:
    if dt is None:
        return None
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + '+00:00'


def resolve_session_end(session) -> datetime | None:
    if session.ended_at:
        return session.ended_at
    if session.started_at and (session.duration_seconds or 0) > 0:
        return session.started_at + timedelta(seconds=int(session.duration_seconds or 0))
    return session.started_at


def collect_session_word_samples(user_id: int, sessions, sample_limit: int = 6) -> dict:
    session_windows = []
    lower_bound = None
    upper_bound = None

    for session in sessions:
        start = session.started_at
        end = resolve_session_end(session)
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

    events = admin_user_detail_repository.list_learning_events_for_sessions(
        user_id,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
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


def user_summary(user) -> dict:
    book_rows = get_effective_book_progress(user.id)
    total_correct = sum(int(row.get('correct_count') or 0) for row in book_rows)
    total_wrong = sum(int(row.get('wrong_count') or 0) for row in book_rows)
    books_completed = sum(1 for row in book_rows if row.get('is_completed'))

    sessions = admin_user_session_repository.list_user_analytics_sessions(user.id)
    total_study_seconds = sum(session.duration_seconds or 0 for session in sessions)
    total_words_studied = sum(session.words_studied or 0 for session in sessions)
    wrong_words_count = admin_user_detail_repository.count_user_wrong_words(user.id)

    last_session = admin_user_session_repository.get_user_last_analytics_session(user.id)
    last_active = last_session.started_at.isoformat() if last_session and last_session.started_at else None

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_sessions = admin_user_session_repository.count_user_recent_analytics_sessions(
        user.id,
        since=seven_days_ago,
    )

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
        },
    }


def build_overview_response() -> tuple[dict, int]:
    total_users = admin_overview_repository.count_total_users()

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    one_day_ago = datetime.utcnow() - timedelta(days=1)
    active_users_7d = admin_overview_repository.count_distinct_active_users_since(seven_days_ago)

    today = datetime.utcnow().date()
    active_users_today = admin_overview_repository.count_distinct_active_users_on(today)

    total_sessions = admin_overview_repository.count_total_analytics_sessions()
    analytics_totals = admin_overview_repository.get_analytics_totals()
    total_study_seconds = analytics_totals['study_seconds']
    total_words_studied = analytics_totals['words_studied']
    total_correct = analytics_totals['correct']
    total_wrong = analytics_totals['wrong']

    total_answered = total_correct + total_wrong
    avg_accuracy = round(total_correct / total_answered * 100) if total_answered > 0 else 0

    new_users_today = admin_overview_repository.count_new_users_on(today)
    new_users_7d = admin_overview_repository.count_new_users_since(seven_days_ago)

    fourteen_days_ago = datetime.utcnow() - timedelta(days=13)
    daily_rows = admin_overview_repository.list_daily_activity_rows(since=fourteen_days_ago)

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

    mode_rows = admin_overview_repository.list_mode_stats_rows()

    mode_stats = [
        {
            'mode': row.mode or '未标注',
            'count': row.count,
            'words': int(row.words or 0),
        }
        for row in mode_rows
    ]

    book_rows = admin_overview_repository.list_top_book_rows(limit=5)
    recent_prompt_rows = admin_overview_repository.list_recent_prompt_run_rows(limit=5)
    recent_tts_rows = admin_overview_repository.list_recent_tts_media_rows(limit=5)

    top_books = [
        {'book_id': row.book_id, 'sessions': row.sessions, 'users': row.users}
        for row in book_rows
    ]

    recent_prompt_runs = [
        {
            'id': row.id,
            'event_id': row.event_id,
            'user_id': row.user_id,
            'run_kind': row.run_kind,
            'provider': row.provider,
            'model': row.model,
            'prompt_excerpt': row.prompt_excerpt,
            'response_excerpt': row.response_excerpt,
            'result_ref': row.result_ref,
            'completed_at': iso_utc(row.completed_at),
        }
        for row in recent_prompt_rows
    ]

    recent_tts_media = [
        {
            'event_id': row.event_id,
            'user_id': row.user_id,
            'media_kind': row.media_kind,
            'media_id': row.media_id,
            'tts_provider': row.tts_provider,
            'storage_provider': row.storage_provider,
            'model': row.model,
            'voice': row.voice,
            'byte_length': int(row.byte_length or 0),
            'generated_at': iso_utc(row.generated_at),
        }
        for row in recent_tts_rows
    ]

    return {
        'total_users': total_users,
        'active_users_today': active_users_today,
        'active_users_7d': active_users_7d,
        'new_users_today': new_users_today,
        'new_users_7d': new_users_7d,
        'total_sessions': total_sessions,
        'total_study_seconds': int(total_study_seconds),
        'total_words_studied': int(total_words_studied),
        'avg_accuracy': avg_accuracy,
        'prompt_run_events_today': admin_overview_repository.count_prompt_run_events_since(one_day_ago),
        'prompt_run_events_7d': admin_overview_repository.count_prompt_run_events_since(seven_days_ago),
        'tts_media_events_today': admin_overview_repository.count_tts_media_events_since(one_day_ago),
        'tts_media_events_7d': admin_overview_repository.count_tts_media_events_since(seven_days_ago),
        'daily_activity': daily_activity,
        'mode_stats': mode_stats,
        'top_books': top_books,
        'recent_prompt_runs': recent_prompt_runs,
        'recent_tts_media': recent_tts_media,
    }, 200


def build_users_response(
    *,
    page: int,
    per_page: int,
    search: str,
    sort: str,
    order: str,
) -> tuple[dict, int]:
    total, users = admin_user_directory_repository.search_users(search=search, order=order)
    summaries = [user_summary(user) for user in users]

    stat_sort_keys = {
        'study_time': lambda summary: summary['stats']['total_study_seconds'],
        'accuracy': lambda summary: summary['stats']['accuracy'],
        'words_studied': lambda summary: summary['stats']['total_words_studied'],
        'last_active': lambda summary: summary['stats']['last_active'] or '',
    }
    if sort in stat_sort_keys:
        summaries.sort(key=stat_sort_keys[sort], reverse=(order == 'desc'))
    elif sort == 'username':
        summaries.sort(key=lambda summary: summary['username'] or '', reverse=(order == 'desc'))

    start = (page - 1) * per_page
    page_data = summaries[start:start + per_page]
    return {
        'users': page_data,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
    }, 200
