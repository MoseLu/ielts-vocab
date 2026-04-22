from __future__ import annotations

from services import books_vocabulary_loader_service
from services.books_favorites_service import (
    _ensure_favorites_book_membership,
    _favorite_word_count,
    _is_favorites_book,
)
from services.learning_activity_service import normalize_learning_mode, record_learning_activity
from services.books_user_state_repository import (
    commit as _commit_user_state,
    create_user_added_book,
    create_user_chapter_mode_progress,
    delete_row as _delete_user_state_row,
    get_user_added_book,
    get_user_chapter_mode_progress,
    list_user_added_books,
)
from services.learning_events import record_learning_event


def _mode_progress_snapshot(record) -> dict:
    return {
        'correct_count': record.correct_count or 0,
        'wrong_count': record.wrong_count or 0,
        'is_completed': bool(record.is_completed),
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

    record = get_user_chapter_mode_progress(user_id, book_id, chapter_id, mode)
    if not record:
        record = create_user_chapter_mode_progress(user_id, book_id, chapter_id, mode)

    before_snapshot = _mode_progress_snapshot(record)
    if 'correct_count' in payload:
        record.correct_count = payload['correct_count']
    if 'wrong_count' in payload:
        record.wrong_count = payload['wrong_count']
    if 'is_completed' in payload:
        record.is_completed = payload['is_completed']

    after_snapshot = _mode_progress_snapshot(record)
    if after_snapshot != before_snapshot:
        record_learning_event(
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
    return {'mode_progress': record.to_dict()}, 200


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


def build_word_examples_response(
    *,
    single_word: str,
    batch_words: str,
) -> tuple[dict, int]:
    single = str(single_word or '').strip().lower()
    batch_raw = str(batch_words or '').strip()

    if single:
        result = {}
        hits = books_vocabulary_loader_service.resolve_unified_examples(single)
        if hits:
            result[single] = hits
        return {'examples': result}, 200

    if batch_raw:
        words = [word.strip().lower() for word in batch_raw.split(',') if word.strip()]
        result = {}
        for word in words:
            hits = books_vocabulary_loader_service.resolve_unified_examples(word)
            if hits:
                result[word] = hits
        return {'examples': result}, 200

    return {'error': 'Provide ?word=<word> or ?words=<word1,word2,...>'}, 400
