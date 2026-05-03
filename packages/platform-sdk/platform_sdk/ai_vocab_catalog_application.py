from __future__ import annotations

import csv
import functools
import json
from pathlib import Path
from threading import RLock

from platform_sdk.catalog_provider_adapter import get_vocab_book, list_vocab_books, load_book_vocabulary
from platform_sdk.study_session_support import normalize_chapter_id

_QUICK_MEMORY_VOCAB_CATALOG_LOCK = RLock()
_QUICK_MEMORY_BOOK_LOOKUP_LOCK = RLock()
_QUICK_MEMORY_LIGHTWEIGHT_LOOKUP_LOCK = RLock()
_AUTO_FAVORITES_BOOK_ID = 'ielts_auto_favorites'
_AUTO_FAVORITES_BOOK_TITLE = '收藏词书'


def _vocabulary_data_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / 'vocabulary_data'
        if candidate.exists():
            return candidate
    return Path.cwd() / 'vocabulary_data'


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


def _raw_word_entry(word: dict, *, chapter_id=None, chapter_title: str = '') -> dict:
    return {
        'word': str(word.get('word') or '').strip(),
        'phonetic': str(word.get('phonetic') or '').strip(),
        'pos': str(word.get('pos') or 'n.').strip(),
        'definition': str(word.get('definition') or word.get('translation') or '').strip(),
        'chapter_id': chapter_id if chapter_id is not None else word.get('chapter_id'),
        'chapter_title': chapter_title or str(word.get('chapter_title') or '').strip(),
    }


def _load_lightweight_book_vocabulary(book_id: str) -> list[dict]:
    book = get_vocab_book(book_id) or {}
    file_name = str(book.get('file') or '').strip()
    if not file_name:
        return []
    file_path = _vocabulary_data_dir() / file_name
    try:
        if file_name.endswith('.json'):
            with file_path.open('r', encoding='utf-8') as file:
                data = json.load(file)
            if isinstance(data, dict) and isinstance(data.get('chapters'), list):
                words = []
                for chapter in data['chapters']:
                    for word in chapter.get('words') or []:
                        words.append(_raw_word_entry(
                            word,
                            chapter_id=chapter.get('id'),
                            chapter_title=str(chapter.get('title') or '').strip(),
                        ))
                return words
            if isinstance(data, dict) and isinstance(data.get('vocabulary'), list):
                return [_raw_word_entry(word) for word in data['vocabulary']]
            if isinstance(data, list):
                return [_raw_word_entry(word) for word in data]
        if file_name.endswith('.csv'):
            with file_path.open('r', encoding='utf-8-sig') as file:
                return [_raw_word_entry(row) for row in csv.DictReader(file)]
    except Exception:
        return []
    return []


@functools.lru_cache(maxsize=1)
def _build_quick_memory_vocab_catalog_snapshot_once() -> tuple[list[dict], dict[str, list[dict]]]:
    pool_by_word: dict[str, dict] = {}
    lookup: dict[str, list[dict]] = {}
    for book in list_vocab_books():
        book_id = book['id']
        book_title = book.get('title') or book_id
        words = load_book_vocabulary(book_id) or []
        for word in words:
            word_text = (word.get('word') or '').strip()
            if not word_text:
                continue

            chapter_id = normalize_chapter_id(word.get('chapter_id'))
            chapter_title = word.get('chapter_title') or (
                f"第{chapter_id}章" if chapter_id is not None else ''
            )
            word_key = word_text.lower()
            lookup.setdefault(word_key, []).append(_copy_vocab_entry(
                word,
                book_id=book_id,
                book_title=book_title,
                chapter_id=chapter_id,
                chapter_title=chapter_title,
            ))
            pool_by_word.setdefault(word_key, _copy_vocab_entry(word))
    return list(pool_by_word.values()), lookup


def _build_quick_memory_vocab_catalog_snapshot() -> tuple[list[dict], dict[str, list[dict]]]:
    with _QUICK_MEMORY_VOCAB_CATALOG_LOCK:
        return _build_quick_memory_vocab_catalog_snapshot_once()


@functools.lru_cache(maxsize=16)
def _build_book_quick_memory_vocab_lookup_once(book_id: str) -> dict[str, list[dict]]:
    lookup: dict[str, list[dict]] = {}
    book = get_vocab_book(book_id)
    if not book:
        return lookup
    book_title = book.get('title') or book_id
    for word in (
        _load_lightweight_book_vocabulary(book_id)
        or load_book_vocabulary(book_id)
        or []
    ):
        word_text = (word.get('word') or '').strip()
        if not word_text:
            continue

        chapter_id = normalize_chapter_id(word.get('chapter_id'))
        chapter_title = word.get('chapter_title') or (
            f"第{chapter_id}章" if chapter_id is not None else ''
        )
        lookup.setdefault(word_text.lower(), []).append(_copy_vocab_entry(
            word,
            book_id=book_id,
            book_title=book_title,
            chapter_id=chapter_id,
            chapter_title=chapter_title,
        ))
    return lookup


