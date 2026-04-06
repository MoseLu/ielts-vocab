from __future__ import annotations

import sys
import time

from models import WordCatalogEntry, db
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

    records = WordCatalogEntry.query.filter(
        WordCatalogEntry.normalized_word.in_(normalized_words),
    ).all()
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


def _persist_llm_item(word_seed: dict, raw_item: dict) -> None:
    root_payload = _sanitize_root_payload(word_seed['display_word'], raw_item.get('root'))
    english_entries = _sanitize_english_entries(raw_item.get('english'))
    derivative_entries = _sanitize_derivatives(word_seed['display_word'], raw_item.get('derivatives'))
    example_entries = _sanitize_examples(raw_item.get('examples'), word_seed['examples'])

    upsert_word_catalog_entry(
        word_seed,
        root_payload=root_payload,
        english_entries=english_entries,
        derivative_entries=derivative_entries,
        example_entries=example_entries,
        source=LLM_SOURCE,
    )


def _enrich_batch(
    word_seeds: list[dict],
    *,
    stats: dict,
    provider: str,
    model: str | None,
    fallback_provider: str | None,
    fallback_model: str | None,
) -> None:
    for attempt in range(4):
        try:
            raw_items = request_llm_batch(
                word_seeds,
                provider=provider,
                model=model,
                fallback_provider=fallback_provider,
                fallback_model=fallback_model,
                normalize_word=_normalize_word,
            )
            for word_seed in word_seeds:
                _persist_llm_item(word_seed, raw_items[word_seed['normalized_word']])
            db.session.commit()
            stats['enriched'] += len(word_seeds)
            return
        except Exception as exc:
            db.session.rollback()
            if 'database is locked' in str(exc).lower() and attempt < 3:
                time.sleep(0.5 * (attempt + 1))
                continue
            raise


def enrich_word_seeds(
    word_seeds: list[dict],
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    overwrite: bool = False,
    sleep_seconds: float = 0.0,
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
    fallback_provider: str | None = None,
    fallback_model: str | None = None,
) -> dict:
    pending = collect_pending_word_seeds(word_seeds, overwrite=overwrite)
    stats = {
        'requested': len(word_seeds),
        'pending': len(pending),
        'enriched': 0,
        'failed': 0,
        'failed_words': [],
        'failure_details': [],
        'quota_exhausted': False,
        'stop_reason': '',
    }
    total_batches = (len(pending) + batch_size - 1) // batch_size if pending else 0

    def process(batch: list[dict], batch_index: int) -> None:
        if not batch:
            return
        try:
            _enrich_batch(
                batch,
                stats=stats,
                provider=provider,
                model=model,
                fallback_provider=fallback_provider,
                fallback_model=fallback_model,
            )
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
        except Exception as exc:
            db.session.rollback()
            if is_quota_exhausted_error(exc):
                stats['failed'] += len(batch)
                stats['failed_words'].extend(
                    seed['normalized_word']
                    for seed in batch
                )
                stats['failure_details'].append({
                    'word': batch[0]['normalized_word'],
                    'reason': str(exc),
                    'batch_size': len(batch),
                })
                stats['quota_exhausted'] = True
                stats['stop_reason'] = str(exc)
                print(
                    f'[Word Detail Enrichment] quota exhausted size={len(batch)} reason={exc}',
                    file=sys.stderr,
                    flush=True,
                )
                return
            print(
                f'[Word Detail Enrichment] split batch size={len(batch)} reason={exc}',
                file=sys.stderr,
                flush=True,
            )
            if len(batch) == 1:
                stats['failed'] += 1
                stats['failed_words'].append(batch[0]['normalized_word'])
                stats['failure_details'].append({
                    'word': batch[0]['normalized_word'],
                    'reason': str(exc),
                })
                return
            midpoint = max(1, len(batch) // 2)
            process(batch[:midpoint], batch_index)
            process(batch[midpoint:], batch_index + 1)

    for batch_index, start in enumerate(range(0, len(pending), batch_size), start=1):
        process(pending[start:start + batch_size], batch_index)
        print(
            f'[Word Detail Enrichment] batch {batch_index}/{total_batches} '
            f'enriched={stats["enriched"]} failed={stats["failed"]}'
        )
        if stats['quota_exhausted']:
            break

    return stats


def enrich_catalog_words(
    *,
    book_ids: tuple[str, ...] | None = None,
    words: list[str] | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    limit: int | None = None,
    overwrite: bool = False,
    sleep_seconds: float = 0.0,
    start_at: int = 0,
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
    fallback_provider: str | None = None,
    fallback_model: str | None = None,
) -> dict:
    seeds = collect_word_seeds(book_ids)
    if words:
        wanted = {_normalize_word(word) for word in words}
        seeds = [seed for seed in seeds if seed['normalized_word'] in wanted]
    if start_at > 0:
        seeds = seeds[start_at:]
    if limit is not None:
        seeds = seeds[:limit]

    stats = enrich_word_seeds(
        seeds,
        batch_size=batch_size,
        overwrite=overwrite,
        sleep_seconds=sleep_seconds,
        provider=provider,
        model=model,
        fallback_provider=fallback_provider,
        fallback_model=fallback_model,
    )
    return {
        **stats,
        'book_ids': list(book_ids or []),
        'provider': normalize_provider(provider),
        'model': resolve_model(normalize_provider(provider), model),
        'word_count': len(seeds),
    }


def enrich_premium_books(
    *,
    book_ids: tuple[str, ...] = PREMIUM_BOOK_IDS,
    words: list[str] | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    limit: int | None = None,
    overwrite: bool = False,
    sleep_seconds: float = 0.0,
    start_at: int = 0,
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
    fallback_provider: str | None = None,
    fallback_model: str | None = None,
) -> dict:
    return enrich_catalog_words(
        book_ids=book_ids,
        words=words,
        batch_size=batch_size,
        limit=limit,
        overwrite=overwrite,
        sleep_seconds=sleep_seconds,
        start_at=start_at,
        provider=provider,
        model=model,
        fallback_provider=fallback_provider,
        fallback_model=fallback_model,
    )
