from __future__ import annotations

from collections import defaultdict

from platform_sdk.books_user_state_repository_adapter import (
    commit as _commit_user_state,
    create_user_book_progress,
    create_user_chapter_progress,
    get_user_book_progress,
    get_user_chapter_progress,
    list_user_book_progress_rows,
    list_user_chapter_mode_progress_rows,
    list_user_chapter_progress_rows,
)
from platform_sdk.catalog_provider_adapter import serialize_effective_book_progress
from platform_sdk.learning_event_support import record_learning_event as queue_learning_event
from platform_sdk.learning_repository_adapters import (
    learning_event_repository,
    legacy_progress_repository,
)


def list_legacy_progress(user_id: int) -> list[dict]:
    return [row.to_dict() for row in legacy_progress_repository.list_user_progress_rows(user_id)]


def save_legacy_progress(user_id: int, payload: dict | None) -> dict:
    data = payload or {}
    day = data.get('day')
    if not day:
        raise ValueError('Day is required')

    progress = legacy_progress_repository.get_user_progress(user_id, day)
    if progress:
        progress.current_index = data.get('current_index', 0)
        progress.correct_count = data.get('correct_count', 0)
        progress.wrong_count = data.get('wrong_count', 0)
    else:
        progress = legacy_progress_repository.create_user_progress(
            user_id,
            day=day,
            current_index=data.get('current_index', 0),
            correct_count=data.get('correct_count', 0),
            wrong_count=data.get('wrong_count', 0),
        )

    legacy_progress_repository.commit()
    return progress.to_dict()


def get_legacy_progress_for_day(user_id: int, day: int) -> dict | None:
    progress = legacy_progress_repository.get_user_progress(user_id, day)
    return progress.to_dict() if progress else None


def build_user_progress_response(user_id: int):
    progress_records = list_user_book_progress_rows(user_id)
    chapter_records = list_user_chapter_progress_rows(user_id)

    progress_by_book = {record.book_id: record for record in progress_records}
    chapters_by_book = defaultdict(list)
    for record in chapter_records:
        chapters_by_book[record.book_id].append(record)

    progress_dict = {}
    for book_id in sorted(set(progress_by_book) | set(chapters_by_book)):
        effective_progress = serialize_effective_book_progress(
            book_id,
            progress_record=progress_by_book.get(book_id),
            chapter_records=chapters_by_book.get(book_id, []),
            user_id=user_id,
        )
        if effective_progress:
            progress_dict[book_id] = effective_progress
    return {'progress': progress_dict}, 200


def build_book_progress_response(user_id: int, book_id):
    progress = get_user_book_progress(user_id, book_id)
    chapter_records = list_user_chapter_progress_rows(user_id, book_id=book_id)
    effective_progress = serialize_effective_book_progress(
        book_id,
        progress_record=progress,
        chapter_records=chapter_records,
        user_id=user_id,
    )
    return {'progress': effective_progress}, 200


def save_book_progress_response(user_id: int, data: dict | None):
    payload = data or {}
    book_id = payload.get('book_id')
    if not book_id:
        return {'error': 'book_id is required'}, 400

    progress = get_user_book_progress(user_id, book_id)
    if not progress:
        progress = create_user_book_progress(user_id, book_id)

    before_snapshot = {
        'current_index': progress.current_index or 0,
        'correct_count': progress.correct_count or 0,
        'wrong_count': progress.wrong_count or 0,
        'is_completed': bool(progress.is_completed),
    }

    if 'current_index' in payload:
        progress.current_index = max(progress.current_index or 0, int(payload['current_index'] or 0))
    if 'correct_count' in payload:
        progress.correct_count = payload['correct_count']
    if 'wrong_count' in payload:
        progress.wrong_count = payload['wrong_count']
    if 'is_completed' in payload:
        progress.is_completed = payload['is_completed']

    after_snapshot = {
        'current_index': progress.current_index or 0,
        'correct_count': progress.correct_count or 0,
        'wrong_count': progress.wrong_count or 0,
        'is_completed': bool(progress.is_completed),
    }
    if after_snapshot != before_snapshot:
        queue_learning_event(
            add_learning_event=learning_event_repository.add_learning_event,
            user_id=user_id,
            event_type='book_progress_updated',
            source='book_progress',
            book_id=book_id,
            item_count=after_snapshot['current_index'],
            correct_count=after_snapshot['correct_count'],
            wrong_count=after_snapshot['wrong_count'],
            payload={'is_completed': after_snapshot['is_completed']},
        )

    _commit_user_state()

    chapter_records = list_user_chapter_progress_rows(user_id, book_id=book_id)
    effective_progress = serialize_effective_book_progress(
        book_id,
        progress_record=progress,
        chapter_records=chapter_records,
        user_id=user_id,
    )
    return {'progress': effective_progress}, 200


def build_chapter_progress_response(user_id: int, book_id):
    progress_records = list_user_chapter_progress_rows(user_id, book_id=book_id)
    mode_records = list_user_chapter_mode_progress_rows(user_id, book_id=book_id)

    progress_dict = {}
    for record in progress_records:
        payload = record.to_dict()
        payload['modes'] = {}
        progress_dict[str(record.chapter_id)] = payload

    for record in mode_records:
        key = str(record.chapter_id)
        if key not in progress_dict:
            progress_dict[key] = {'modes': {}}
        progress_dict[key]['modes'][record.mode] = record.to_dict()

    return {'chapter_progress': progress_dict}, 200


def save_chapter_progress_response(user_id: int, book_id, chapter_id, data: dict | None):
    payload = data or {}
    progress = get_user_chapter_progress(user_id, book_id, chapter_id)
    if not progress:
        progress = create_user_chapter_progress(user_id, book_id, chapter_id)

    before_snapshot = {
        'words_learned': progress.words_learned or 0,
        'correct_count': progress.correct_count or 0,
        'wrong_count': progress.wrong_count or 0,
        'is_completed': bool(progress.is_completed),
    }

    if 'words_learned' in payload:
        progress.words_learned = max(progress.words_learned or 0, int(payload['words_learned'] or 0))
    if 'correct_count' in payload:
        progress.correct_count = payload['correct_count']
    if 'wrong_count' in payload:
        progress.wrong_count = payload['wrong_count']
    if 'is_completed' in payload:
        progress.is_completed = payload['is_completed']

    after_snapshot = {
        'words_learned': progress.words_learned or 0,
        'correct_count': progress.correct_count or 0,
        'wrong_count': progress.wrong_count or 0,
        'is_completed': bool(progress.is_completed),
    }
    if after_snapshot != before_snapshot:
        queue_learning_event(
            add_learning_event=learning_event_repository.add_learning_event,
            user_id=user_id,
            event_type='chapter_progress_updated',
            source='chapter_progress',
            book_id=book_id,
            chapter_id=str(chapter_id),
            item_count=after_snapshot['words_learned'],
            correct_count=after_snapshot['correct_count'],
            wrong_count=after_snapshot['wrong_count'],
            payload={'is_completed': after_snapshot['is_completed']},
        )

    _commit_user_state()
    return {'progress': progress.to_dict()}, 200
