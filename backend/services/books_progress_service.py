from __future__ import annotations

from collections import defaultdict

from services import books_confusable_service, books_favorites_service
from services.books_catalog_query_service import load_book_vocabulary
from services.custom_book_catalog_service import get_custom_book_for_user
from services.books_structure_service import (
    load_book_chapters,
    serialize_effective_book_progress,
)
from services.books_user_state_repository import (
    commit as _commit_user_state,
    create_user_book_progress,
    create_user_chapter_progress,
    get_user_book_progress,
    get_user_chapter_progress,
    list_user_book_progress_rows,
    list_user_chapter_mode_progress_rows,
    list_user_chapter_progress_rows,
)
from services.learning_events import record_learning_event


def _find_book(book_id):
    from services import books_registry_service
    return books_registry_service.get_vocab_book(book_id)


def _paginate_items(items, page, per_page):
    start = (page - 1) * per_page
    end = start + per_page
    total = len(items)
    return {
        'items': items[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
    }


def _chapter_id_matches(value, chapter_id):
    try:
        return int(value) == int(chapter_id)
    except (TypeError, ValueError):
        return str(value) == str(chapter_id)


def _strip_chapter_fields(word_entry):
    return {
        key: value
        for key, value in word_entry.items()
        if key not in {'chapter_id', 'chapter_title'}
    }


def build_chapter_words_response(book_id, chapter_id):
    if books_favorites_service._is_favorites_book(book_id):
        return _build_favorites_chapter_words_response(chapter_id)

    current_user = books_confusable_service.resolve_optional_current_user()
    custom_book = get_custom_book_for_user(current_user.id if current_user else None, book_id)
    if not custom_book and not _find_book(book_id):
        return {'error': 'Book not found'}, 404

    if books_confusable_service.is_confusable_match_book(book_id):
        custom_chapter = books_confusable_service.get_confusable_custom_chapter(
            current_user.id if current_user else None,
            chapter_id,
        )
        if custom_chapter:
            return {
                'chapter': {
                    'id': chapter_id,
                    'title': custom_chapter.title,
                    'word_count': int(custom_chapter.word_count or len(custom_chapter.words)),
                    'group_count': 1,
                    'is_custom': True,
                },
                'words': books_confusable_service.serialize_confusable_custom_words(custom_chapter),
            }, 200

    chapters_data = load_book_chapters(book_id)
    if not chapters_data:
        return {'error': 'Chapters not available for this book'}, 404

    chapter = next(
        (
            entry
            for entry in chapters_data.get('chapters', [])
            if _chapter_id_matches(entry.get('id'), chapter_id)
        ),
        None,
    )
    if not chapter:
        return {'error': 'Chapter not found'}, 404

    words = load_book_vocabulary(book_id)
    if words is None:
        return {'error': 'Failed to load chapter'}, 500

    chapter_words = [
        _strip_chapter_fields(word)
        for word in words
        if _chapter_id_matches(word.get('chapter_id'), chapter_id)
    ]
    return {'chapter': chapter, 'words': chapter_words}, 200


def _build_favorites_chapter_words_response(chapter_id):
    if not _chapter_id_matches(chapter_id, books_favorites_service.FAVORITES_CHAPTER_ID):
        return {'error': 'Chapter not found'}, 404

    current_user = books_confusable_service.resolve_optional_current_user()
    if not current_user:
        return {'error': 'Book not found'}, 404

    words = books_favorites_service._serialize_favorite_words(current_user.id)
    if not words:
        return {'error': 'Chapter not found'}, 404

    return {
        'chapter': {
            'id': books_favorites_service.FAVORITES_CHAPTER_ID,
            'title': books_favorites_service.FAVORITES_CHAPTER_TITLE,
            'word_count': len(words),
            'is_custom': True,
        },
        'words': words,
    }, 200


def build_book_words_response(book_id, page=1, per_page=100):
    if books_favorites_service._is_favorites_book(book_id):
        current_user = books_confusable_service.resolve_optional_current_user()
        if not current_user:
            return {'error': 'Book not found'}, 404

        words = books_favorites_service._serialize_favorite_words(current_user.id)
        if not words:
            return {'error': 'Book not found'}, 404
        paginated = _paginate_items(words, page, per_page)
        return {
            'words': paginated['items'],
            'total': paginated['total'],
            'page': paginated['page'],
            'per_page': paginated['per_page'],
            'total_pages': paginated['total_pages'],
        }, 200

    current_user = books_confusable_service.resolve_optional_current_user()
    if not get_custom_book_for_user(current_user.id if current_user else None, book_id) and not _find_book(book_id):
        return {'error': 'Book not found'}, 404

    words = load_book_vocabulary(book_id)
    if words is None:
        return {'error': 'Failed to load vocabulary'}, 500

    if books_confusable_service.is_confusable_match_book(book_id):
        custom_book = (
            books_confusable_service.get_confusable_custom_book(current_user.id)
            if current_user else None
        )
        if custom_book:
            custom_words = []
            for chapter in custom_book.chapters:
                try:
                    custom_chapter_id = int(str(chapter.id))
                except (TypeError, ValueError):
                    continue
                for word in books_confusable_service.serialize_confusable_custom_words(chapter):
                    custom_words.append({
                        **word,
                        'chapter_id': custom_chapter_id,
                        'chapter_title': chapter.title,
                    })
            if custom_words:
                words = [*words, *custom_words]

    paginated = _paginate_items(words, page, per_page)
    return {
        'words': paginated['items'],
        'total': paginated['total'],
        'page': paginated['page'],
        'per_page': paginated['per_page'],
        'total_pages': paginated['total_pages'],
    }, 200


def build_user_progress_response(user_id):
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


def build_book_progress_response(user_id, book_id):
    progress = get_user_book_progress(user_id, book_id)
    chapter_records = list_user_chapter_progress_rows(user_id, book_id=book_id)
    effective_progress = serialize_effective_book_progress(
        book_id,
        progress_record=progress,
        chapter_records=chapter_records,
        user_id=user_id,
    )
    return {'progress': effective_progress}, 200


def save_book_progress_response(user_id, data):
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
        record_learning_event(
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


def build_chapter_progress_response(user_id, book_id):
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


def save_chapter_progress_response(user_id, book_id, chapter_id, data):
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
        record_learning_event(
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
