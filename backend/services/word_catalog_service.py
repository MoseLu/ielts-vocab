from __future__ import annotations

import os
from collections import OrderedDict, defaultdict

import routes.books as books_routes
from models import WordCatalogBookRef, WordCatalogEntry, db
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
    for entry in books_routes._build_global_word_search_catalog():
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
    WordCatalogBookRef.query.filter_by(catalog_entry_id=entry.id).delete()
    for item in refs:
        db.session.add(WordCatalogBookRef(
            catalog_entry_id=entry.id,
            book_id=item.get('book_id', ''),
            book_title=item.get('book_title', ''),
            chapter_id=item.get('chapter_id') or None,
            chapter_title=item.get('chapter_title') or None,
        ))


def ensure_word_catalog_entry(
    word: str,
    *,
    book_ids: tuple[str, ...] | None = None,
) -> tuple[WordCatalogEntry, bool]:
    seed = get_word_seed(word, book_ids=book_ids)
    normalized = seed['normalized_word']
    record = WordCatalogEntry.query.filter_by(normalized_word=normalized).first()
    created = record is None
    changed = created

    if not record:
        record = WordCatalogEntry(word=seed['display_word'], normalized_word=normalized)
        db.session.add(record)
        db.session.flush()

    if seed['display_word'] and record.word != seed['display_word']:
        record.word = seed['display_word']
        changed = True
    if seed['phonetic'] and record.phonetic != seed['phonetic']:
        record.phonetic = seed['phonetic']
        changed = True
    if seed['pos'] and record.pos != seed['pos']:
        record.pos = seed['pos']
        changed = True
    if seed['definition'] and record.definition != seed['definition']:
        record.definition = seed['definition']
        changed = True

    if not record.get_root_segments():
        root_payload = build_default_root_payload(record.word)
        record.set_root_segments(root_payload['segments'])
        record.root_summary = root_payload['summary']
        changed = True
    if not record.get_derivatives():
        record.set_derivatives(build_default_derivative_payload(normalized, book_ids=book_ids))
        changed = True
    if not record.get_examples() and seed['examples']:
        record.set_examples(seed['examples'])
        changed = True

    book_refs_changed = False
    if seed['book_refs']:
        current_refs = record.get_book_refs()
        if current_refs != seed['book_refs']:
            record.set_book_refs(seed['book_refs'])
            changed = True
            book_refs_changed = True

    if created and not record.source:
        record.source = 'catalog'

    db.session.flush()
    if seed['book_refs'] and (created or book_refs_changed):
        _replace_book_refs(record, seed['book_refs'])

    return record, changed


def upsert_word_catalog_entry(
    word_seed: dict,
    *,
    root_payload: dict,
    english_entries: list[dict],
    derivative_entries: list[dict],
    example_entries: list[dict],
    source: str,
) -> WordCatalogEntry:
    normalized = word_seed['normalized_word']
    record = WordCatalogEntry.query.filter_by(normalized_word=normalized).first()
    if not record:
        record = WordCatalogEntry(
            word=word_seed['display_word'],
            normalized_word=normalized,
        )
        db.session.add(record)
        db.session.flush()

    record.word = word_seed['display_word']
    record.phonetic = word_seed.get('phonetic', '')
    record.pos = word_seed.get('pos', '')
    record.definition = word_seed.get('definition', '')
    record.set_root_segments(root_payload.get('segments', []))
    record.root_summary = root_payload.get('summary', '')
    record.set_english_entries(english_entries)
    record.set_derivatives(derivative_entries)
    record.set_examples(example_entries)
    record.set_book_refs(word_seed.get('book_refs', []))
    record.source = source
    db.session.flush()

    _replace_book_refs(record, word_seed.get('book_refs', []))
    return record


def materialize_word_catalog(
    *,
    book_ids: tuple[str, ...] | None = None,
    limit: int | None = None,
    start_at: int = 0,
    commit_interval: int = 200,
) -> dict:
    seeds = list(build_word_seed_index(book_ids).values())
    if start_at > 0:
        seeds = seeds[start_at:]
    if limit is not None:
        seeds = seeds[:limit]

    stats = {'total': len(seeds), 'created': 0, 'updated': 0}
    for index, seed in enumerate(seeds, start=1):
        existed = WordCatalogEntry.query.filter_by(
            normalized_word=seed['normalized_word'],
        ).first() is not None
        _record, changed = ensure_word_catalog_entry(seed['normalized_word'], book_ids=book_ids)
        if not existed:
            stats['created'] += 1
        elif changed:
            stats['updated'] += 1

        if index % commit_interval == 0:
            db.session.commit()

    db.session.commit()
    return stats
