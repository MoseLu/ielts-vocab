from __future__ import annotations

from typing import Any

from platform_sdk import catalog_content_confusable_support as confusable_support
from platform_sdk.catalog_content_service_repositories import custom_book_catalog_service
from platform_sdk.ai_wrong_words_application import build_wrong_words_response
from platform_sdk.catalog_provider_adapter import (
    get_vocab_book,
    load_book_chapters,
    load_book_vocabulary,
    normalize_word_key,
)
from platform_sdk.learning_core_quick_memory_read_adapter import (
    build_quick_memory_review_queue_response,
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


def _book_word_list(
    book_id: str,
    chapter_id: Any = None,
    *,
    include_dictionary: bool = True,
) -> tuple[dict, int]:
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
                include_dictionary=include_dictionary,
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
        include_dictionary=include_dictionary,
    ), 200


def _selected_word_list(selected_words: list[str]) -> tuple[dict, int]:
    words = [
        _copy_word({'word': word, 'phonetic': '', 'pos': '', 'definition': ''}, source_order=index)
        for index, word in enumerate(selected_words)
        if normalize_word_key(word)
    ]
    return _build_payload(book=None, chapter=None, words=words), 200


def _row_to_wrong_word(row) -> dict:
    if isinstance(row, dict):
        return {
            'word': row.get('word', ''),
            'phonetic': row.get('phonetic', ''),
            'pos': row.get('pos', ''),
            'definition': row.get('definition', ''),
        }
    return {
        'word': getattr(row, 'word', ''),
        'phonetic': getattr(row, 'phonetic', ''),
        'pos': getattr(row, 'pos', ''),
        'definition': getattr(row, 'definition', ''),
    }


