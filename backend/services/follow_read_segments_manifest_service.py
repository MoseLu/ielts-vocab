from __future__ import annotations

import json
from pathlib import Path

from services import books_registry_service, books_vocabulary_loader_service


_sidecar_cache: dict[str, dict] = {}
_global_entries_cache: dict[str, dict] | None = None


def reset_follow_read_segment_manifest_caches() -> None:
    global _global_entries_cache
    _sidecar_cache.clear()
    _global_entries_cache = None


def follow_read_segments_dir() -> Path:
    path = Path(books_vocabulary_loader_service.get_vocab_data_path()) / 'follow_read_segments'
    path.mkdir(parents=True, exist_ok=True)
    return path


def follow_read_sidecar_path(book_id: str) -> Path:
    return follow_read_segments_dir() / f'{book_id}.json'


def load_follow_read_sidecar_entries(book_id: str) -> dict[str, dict]:
    if book_id in _sidecar_cache:
        return _sidecar_cache[book_id]
    path = follow_read_sidecar_path(book_id)
    if not path.exists():
        _sidecar_cache[book_id] = {}
        return _sidecar_cache[book_id]
    data = json.loads(path.read_text(encoding='utf-8'))
    entries = data.get('entries') if isinstance(data, dict) else {}
    _sidecar_cache[book_id] = entries if isinstance(entries, dict) else {}
    return _sidecar_cache[book_id]


def load_global_follow_read_sidecar_entries(book_ids: tuple[str, ...]) -> dict[str, dict]:
    global _global_entries_cache
    if _global_entries_cache is not None:
        return _global_entries_cache
    entries: dict[str, dict] = {}
    for book_id in book_ids:
        entries.update(load_follow_read_sidecar_entries(book_id))
    _global_entries_cache = entries
    return _global_entries_cache


def load_follow_read_source_words(book_id: str) -> list[dict]:
    book = books_registry_service.get_vocab_book(book_id)
    if book is None:
        raise ValueError(f'Unknown vocabulary book: {book_id}')
    file_name = str(book.get('file') or '').strip()
    if not file_name.endswith('.json'):
        raise ValueError(f'Follow-read sidecar generation only supports JSON books: {book_id}')
    path = Path(books_vocabulary_loader_service.get_vocab_data_path()) / file_name
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or 'chapters' not in data:
        raise ValueError(f'Unexpected JSON book shape for follow-read sidecar generation: {book_id}')
    words: list[dict] = []
    for chapter in data['chapters']:
        for word in chapter.get('words', []):
            word_text = str(word.get('word') or '').strip()
            phonetic = str(word.get('phonetic') or '').strip()
            if word_text and phonetic:
                words.append({'word': word_text, 'phonetic': phonetic})
    return words