@functools.lru_cache(maxsize=1)
def _build_lightweight_quick_memory_vocab_lookup_once() -> dict[str, list[dict]]:
    lookup: dict[str, list[dict]] = {}
    for book in list_vocab_books():
        book_id = book['id']
        book_title = book.get('title') or book_id
        for word in _load_lightweight_book_vocabulary(book_id):
            word_text = (word.get('word') or '').strip()
            if not word_text:
                continue
            chapter_id = normalize_chapter_id(word.get('chapter_id'))
            chapter_title = word.get('chapter_title') or (
                f"第{chapter_id}章" if chapter_id is not None else ''
            )
            lookup.setdefault(word_text.lower(), []).append(_copy_vocab_entry(
                word,
                book_id=book_id,
                book_title=book_title,
                chapter_id=chapter_id,
                chapter_title=chapter_title,
            ))
    return lookup


def _get_book_quick_memory_vocab_lookup(book_id: str) -> dict[str, list[dict]]:
    with _QUICK_MEMORY_BOOK_LOOKUP_LOCK:
        return _build_book_quick_memory_vocab_lookup_once(book_id)


def _get_lightweight_quick_memory_vocab_entries(word_key: str) -> list[dict]:
    with _QUICK_MEMORY_LIGHTWEIGHT_LOOKUP_LOCK:
        lookup = _build_lightweight_quick_memory_vocab_lookup_once()
    return [dict(entry) for entry in (lookup.get(word_key) or [])]


def _clear_quick_memory_vocab_catalog_cache() -> None:
    _build_quick_memory_vocab_catalog_snapshot_once.cache_clear()
    _build_book_quick_memory_vocab_lookup_once.cache_clear()
    _build_lightweight_quick_memory_vocab_lookup_once.cache_clear()


def get_global_vocab_pool() -> list:
    pool, _ = _build_quick_memory_vocab_catalog_snapshot()
    return pool


def get_quick_memory_vocab_lookup() -> dict[str, list[dict]]:
    _, lookup = _build_quick_memory_vocab_catalog_snapshot()
    return lookup


def get_quick_memory_vocab_entries(word_key: str, *, book_id: str | None = None) -> list[dict]:
    if book_id:
        return [
            dict(entry)
            for entry in (_get_book_quick_memory_vocab_lookup(book_id).get(word_key) or [])
        ]
    return [dict(entry) for entry in (get_quick_memory_vocab_lookup().get(word_key) or [])]


get_global_vocab_pool.cache_clear = _clear_quick_memory_vocab_catalog_cache
get_quick_memory_vocab_lookup.cache_clear = _clear_quick_memory_vocab_catalog_cache


def _select_quick_memory_vocab_entry(
    entries: list[dict],
    *,
    book_id: str | None = None,
    chapter_id: str | None = None,
) -> dict | None:
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


def resolve_unique_quick_memory_vocab_context(word_key: str) -> tuple[str | None, str | None] | None:
    contexts = {
        (
            (entry.get('book_id') or '').strip() or None,
            normalize_chapter_id(entry.get('chapter_id')),
        )
        for entry in get_quick_memory_vocab_entries(word_key)
        if (entry.get('book_id') or '').strip() or normalize_chapter_id(entry.get('chapter_id')) is not None
    }
    if len(contexts) != 1:
        return None
    return next(iter(contexts))


def resolve_quick_memory_vocab_entry(
    word_key: str,
    *,
    book_id: str | None = None,
    chapter_id: str | None = None,
) -> dict | None:
    entries = get_quick_memory_vocab_entries(word_key, book_id=book_id) if book_id else (
        get_quick_memory_vocab_entries(word_key)
    )
    if book_id and not entries and book_id == _AUTO_FAVORITES_BOOK_ID:
        entry = _select_quick_memory_vocab_entry(
            _get_lightweight_quick_memory_vocab_entries(word_key),
            chapter_id=chapter_id,
        )
        if entry:
            entry['book_id'] = book_id
            entry['book_title'] = _AUTO_FAVORITES_BOOK_TITLE
            return entry
    if book_id and not entries:
        entries = get_quick_memory_vocab_entries(word_key)
    return _select_quick_memory_vocab_entry(
        entries,
        book_id=book_id,
        chapter_id=chapter_id,
    )
