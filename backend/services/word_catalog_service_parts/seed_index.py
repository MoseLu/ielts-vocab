from __future__ import annotations

import os
from collections import OrderedDict, defaultdict

from service_models.catalog_content_models import WordCatalogEntry
from services import books_catalog_service, word_catalog_repository
from services.word_catalog_defaults import (
    build_default_root_payload,
    generate_derivative_candidates,
)


_WORD_SEED_CACHE: dict[tuple[str, ...], dict[str, dict]] = {}
_WORD_CATALOG_INDEX_CACHE: dict[tuple[str, ...], tuple[dict[str, list[dict]], dict[str, list[dict]]]] = {}

def normalize_word_key(value) -> str:
    if not isinstance(value, str):
        return ''
    return value.strip().lower()


def _should_use_cache() -> bool:
    return os.environ.get('PYTEST_RUNNING') != '1'


def _seed_cache_key(book_ids: tuple[str, ...] | None) -> tuple[str, ...]:
    return tuple(sorted(book_ids)) if book_ids else ('__all__',)


def _iter_catalog_entries(book_ids: tuple[str, ...] | None = None):
    selected_books = set(book_ids or [])
    for entry in books_catalog_service._build_global_word_search_catalog():
        book_id = str(entry.get('book_id') or '').strip()
        if selected_books and book_id not in selected_books:
            continue
        yield entry


def _score_seed_entry(entry: dict) -> tuple[int, int, int, int]:
    examples = entry.get('examples') or []
    definition = str(entry.get('definition') or '').strip()
    return (
        1 if entry.get('phonetic') else 0,
        1 if entry.get('pos') else 0,
        len(definition),
        len(examples),
    )


def _merge_examples(existing: list[dict], incoming: list[dict], limit: int = 4) -> list[dict]:
    seen = {str(item.get('en') or '').strip().lower() for item in existing}
    merged = list(existing)
    for item in incoming:
        en = str(item.get('en') or '').strip()
        zh = str(item.get('zh') or '').strip()
        if not en or en.lower() in seen:
            continue
        seen.add(en.lower())
        merged.append({'en': en, 'zh': zh})
        if len(merged) >= limit:
            break
    return merged


def _append_book_ref(seed: dict, entry: dict) -> None:
    ref = {
        'book_id': str(entry.get('book_id') or '').strip(),
        'book_title': str(entry.get('book_title') or '').strip(),
        'chapter_id': str(entry.get('chapter_id') or '').strip(),
        'chapter_title': str(entry.get('chapter_title') or '').strip(),
    }
    if not ref['book_id']:
        return

    existing_keys = {(item['book_id'], item['chapter_id']) for item in seed['book_refs']}
    unique_key = (ref['book_id'], ref['chapter_id'])
    if unique_key not in existing_keys:
        seed['book_refs'].append(ref)


def build_word_seed_index(book_ids: tuple[str, ...] | None = None) -> dict[str, dict]:
    cache_key = _seed_cache_key(book_ids)
    if _should_use_cache():
        cached = _WORD_SEED_CACHE.get(cache_key)
        if cached is not None:
            return cached

    seeds: OrderedDict[str, dict] = OrderedDict()
    for entry in _iter_catalog_entries(book_ids):
        normalized = normalize_word_key(entry.get('word'))
        if not normalized:
            continue

        seed = seeds.setdefault(normalized, {
            'word': normalized,
            'display_word': str(entry.get('word') or '').strip() or normalized,
            'normalized_word': normalized,
            'phonetic': '',
            'pos': '',
            'definition': '',
            'examples': [],
            'book_refs': [],
            '_score': (-1, -1, -1, -1),
        })

        score = _score_seed_entry(entry)
        if score > seed['_score']:
            seed['display_word'] = str(entry.get('word') or '').strip() or normalized
            seed['phonetic'] = str(entry.get('phonetic') or '').strip()
            seed['pos'] = str(entry.get('pos') or '').strip()
            seed['definition'] = str(entry.get('definition') or '').strip()
            seed['_score'] = score

        seed['examples'] = _merge_examples(seed['examples'], entry.get('examples') or [])
        _append_book_ref(seed, entry)

    for seed in seeds.values():
        seed.pop('_score', None)

    materialized = dict(seeds)
    if _should_use_cache():
        _WORD_SEED_CACHE[cache_key] = materialized
    return materialized


