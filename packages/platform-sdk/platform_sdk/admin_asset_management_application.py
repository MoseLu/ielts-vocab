from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services import books_registry_service, premium_word_mnemonic_catalog


PAID_ASSET_BOOK_IDS = ('ielts_reading_premium', 'ielts_listening_premium')
MNEMONIC_STATUSES = {'all', 'with_mnemonic', 'missing_mnemonic'}


def _normalize_text(value: Any, *, max_length: int | None = None) -> str:
    text = ' '.join(str(value or '').split())
    if max_length is not None:
        return text[:max_length]
    return text


def _safe_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return min(max(number, minimum), maximum)


def _book_data_path(file_name: str) -> Path:
    return premium_word_mnemonic_catalog.REPO_ROOT / 'vocabulary_data' / file_name


def _load_raw_mnemonic_payload() -> dict:
    path = premium_word_mnemonic_catalog.PREMIUM_WORD_MNEMONICS_PATH
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_raw_mnemonic_index() -> tuple[dict[str, dict], str | None]:
    payload = _load_raw_mnemonic_payload()
    raw_items = payload.get('items')
    if not isinstance(raw_items, dict):
        return {}, None

    items = {
        _normalize_text(key, max_length=160).lower(): value
        for key, value in raw_items.items()
        if isinstance(value, dict)
    }
    updated_at = _normalize_text(payload.get('generated_at'), max_length=80) or None
    return items, updated_at


def _load_book_payload(book_id: str) -> dict:
    book = books_registry_service.get_vocab_book(book_id)
    file_name = _normalize_text((book or {}).get('file'))
    if not file_name:
        return {}

    try:
        payload = json.loads(_book_data_path(file_name).read_text(encoding='utf-8'))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _serialize_word_asset(book: dict, chapter: dict, word_entry: dict) -> dict | None:
    word = _normalize_text(word_entry.get('word'), max_length=120)
    if not word:
        return None

    chapter_id = _normalize_text(chapter.get('id'), max_length=80)
    return {
        'id': f'asset:{word.lower()}',
        'book_id': book['id'],
        'book_title': book.get('title') or book['id'],
        'source_book_ids': [book['id']],
        'source_book_titles': [book.get('title') or book['id']],
        'chapter_id': chapter_id,
        'chapter_title': _normalize_text(chapter.get('title'), max_length=160),
        'word': word,
        'normalized_word': word.lower(),
        'phonetic': _normalize_text(word_entry.get('phonetic'), max_length=100),
        'pos': _normalize_text(word_entry.get('pos'), max_length=50),
        'definition': _normalize_text(word_entry.get('definition'), max_length=500),
        'memory_badge': '',
        'memory_text': '',
        'memory_source': '',
        'memory_updated_at': None,
        'has_mnemonic': False,
    }


def _merge_book_source(asset: dict, book: dict) -> None:
    book_id = book['id']
    if book_id in asset['source_book_ids']:
        return
    asset['source_book_ids'].append(book_id)
    asset['source_book_titles'].append(book.get('title') or book_id)


def _apply_raw_mnemonic(asset: dict, mnemonic_index: dict[str, dict], updated_at: str | None) -> None:
    mnemonic = mnemonic_index.get(asset['normalized_word']) or {}
    memory_text = _normalize_text(mnemonic.get('text'), max_length=1000)
    asset['memory_badge'] = _normalize_text(mnemonic.get('badge'), max_length=40)
    asset['memory_text'] = memory_text
    asset['memory_source'] = _normalize_text(mnemonic.get('source'), max_length=80)
    asset['memory_updated_at'] = updated_at
    asset['has_mnemonic'] = bool(memory_text)


def _load_paid_book_assets() -> list[dict]:
    assets_by_word: dict[str, dict] = {}
    mnemonic_index, memory_updated_at = _load_raw_mnemonic_index()
    for book_id in PAID_ASSET_BOOK_IDS:
        book = books_registry_service.get_vocab_book(book_id)
        if not book or not book.get('is_paid'):
            continue

        payload = _load_book_payload(book_id)
        chapters = payload.get('chapters')
        if not isinstance(chapters, list):
            continue

        for chapter in chapters:
            if not isinstance(chapter, dict):
                continue
            words = chapter.get('words')
            if not isinstance(words, list):
                continue
            for word_entry in words:
                if not isinstance(word_entry, dict):
                    continue
                item = _serialize_word_asset(book, chapter, word_entry)
                if item is None:
                    continue
                existing = assets_by_word.get(item['normalized_word'])
                if existing is None:
                    assets_by_word[item['normalized_word']] = item
                else:
                    _merge_book_source(existing, book)

    assets = list(assets_by_word.values())
    for item in assets:
        _apply_raw_mnemonic(item, mnemonic_index, memory_updated_at)
    return assets


def _matches_search(item: dict, search: str) -> bool:
    if not search:
        return True
    haystack = ' '.join([
        item['word'],
        item['definition'],
        item['memory_text'],
    ]).lower()
    return search.lower() in haystack


def _filter_assets(items: list[dict], *, book_id: str, search: str, mnemonic_status: str) -> list[dict]:
    filtered = items
    if book_id:
        filtered = [item for item in filtered if book_id in item['source_book_ids']]
    if mnemonic_status == 'with_mnemonic':
        filtered = [item for item in filtered if item['has_mnemonic']]
    elif mnemonic_status == 'missing_mnemonic':
        filtered = [item for item in filtered if not item['has_mnemonic']]
    if search:
        filtered = [item for item in filtered if _matches_search(item, search)]
    return filtered


def build_asset_words_response(args) -> tuple[dict, int]:
    page = _safe_int(args.get('page'), default=1, minimum=1, maximum=10000)
    per_page = _safe_int(args.get('per_page'), default=20, minimum=1, maximum=100)
    search = _normalize_text(args.get('search'), max_length=120)
    book_id = _normalize_text(args.get('book_id'), max_length=80)
    mnemonic_status = _normalize_text(args.get('mnemonic_status'), max_length=40) or 'all'

    if book_id and book_id not in PAID_ASSET_BOOK_IDS:
        return {'error': '不支持的词书筛选'}, 400
    if mnemonic_status not in MNEMONIC_STATUSES:
        return {'error': '不支持的助记状态筛选'}, 400

    all_items = _load_paid_book_assets()
    filtered = _filter_assets(
        all_items,
        book_id=book_id,
        search=search,
        mnemonic_status=mnemonic_status,
    )
    total = len(filtered)
    pages = max(1, (total + per_page - 1) // per_page)
    if page > pages:
        page = pages
    start = (page - 1) * per_page

    return {
        'items': filtered[start:start + per_page],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': pages,
        'summary': {
            'total_words': len(all_items),
            'with_mnemonic': sum(1 for item in all_items if item['has_mnemonic']),
            'missing_mnemonic': sum(1 for item in all_items if not item['has_mnemonic']),
        },
        'book_options': [
            {
                'id': book_id,
                'title': (books_registry_service.get_vocab_book(book_id) or {}).get('title') or book_id,
            }
            for book_id in PAID_ASSET_BOOK_IDS
        ],
    }, 200
