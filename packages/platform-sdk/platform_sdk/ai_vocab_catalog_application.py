from __future__ import annotations

import functools

from services import books_registry_service
from services.books_catalog_query_service import load_book_vocabulary
from services.study_sessions import normalize_chapter_id


def _clone_vocab_examples(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [
        {
            'en': str(item.get('en') or '').strip(),
            'zh': str(item.get('zh') or '').strip(),
        }
        for item in value
        if isinstance(item, dict) and (item.get('en') or item.get('zh'))
    ]


def _clone_listening_confusables(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [
        {
            'word': str(item.get('word') or '').strip(),
            'phonetic': str(item.get('phonetic') or '').strip(),
            'pos': str(item.get('pos') or '').strip(),
            'definition': str(item.get('definition') or '').strip(),
            'group_key': str(item.get('group_key') or '').strip() or None,
        }
        for item in value
        if isinstance(item, dict) and str(item.get('word') or '').strip()
    ]


def _copy_vocab_entry(word: dict, **extra_fields) -> dict:
    item = {
        'word': str(word.get('word') or '').strip(),
        'phonetic': str(word.get('phonetic') or '').strip(),
        'pos': str(word.get('pos') or '').strip(),
        'definition': str(word.get('definition') or '').strip(),
        'group_key': str(word.get('group_key') or '').strip() or None,
        'listening_confusables': _clone_listening_confusables(word.get('listening_confusables')),
        'examples': _clone_vocab_examples(word.get('examples')),
    }
    item.update(extra_fields)
    return item


@functools.lru_cache(maxsize=1)
def get_global_vocab_pool() -> list:
    seen: dict[str, dict] = {}
    for book in books_registry_service.list_vocab_books():
        words = load_book_vocabulary(book['id']) or []
        for word in words:
            key = word.get('word', '').strip().lower()
            if key and key not in seen:
                seen[key] = _copy_vocab_entry(word)
    return list(seen.values())


@functools.lru_cache(maxsize=1)
def get_quick_memory_vocab_lookup() -> dict[str, list[dict]]:
    lookup: dict[str, list[dict]] = {}
    for book in books_registry_service.list_vocab_books():
        book_id = book['id']
        book_title = book.get('title') or book_id
        words = load_book_vocabulary(book_id) or []
        for word in words:
            text = (word.get('word') or '').strip()
            if not text:
                continue

            chapter_id = normalize_chapter_id(word.get('chapter_id'))
            chapter_title = word.get('chapter_title') or (
                f"第{chapter_id}章" if chapter_id is not None else ''
            )
            lookup.setdefault(text.lower(), []).append(_copy_vocab_entry(
                word,
                book_id=book_id,
                book_title=book_title,
                chapter_id=chapter_id,
                chapter_title=chapter_title,
            ))
    return lookup


def resolve_quick_memory_vocab_entry(
    word_key: str,
    *,
    book_id: str | None = None,
    chapter_id: str | None = None,
) -> dict | None:
    entries = get_quick_memory_vocab_lookup().get(word_key) or []
    if not entries:
        return None

    if book_id is not None and chapter_id is not None:
        for entry in entries:
            if entry.get('book_id') == book_id and normalize_chapter_id(entry.get('chapter_id')) == chapter_id:
                return dict(entry)

    if book_id is not None:
        for entry in entries:
            if entry.get('book_id') == book_id:
                return dict(entry)

    if chapter_id is not None:
        for entry in entries:
            if normalize_chapter_id(entry.get('chapter_id')) == chapter_id:
                return dict(entry)

    return dict(entries[0])
