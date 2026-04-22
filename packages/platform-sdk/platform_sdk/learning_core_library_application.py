from __future__ import annotations

from platform_sdk.learning_core_favorites_support import (
    _ensure_favorites_book_membership,
    _favorite_word_count,
    _is_favorites_book,
)
from platform_sdk.books_user_state_repository_adapter import (
    commit as _commit_user_state,
    create_user_added_book,
    delete_row as _delete_user_state_row,
    get_user_added_book,
    list_user_added_books,
)
from platform_sdk.learning_event_support import record_learning_event as queue_learning_event
from platform_sdk.learning_repository_adapters import learning_event_repository
from services.learning_activity_service import (
    get_chapter_mode_rollup_compat_row,
    normalize_learning_mode,
    record_learning_activity,
)


def _mode_progress_snapshot(record) -> dict:
    return {
        'correct_count': max(0, int(getattr(record, 'correct_count', 0) or 0)),
        'wrong_count': max(0, int(getattr(record, 'wrong_count', 0) or 0)),
        'is_completed': bool(getattr(record, 'is_completed', False)),
    }


def _mode_progress_payload(mode: str, snapshot: dict) -> dict:
    total = snapshot['correct_count'] + snapshot['wrong_count']
    return {
        'mode': mode,
        'correct_count': snapshot['correct_count'],
        'wrong_count': snapshot['wrong_count'],
        'accuracy': round(snapshot['correct_count'] / total * 100) if total > 0 else 0,
        'is_completed': snapshot['is_completed'],
        'updated_at': None,
    }


def save_chapter_mode_progress_response(
    user_id: int,
    book_id,
    chapter_id,
    data: dict | None,
) -> tuple[dict, int]:
    payload = data or {}
    mode = normalize_learning_mode(payload.get('mode'))
    if not mode:
        return {'error': '缺少 mode 参数'}, 400

    record = get_chapter_mode_rollup_compat_row(
        user_id,
        book_id=book_id,
        chapter_id=chapter_id,
        mode=mode,
    )
    before_snapshot = _mode_progress_snapshot(record)
    after_snapshot = dict(before_snapshot)
    if 'correct_count' in payload:
        after_snapshot['correct_count'] = max(0, int(payload['correct_count'] or 0))
    if 'wrong_count' in payload:
        after_snapshot['wrong_count'] = max(0, int(payload['wrong_count'] or 0))
    if 'is_completed' in payload:
        after_snapshot['is_completed'] = bool(payload['is_completed'])

    if after_snapshot != before_snapshot:
        queue_learning_event(
            add_learning_event=learning_event_repository.add_learning_event,
            user_id=user_id,
            event_type='chapter_mode_progress_updated',
            source='chapter_mode_progress',
            mode=mode,
            book_id=book_id,
            chapter_id=str(chapter_id),
            correct_count=after_snapshot['correct_count'],
            wrong_count=after_snapshot['wrong_count'],
            payload={'is_completed': after_snapshot['is_completed']},
        )
        record_learning_activity(
            user_id=user_id,
            book_id=book_id,
            mode=mode,
            chapter_id=str(chapter_id),
            correct_count=after_snapshot['correct_count'],
            wrong_count=after_snapshot['wrong_count'],
            is_completed=after_snapshot['is_completed'],
        )

    _commit_user_state()
    updated = get_chapter_mode_rollup_compat_row(
        user_id,
        book_id=book_id,
        chapter_id=chapter_id,
        mode=mode,
    )
    return {
        'mode_progress': updated.to_dict() if updated is not None else _mode_progress_payload(mode, after_snapshot),
    }, 200


def build_my_books_response(user_id: int) -> tuple[dict, int]:
    records = list_user_added_books(user_id)
    return {'book_ids': [record.book_id for record in records]}, 200


def add_my_book_response(user_id: int, data: dict | None) -> tuple[dict, int]:
    payload = data or {}
    book_id = payload.get('book_id')
    if not book_id:
        return {'error': '缺少 book_id'}, 400

    if _is_favorites_book(book_id):
        if _favorite_word_count(user_id) <= 0:
            return {'error': '收藏词书由系统自动创建'}, 400
        _ensure_favorites_book_membership(user_id)
        _commit_user_state()
        return {'book_id': book_id, 'auto_managed': True}, 200

    existing = get_user_added_book(user_id, book_id)
    if existing:
        return {'message': '已在词书中'}, 200

    create_user_added_book(user_id, book_id)
    _commit_user_state()
    return {'book_id': book_id}, 201


def remove_my_book_response(user_id: int, book_id) -> tuple[dict, int]:
    if _is_favorites_book(book_id) and _favorite_word_count(user_id) > 0:
        return {'message': '收藏词书由系统自动管理'}, 200

    record = get_user_added_book(user_id, book_id)
    if record:
        _delete_user_state_row(record)
        _commit_user_state()
    return {'message': '已移除'}, 200
