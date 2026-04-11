from __future__ import annotations

from datetime import datetime, timedelta

from platform_sdk.admin_overview_application import (
    collect_session_word_samples,
    get_effective_book_progress,
    iso_utc,
    resolve_session_end,
    user_summary,
)
from platform_sdk.cross_service_boundary import build_strict_internal_contract_error
from platform_sdk.admin_repository_adapters import (
    admin_user_detail_repository,
    admin_user_directory_repository,
    admin_user_session_repository,
)


def _parse_wrong_word_iso_timestamp(value) -> float:
    if not isinstance(value, str) or not value.strip():
        return 0.0
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except ValueError:
        return 0.0


def _resolve_wrong_word_last_error(record: dict) -> str | None:
    dimension_states = record.get('dimension_states')
    last_wrong_candidates = []
    if isinstance(dimension_states, dict):
        for dimension in ('recognition', 'meaning', 'listening', 'dictation'):
            state = dimension_states.get(dimension)
            if not isinstance(state, dict):
                continue
            last_wrong_at = state.get('last_wrong_at') or state.get('lastWrongAt')
            if _parse_wrong_word_iso_timestamp(last_wrong_at) > 0:
                last_wrong_candidates.append(last_wrong_at)
    if last_wrong_candidates:
        return max(last_wrong_candidates, key=_parse_wrong_word_iso_timestamp)
    fallback_updated_at = record.get('updated_at')
    return fallback_updated_at if _parse_wrong_word_iso_timestamp(fallback_updated_at) > 0 else None


def get_sorted_wrong_words(user_id: int, sort_mode: str) -> list[dict]:
    wrong_words = [row.to_dict() for row in admin_user_detail_repository.list_user_wrong_word_rows(user_id)]
    for record in wrong_words:
        record['last_wrong_at'] = _resolve_wrong_word_last_error(record)

    if sort_mode == 'wrong_count':
        wrong_words.sort(
            key=lambda record: (
                -int(record.get('wrong_count') or 0),
                -_parse_wrong_word_iso_timestamp(record.get('last_wrong_at')),
                (record.get('word') or '').lower(),
            )
        )
    else:
        wrong_words.sort(
            key=lambda record: (
                -_parse_wrong_word_iso_timestamp(record.get('last_wrong_at')),
                -int(record.get('wrong_count') or 0),
                (record.get('word') or '').lower(),
            )
        )
    return wrong_words[:50]


def get_favorite_words(user_id: int) -> list[dict]:
    return [row.to_dict() for row in admin_user_detail_repository.list_user_favorite_word_rows(user_id)]


def build_user_detail_response(
    user_id: int,
    *,
    date_from: str | None,
    date_to: str | None,
    mode: str | None,
    book_id: str | None,
    wrong_words_sort: str | None,
) -> tuple[dict, int]:
    user = admin_user_directory_repository.get_user(user_id)
    if user is None:
        return {'error': '用户不存在'}, 404

    sort_mode = wrong_words_sort if wrong_words_sort in ('last_error', 'wrong_count') else 'last_error'
    try:
        book_progress = get_effective_book_progress(user_id)
        chapter_progress = [
            row.to_dict()
            for row in admin_user_detail_repository.list_user_chapter_progress_rows(user_id, limit=50)
        ]
        wrong_words = get_sorted_wrong_words(user_id, sort_mode)
        favorite_words = get_favorite_words(user_id)

        raw_sessions = admin_user_session_repository.list_user_filtered_analytics_sessions(
            user_id,
            date_from=date_from,
            date_to=date_to,
            mode=mode,
            book_id=book_id,
        )
        session_word_samples = collect_session_word_samples(user_id, raw_sessions)
        sessions = []
        for session in raw_sessions:
            payload = session.to_dict()
            derived_end = resolve_session_end(session)
            payload['chapter_id'] = session.chapter_id
            payload['ended_at'] = iso_utc(derived_end) if derived_end and derived_end != session.started_at else None
            payload.update(session_word_samples.get(session.id, {'studied_words': [], 'studied_words_total': 0}))
            sessions.append(payload)

        base_since = (datetime.utcnow() - timedelta(days=89)).strftime('%Y-%m-%d')
        daily_base = date_from or base_since
        return {
            'user': user_summary(user),
            'book_progress': book_progress,
            'chapter_progress': chapter_progress,
            'wrong_words': wrong_words,
            'favorite_words': favorite_words,
            'sessions': sessions,
            'daily_study': [
                {
                    'day': str(row.day),
                    'seconds': int(row.seconds or 0),
                    'words': int(row.words or 0),
                    'correct': int(row.correct or 0),
                    'wrong': int(row.wrong or 0),
                }
                for row in admin_user_session_repository.list_user_daily_study_rows(
                    user_id,
                    daily_base=daily_base,
                    date_to=date_to,
                    mode=mode,
                    book_id=book_id,
                )
            ],
            'chapter_daily': [
                {
                    'book_id': row.book_id or '',
                    'chapter_id': row.chapter_id or '',
                    'day': str(row.day),
                    'mode': row.mode or '',
                    'sessions': row.sessions,
                    'words': int(row.words or 0),
                    'correct': int(row.correct or 0),
                    'wrong': int(row.wrong or 0),
                    'seconds': int(row.seconds or 0),
                }
                for row in admin_user_session_repository.list_user_chapter_daily_rows(
                    user_id,
                    date_from=date_from,
                    date_to=date_to,
                    mode=mode,
                    book_id=book_id,
                    default_since=base_since,
                    limit=500,
                )
            ],
        }, 200
    except admin_user_detail_repository.LearningCoreAdminDetailUnavailable as exc:
        return build_strict_internal_contract_error(
            upstream_name='learning-core-service',
            action=exc.action,
        )


def set_admin_response(current_admin_id: int, target_user_id: int, data: dict | None) -> tuple[dict, int]:
    if current_admin_id == target_user_id:
        return {'error': '不能修改自己的管理员状态'}, 400

    user = admin_user_directory_repository.get_user(target_user_id)
    if user is None:
        return {'error': '用户不存在'}, 404

    updated = admin_user_directory_repository.set_user_admin(
        user,
        is_admin=bool((data or {}).get('is_admin', False)),
    )
    return {'message': '已更新', 'user': updated.to_dict()}, 200
