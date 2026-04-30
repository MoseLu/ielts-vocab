from __future__ import annotations

from typing import Any

from platform_sdk import catalog_content_confusable_support as confusable_support
from platform_sdk.catalog_content_service_repositories import custom_book_catalog_service
from platform_sdk.catalog_provider_adapter import (
    get_vocab_book,
    load_book_chapters,
    load_book_vocabulary,
    normalize_word_key,
)
from platform_sdk.learning_core_favorites_support import (
    FAVORITES_BOOK_ID,
    FAVORITES_CHAPTER_ID,
    FAVORITES_CHAPTER_TITLE,
    _is_favorites_book,
    _serialize_favorite_words,
)


def _chapter_id_matches(value: Any, chapter_id: Any) -> bool:
    try:
        return int(value) == int(chapter_id)
    except (TypeError, ValueError):
        return str(value) == str(chapter_id)


def _current_user_id() -> int | None:
    current_user = confusable_support.resolve_optional_current_user()
    return current_user.id if current_user else None


def _copy_word(word: dict, *, source_order: int, fallback_chapter_id: Any = None) -> dict:
    chapter_id = word.get('chapter_id', fallback_chapter_id)
    return {
        **word,
        'word_key': normalize_word_key(word.get('word')),
        'source_order': source_order,
        'chapter_id': chapter_id,
    }


def _dictionary_from_words(words: list[dict]) -> list[dict]:
    return [dict(word) for word in words]


def _empty_rejected_words() -> list[dict]:
    return []


def _find_chapter(chapters: list[dict], chapter_id: Any) -> dict | None:
    return next(
        (chapter for chapter in chapters if _chapter_id_matches(chapter.get('id'), chapter_id)),
        None,
    )


def _favorites_word_list(chapter_id: Any = None) -> tuple[dict, int]:
    if chapter_id is not None and not _chapter_id_matches(chapter_id, FAVORITES_CHAPTER_ID):
        return {'error': 'Chapter not found'}, 404

    user_id = _current_user_id()
    if not user_id:
        return {'error': 'Book not found'}, 404

    words = [
        _copy_word(word, source_order=index, fallback_chapter_id=FAVORITES_CHAPTER_ID)
        for index, word in enumerate(_serialize_favorite_words(user_id))
    ]
    if not words:
        return {'error': 'Book not found'}, 404

    chapter = {
        'id': FAVORITES_CHAPTER_ID,
        'title': FAVORITES_CHAPTER_TITLE,
        'word_count': len(words),
        'is_custom': True,
    }
    return _build_payload(
        book={'id': FAVORITES_BOOK_ID, 'title': '收藏词书'},
        chapter=chapter if chapter_id is not None else None,
        words=words,
    ), 200


def _custom_confusable_words(book_id: str, user_id: int | None) -> list[dict]:
    if not confusable_support.is_confusable_match_book(book_id) or not user_id:
        return []
    custom_book = confusable_support.get_confusable_custom_book(user_id)
    if not custom_book:
        return []

    words: list[dict] = []
    for chapter in custom_book.chapters:
        for word in confusable_support.serialize_confusable_custom_words(chapter):
            words.append({
                **word,
                'chapter_id': chapter.id,
                'chapter_title': chapter.title,
            })
    return words


def _book_word_list(book_id: str, chapter_id: Any = None) -> tuple[dict, int]:
    if _is_favorites_book(book_id):
        return _favorites_word_list(chapter_id)

    user_id = _current_user_id()
    book = get_vocab_book(book_id)
    custom_book = custom_book_catalog_service.get_custom_book_for_user(user_id, book_id)
    if not book and not custom_book:
        return {'error': 'Book not found'}, 404

    if chapter_id is not None and confusable_support.is_confusable_match_book(book_id):
        custom_chapter = confusable_support.get_confusable_custom_chapter(user_id, chapter_id)
        if custom_chapter:
            raw_words = confusable_support.serialize_confusable_custom_words(custom_chapter)
            words = [
                _copy_word(word, source_order=index, fallback_chapter_id=chapter_id)
                for index, word in enumerate(raw_words)
            ]
            return _build_payload(
                book=book,
                chapter={
                    'id': chapter_id,
                    'title': custom_chapter.title,
                    'word_count': int(custom_chapter.word_count or len(custom_chapter.words)),
                    'group_count': 1,
                    'is_custom': True,
                },
                words=words,
            ), 200

    chapters_data = load_book_chapters(book_id) or {}
    chapters = list(chapters_data.get('chapters') or [])
    chapter = _find_chapter(chapters, chapter_id) if chapter_id is not None else None
    if chapter_id is not None and chapter is None:
        return {'error': 'Chapter not found'}, 404

    raw_words = list(load_book_vocabulary(book_id) or [])
    raw_words.extend(_custom_confusable_words(book_id, user_id))
    if chapter_id is not None:
        raw_words = [
            word for word in raw_words
            if _chapter_id_matches(word.get('chapter_id'), chapter_id)
        ]

    words = [
        _copy_word(word, source_order=index, fallback_chapter_id=chapter_id)
        for index, word in enumerate(raw_words)
    ]
    return _build_payload(
        book=custom_book_catalog_service.serialize_custom_book_summary(custom_book) if custom_book else book,
        chapter=chapter,
        words=words,
    ), 200


def _selected_word_list(selected_words: list[str]) -> tuple[dict, int]:
    words = [
        _copy_word({'word': word, 'phonetic': '', 'pos': '', 'definition': ''}, source_order=index)
        for index, word in enumerate(selected_words)
        if normalize_word_key(word)
    ]
    return _build_payload(book=None, chapter=None, words=words), 200


def _build_payload(*, book: dict | None, chapter: dict | None, words: list[dict]) -> dict:
    return {
        'book': book,
        'chapter': chapter,
        'words': words,
        'dictionary': _dictionary_from_words(words),
        'rejected_words': _empty_rejected_words(),
        'order': 'canonical',
        'total': len(words),
    }


def build_word_list_response(
    *,
    scope: str = 'book',
    book_id: str | None = None,
    chapter_id: Any = None,
    selected_words: list[str] | None = None,
    order: str = 'canonical',
) -> tuple[dict, int]:
    if order != 'canonical':
        return {'error': 'Only canonical order is supported'}, 400

    normalized_scope = str(scope or 'book').strip() or 'book'
    if normalized_scope == 'favorites':
        return _favorites_word_list(chapter_id)
    if normalized_scope in {'wrong-selection', 'quickmemory'} and selected_words:
        return _selected_word_list(selected_words)
    if normalized_scope in {'book', 'confusable'}:
        resolved_book_id = book_id or (FAVORITES_BOOK_ID if normalized_scope == 'favorites' else None)
        if normalized_scope == 'confusable' and not resolved_book_id:
            resolved_book_id = confusable_support.CONFUSABLE_MATCH_BOOK_ID
        if not resolved_book_id:
            return {'error': 'book_id is required'}, 400
        return _book_word_list(str(resolved_book_id), chapter_id)
    return {'error': f'Unsupported scope: {normalized_scope}'}, 400
