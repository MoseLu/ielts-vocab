from __future__ import annotations

import sys
import time

from models import WordCatalogEntry
from services import word_catalog_repository
from services.word_detail_llm_client import (
    DEFAULT_PROVIDER,
    is_quota_exhausted_error,
    normalize_provider,
    request_llm_batch,
    resolve_model,
)
from services.word_catalog_service import (
    build_default_derivative_payload,
    build_default_root_payload,
    build_word_seed_index,
    normalize_word_key,
    upsert_word_catalog_entry,
)


PREMIUM_BOOK_IDS = (
    'ielts_listening_premium',
    'ielts_reading_premium',
)
DEFAULT_BATCH_SIZE = 8
LLM_SOURCE = 'llm'


def _normalize_word(value) -> str:
    return normalize_word_key(value)


def _dedupe_texts(values: list[str], limit: int) -> list[str]:
    seen = set()
    items = []
    for value in values:
        text = str(value or '').strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        items.append(text)
        if len(items) >= limit:
            break
    return items


def collect_word_seeds(book_ids: tuple[str, ...] | None = PREMIUM_BOOK_IDS) -> list[dict]:
    seed_index = build_word_seed_index(book_ids)
    merged: list[dict] = []
    for seed in seed_index.values():
        merged.append({
            'word': seed['word'],
            'display_word': seed['display_word'],
            'normalized_word': seed['normalized_word'],
            'phonetic': seed['phonetic'],
            'pos': seed['pos'],
            'definition': seed['definition'],
            'definitions': _dedupe_texts([seed['definition']], 3),
            'examples': seed['examples'],
            'book_refs': seed['book_refs'],
            'book_ids': _dedupe_texts([item['book_id'] for item in seed['book_refs']], 8),
        })
    return merged


def _sanitize_root_payload(word: str, raw_root) -> dict:
    fallback = build_default_root_payload(word)
    if not isinstance(raw_root, dict):
        return fallback

    segments = []
    for item in raw_root.get('segments') or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get('kind') or '').strip()
        text = str(item.get('text') or '').strip()
        meaning = str(item.get('meaning') or '').strip()
        if kind not in {'前缀', '词根', '后缀'} or not text or not meaning:
            continue
        segments.append({'kind': kind, 'text': text, 'meaning': meaning})

    if not segments:
        segments = fallback['segments']

    summary = str(raw_root.get('summary') or '').strip() or fallback['summary']
    return {'segments': segments, 'summary': summary}


def _sanitize_english_entries(raw_entries) -> list[dict]:
    entries = []
    for item in raw_entries or []:
        if not isinstance(item, dict):
            continue
        pos = str(item.get('pos') or item.get('part_of_speech') or '').strip()
        definition = str(item.get('definition') or item.get('meaning') or '').strip()
        if not definition:
            continue
        entries.append({'pos': pos, 'definition': definition})
        if len(entries) >= 2:
            break
    return entries


def _sanitize_derivatives(word: str, raw_entries) -> list[dict]:
    entries = []
    seen = set()

    for item in raw_entries or []:
        if not isinstance(item, dict):
            continue
        derivative_word = str(item.get('word') or '').strip()
        normalized = _normalize_word(derivative_word)
        if not normalized or normalized == _normalize_word(word) or normalized in seen:
            continue
        seen.add(normalized)
        entries.append({
            'word': derivative_word,
            'phonetic': str(item.get('phonetic') or '').strip(),
            'pos': str(item.get('pos') or '').strip(),
            'definition': str(item.get('definition') or '').strip(),
            'relation_type': str(item.get('relation_type') or 'derived').strip() or 'derived',
        })
        if len(entries) >= 3:
            break

    if entries:
        return entries

    fallback = build_default_derivative_payload(word)
    return [{
        'word': item['word'],
        'phonetic': item.get('phonetic', ''),
        'pos': item.get('pos', ''),
        'definition': item.get('definition', ''),
        'relation_type': item.get('relation_type', 'generated'),
    } for item in fallback]


def _sanitize_examples(raw_entries, fallback_examples: list[dict]) -> list[dict]:
    examples = []
    seen = set()

    for item in raw_entries or []:
        if not isinstance(item, dict):
            continue
        en = str(item.get('en') or item.get('sentence_en') or '').strip()
        zh = str(item.get('zh') or item.get('sentence_zh') or '').strip()
        key = en.lower()
        if not en or key in seen:
            continue
        seen.add(key)
        examples.append({'en': en, 'zh': zh})
        if len(examples) >= 2:
            break

    if examples:
        return examples
    return fallback_examples[:2]


def _has_complete_word_details(catalog_entry: WordCatalogEntry | None) -> bool:
    if not catalog_entry:
        return False

    return (
        bool(catalog_entry.get_root_segments())
        and bool(catalog_entry.get_english_entries())
        and len(catalog_entry.get_examples()) >= 2
        and bool(catalog_entry.get_derivatives())
    )


def _needs_enrichment_record(catalog_entry: WordCatalogEntry | None, overwrite: bool) -> bool:
    if overwrite:
        return True
    return not _has_complete_word_details(catalog_entry)


def _build_record_index(word_seeds: list[dict]) -> dict[str, WordCatalogEntry]:
    normalized_words = [seed['normalized_word'] for seed in word_seeds if seed.get('normalized_word')]
    if not normalized_words:
        return {}

    records = word_catalog_repository.list_word_catalog_entries_by_normalized_words(
        normalized_words,
    )
    return {record.normalized_word: record for record in records}


def collect_pending_word_seeds(
    word_seeds: list[dict],
    *,
    overwrite: bool = False,
) -> list[dict]:
    record_index = _build_record_index(word_seeds)
    return [
        seed
        for seed in word_seeds
        if _needs_enrichment_record(record_index.get(seed['normalized_word']), overwrite)
    ]