def get_word_seed(word: str, *, book_ids: tuple[str, ...] | None = None) -> dict:
    normalized = normalize_word_key(word)
    seed = build_word_seed_index(book_ids).get(normalized)
    if seed is not None:
        return seed
    return {
        'word': normalized or word.strip(),
        'display_word': word.strip() or normalized,
        'normalized_word': normalized,
        'phonetic': '',
        'pos': '',
        'definition': '',
        'examples': [],
        'book_refs': [],
    }


def _build_catalog_indexes(
    book_ids: tuple[str, ...] | None = None,
) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    cache_key = _seed_cache_key(book_ids)
    if _should_use_cache():
        cached = _WORD_CATALOG_INDEX_CACHE.get(cache_key)
        if cached is not None:
            return cached

    by_word = defaultdict(list)
    by_headword = defaultdict(list)
    for entry in _iter_catalog_entries(book_ids):
        word_key = normalize_word_key(entry.get('word'))
        if word_key:
            by_word[word_key].append(entry)

        headword_key = normalize_word_key(entry.get('headword'))
        if headword_key:
            by_headword[headword_key].append(entry)

    materialized = (dict(by_word), dict(by_headword))
    if _should_use_cache():
        _WORD_CATALOG_INDEX_CACHE[cache_key] = materialized
    return materialized


def build_default_derivative_payload(
    word: str,
    *,
    book_ids: tuple[str, ...] | None = None,
) -> list[dict]:
    normalized = normalize_word_key(word)
    if not normalized:
        return []

    by_word, by_headword = _build_catalog_indexes(book_ids)
    exact_entries = by_word.get(normalized, [])
    headword_keys = {
        normalize_word_key(entry.get('headword'))
        for entry in exact_entries
        if normalize_word_key(entry.get('headword'))
    }
    lookup_keys = {normalized, *headword_keys}
    candidate_rank = {
        candidate: index
        for index, candidate in enumerate(generate_derivative_candidates(word))
    }
    ranked: OrderedDict[str, dict] = OrderedDict()

    for lookup_key in lookup_keys:
        for entry in by_headword.get(lookup_key, []):
            derivative_key = normalize_word_key(entry.get('word'))
            if not derivative_key or derivative_key == normalized:
                continue
            ranked.setdefault(derivative_key, {
                'word': entry.get('word', ''),
                'phonetic': entry.get('phonetic', ''),
                'pos': entry.get('pos', ''),
                'definition': entry.get('definition', ''),
                'relation_type': 'headword',
                'source': 'catalog',
                'sort_order': candidate_rank.get(derivative_key, 100 + len(ranked)),
            })

    for candidate, index in candidate_rank.items():
        for entry in by_word.get(candidate, []):
            ranked.setdefault(candidate, {
                'word': entry.get('word', ''),
                'phonetic': entry.get('phonetic', ''),
                'pos': entry.get('pos', ''),
                'definition': entry.get('definition', ''),
                'relation_type': 'generated',
                'source': 'catalog',
                'sort_order': index,
            })

    if ranked:
        return sorted(ranked.values(), key=lambda item: (item['sort_order'], item['word'].lower()))

    return [{
        'word': candidate,
        'phonetic': '',
        'pos': '',
        'definition': '',
        'relation_type': 'generated',
        'source': 'placeholder',
        'sort_order': index,
    } for index, candidate in enumerate(generate_derivative_candidates(word)[:3])]


def _replace_book_refs(entry: WordCatalogEntry, refs: list[dict]) -> None:
    word_catalog_repository.replace_word_catalog_book_refs(entry, refs)
