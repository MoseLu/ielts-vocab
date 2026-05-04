from __future__ import annotations

from typing import Any

from services import ai_custom_book_repository
from services.wrong_word_custom_book_service import (
    WRONG_WORD_CUSTOM_BOOK_DESCRIPTION,
    WRONG_WORD_CUSTOM_BOOK_TITLE,
    delete_user_managed_chapters,
    is_wrong_word_system_chapter_id,
)


def _payload_for_user_chapters(book_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    raw_chapters = payload.get('chapters')
    raw_words = payload.get('words')
    chapters = raw_chapters if isinstance(raw_chapters, list) else []
    user_chapters = [
        chapter
        for chapter in chapters
        if isinstance(chapter, dict)
        and not is_wrong_word_system_chapter_id(book_id, str(chapter.get('id') or ''))
    ]
    user_chapter_ids = {
        str(chapter.get('id') or '').strip()
        for chapter in user_chapters
        if str(chapter.get('id') or '').strip()
    }
    words = raw_words if isinstance(raw_words, list) else []
    user_words = [
        word
        for word in words
        if isinstance(word, dict)
        and str(word.get('chapterId', word.get('chapter_id')) or '').strip() in user_chapter_ids
    ]
    return {
        **payload,
        'title': WRONG_WORD_CUSTOM_BOOK_TITLE,
        'description': WRONG_WORD_CUSTOM_BOOK_DESCRIPTION,
        'chapters': user_chapters,
        'words': user_words,
    }


def update_wrong_word_custom_book_response(user_id: int, book, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
    from services.custom_book_catalog_service import (
        _accepted_words_from_content,
        _append_custom_book_chapters,
        _next_custom_book_chapter_sequence,
        _prepare_custom_book_content,
        build_custom_book_vocabulary_entries,
        serialize_custom_book_detail,
    )

    payload = _payload_for_user_chapters(book.id, body if isinstance(body, dict) else {})
    if not payload['words']:
        try:
            from services.wrong_word_custom_book_catalog_service import sync_wrong_word_custom_book_for_catalog_session
            sync_wrong_word_custom_book_for_catalog_session(user_id)
            ai_custom_book_repository.commit()
        except Exception:
            ai_custom_book_repository.rollback()
            raise
        detail = serialize_custom_book_detail(book)
        return {
            'bookId': book.id,
            'book': detail,
            'title': detail['title'],
            'description': detail['description'],
            'updated_count': 0,
            'chapters': detail['chapters'],
            'words': build_custom_book_vocabulary_entries(book),
            'accepted_words': [],
            'rejected_words': [],
        }, 200

    try:
        prepared_content = _prepare_custom_book_content(payload)
    except ValueError as exc:
        return {'error': str(exc)}, 400

    try:
        next_sequence = _next_custom_book_chapter_sequence(book)
        delete_user_managed_chapters(book)
        updated_chapters = _append_custom_book_chapters(
            book,
            prepared_content['chapters'],
            prepared_content['words_by_chapter'],
            sequence_base=next_sequence,
            sort_order_base=26,
        )
        from services.wrong_word_custom_book_catalog_service import sync_wrong_word_custom_book_for_catalog_session
        sync_wrong_word_custom_book_for_catalog_session(user_id)
        ai_custom_book_repository.commit()
        updated_book = ai_custom_book_repository.get_custom_book(user_id, book.id)
        if updated_book is None:
            raise RuntimeError('updated wrong-word custom book is missing')
    except Exception:
        ai_custom_book_repository.rollback()
        raise

    detail = serialize_custom_book_detail(updated_book)
    return {'bookId': updated_book.id, 'book': detail, 'title': detail['title'],
            'description': detail['description'], 'updated_count': len(updated_chapters),
            'chapters': detail['chapters'], 'words': build_custom_book_vocabulary_entries(updated_book),
            'accepted_words': _accepted_words_from_content(prepared_content),
            'rejected_words': prepared_content['rejected_words']}, 200