def _row_id_value(row) -> int:
    value = row.get('id') if isinstance(row, dict) else getattr(row, 'id', 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _wrong_selection_word_list(selected_words: list[str] | None) -> tuple[dict, int]:
    user_id = _current_user_id()
    if not user_id and not selected_words:
        return {'error': 'Book not found'}, 404

    wrong_payload, wrong_status = build_wrong_words_response(user_id, detail_mode='full') if user_id else ({'words': []}, 200)
    if wrong_status != 200 and not selected_words:
        return wrong_payload, wrong_status
    rows = wrong_payload.get('words') or []
    wrong_by_key = {
        normalize_word_key(_row_to_wrong_word(row).get('word')): _row_to_wrong_word(row)
        for row in rows
    }
    if selected_words:
        raw_words = [
            wrong_by_key.get(normalize_word_key(word), {
                'word': word,
                'phonetic': '',
                'pos': '',
                'definition': '',
            })
            for word in selected_words
            if normalize_word_key(word)
        ]
    elif user_id:
        raw_words = [_row_to_wrong_word(row) for row in sorted(
            rows,
            key=_row_id_value,
        )]

    words = [
        _copy_word(word, source_order=index, fallback_chapter_id='wrong-selection')
        for index, word in enumerate(raw_words)
    ]
    return _build_payload(
        book={'id': 'wrong-selection', 'title': '自选错词本'},
        chapter={
            'id': 'wrong-selection',
            'title': '自选错词本',
            'word_count': len(words),
            'is_custom': True,
        },
        words=words,
    ), 200


def _quickmemory_args(request_args: Any | None) -> dict[str, str]:
    raw = request_args or {}
    return {
        'limit': str(raw.get('limit', '0')),
        'offset': str(raw.get('offset', '0')),
        'within_days': str(raw.get('within_days', '30')),
        'scope': str(raw.get('review_scope', 'due')),
        'book_id': str(raw.get('book_id', '') or ''),
        'chapter_id': str(raw.get('chapter_id', '') or ''),
    }


def _chapter_sort_value(value: Any) -> tuple[int, int | str]:
    try:
        return (0, int(value))
    except (TypeError, ValueError):
        return (1, str(value or ''))


def _build_source_order_lookup(words: list[dict]) -> dict[tuple[str, str, str], int]:
    book_ids = sorted({
        str(word.get('book_id') or '').strip()
        for word in words
        if str(word.get('book_id') or '').strip()
    })
    lookup: dict[tuple[str, str, str], int] = {}
    for book_id in book_ids:
        for index, word in enumerate(load_book_vocabulary(book_id) or []):
            word_key = normalize_word_key(word.get('word'))
            if not word_key:
                continue
            lookup.setdefault(
                (book_id, str(word.get('chapter_id') or ''), word_key),
                index,
            )
    return lookup


def _quickmemory_sort_key(
    word: dict,
    fallback_index: int,
    source_order_lookup: dict[tuple[str, str, str], int],
) -> tuple[str, tuple[int, int | str], int, int]:
    book_id = str(word.get('book_id') or '')
    chapter_id = str(word.get('chapter_id') or '')
    word_key = normalize_word_key(word.get('word'))
    explicit_source_order = word.get('source_order')
    try:
        source_order = int(explicit_source_order)
    except (TypeError, ValueError):
        source_order = source_order_lookup.get((book_id, chapter_id, word_key), fallback_index)
    return (book_id, _chapter_sort_value(chapter_id), source_order, fallback_index)


def _quickmemory_word_list(request_args: Any | None = None) -> tuple[dict, int]:
    user_id = _current_user_id()
    if not user_id:
        return {'error': 'Book not found'}, 404

    payload, status = build_quick_memory_review_queue_response(
        user_id,
        _quickmemory_args(request_args),
    )
    if status != 200:
        return payload, status

    raw_words = list(payload.get('words') or [])
    source_order_lookup = _build_source_order_lookup(raw_words)
    sorted_words = [
        word
        for _, word in sorted(
            enumerate(raw_words),
            key=lambda item: _quickmemory_sort_key(item[1], item[0], source_order_lookup),
        )
    ]
    words = [
        _copy_word(word, source_order=index, fallback_chapter_id=word.get('chapter_id'))
        for index, word in enumerate(sorted_words)
    ]
    return _build_payload(
        book={'id': 'quickmemory', 'title': '艾宾浩斯复习'},
        chapter={
            'id': 'quickmemory',
            'title': '艾宾浩斯复习',
            'word_count': len(words),
            'is_custom': True,
        },
        words=words,
        extra={'summary': payload.get('summary')},
    ), 200


def _build_payload(
    *,
    book: dict | None,
    chapter: dict | None,
    words: list[dict],
    extra: dict | None = None,
    include_dictionary: bool = True,
) -> dict:
    payload = {
        'book': book,
        'chapter': chapter,
        'words': words,
        'rejected_words': _empty_rejected_words(),
        'order': 'canonical',
        'total': len(words),
    }
    if include_dictionary:
        payload['dictionary'] = _dictionary_from_words(words)
    if extra:
        payload.update(extra)
    return payload


def build_word_list_response(
    *,
    scope: str = 'book',
    book_id: str | None = None,
    chapter_id: Any = None,
    selected_words: list[str] | None = None,
    order: str = 'canonical',
    request_args: Any | None = None,
    include_dictionary: bool = True,
) -> tuple[dict, int]:
    if order != 'canonical':
        return {'error': 'Only canonical order is supported'}, 400

    normalized_scope = str(scope or 'book').strip() or 'book'
    if normalized_scope == 'favorites':
        return _favorites_word_list(chapter_id)
    if normalized_scope == 'quickmemory':
        if selected_words:
            return _selected_word_list(selected_words)
        return _quickmemory_word_list(request_args)
    if normalized_scope == 'wrong-selection':
        return _wrong_selection_word_list(selected_words)
    if normalized_scope in {'book', 'confusable'}:
        resolved_book_id = book_id or (FAVORITES_BOOK_ID if normalized_scope == 'favorites' else None)
        if normalized_scope == 'confusable' and not resolved_book_id:
            resolved_book_id = confusable_support.CONFUSABLE_MATCH_BOOK_ID
        if not resolved_book_id:
            return {'error': 'book_id is required'}, 400
        return _book_word_list(str(resolved_book_id), chapter_id, include_dictionary=include_dictionary)
    return {'error': f'Unsupported scope: {normalized_scope}'}, 400
