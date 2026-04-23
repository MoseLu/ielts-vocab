from __future__ import annotations

import re
import random
import sys
import time
from copy import deepcopy

from services import word_catalog_repository
from services.word_catalog_service import ensure_word_catalog_entry, normalize_word_key
from services.word_detail_enrichment import collect_word_seeds
from services.word_detail_llm_client import (
    DEFAULT_PROVIDER,
    is_quota_exhausted_error,
    is_rate_limit_error,
)
from services.word_memory_note_llm_client import request_memory_note_batch


PREMIUM_BOOK_IDS = (
    'ielts_listening_premium',
    'ielts_reading_premium',
)
DEFAULT_BATCH_SIZE = 8
MEMORY_NOTE_SOURCE = 'llm_memory'
DEFAULT_RATE_LIMIT_MAX_ATTEMPTS = 0
DEFAULT_RATE_LIMIT_BASE_SLEEP_SECONDS = 20.0
DEFAULT_RATE_LIMIT_MAX_SLEEP_SECONDS = 600.0
_ONLY_LATIN_FORMULA_RE = re.compile(r'^[A-Za-z0-9\s\-\+\=\>\(\)\[\]/,.;:]+$')
_CJK_RE = re.compile(r'[\u4e00-\u9fff]')


def _compact_text(value: str | None) -> str:
    return re.sub(r'[\W_]+', '', str(value or '').lower())


def _normalize_note_text(value: str | None) -> str:
    text = re.sub(r'\s+', ' ', str(value or '')).strip()
    return text.replace('“ ', '“').replace(' ”', '”')


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


def _definition_terms(definitions: list[str]) -> list[str]:
    terms: list[str] = []
    seen = set()
    for definition in definitions:
        text = re.sub(r'^[A-Za-z]+\.\s*', '', str(definition or '')).strip()
        for part in re.split(r'[;；,，/、()（）]+', text):
            term = str(part or '').strip()
            if len(term) < 2 or not _CJK_RE.search(term):
                continue
            if term in seen:
                continue
            seen.add(term)
            terms.append(term)
            if len(terms) >= 12:
                return terms
    return terms


def _is_phrase(display_word: str) -> bool:
    return bool(re.search(r'\s', str(display_word or '').strip()))


def collect_memory_word_seeds(
    book_ids: tuple[str, ...] | None = PREMIUM_BOOK_IDS,
) -> list[dict]:
    selected_book_ids = set(book_ids or ())
    merged: list[dict] = []
    records = sorted(
        word_catalog_repository.list_all_word_catalog_entries(),
        key=lambda record: record.normalized_word,
    )
    for record in records:
        book_refs = record.get_book_refs()
        if selected_book_ids:
            book_refs = [
                item
                for item in book_refs
                if item.get('book_id') in selected_book_ids
            ]
        if not book_refs:
            continue
        display_word = str(record.word or '').strip() or record.normalized_word
        definition = str(record.definition or '').strip()
        merged.append({
            'word': record.normalized_word,
            'display_word': display_word,
            'normalized_word': record.normalized_word,
            'phonetic': str(record.phonetic or '').strip(),
            'pos': str(record.pos or '').strip(),
            'definition': definition,
            'definitions': _dedupe_texts([definition], 3),
            'examples': record.get_examples(),
            'book_refs': book_refs,
            'book_ids': _dedupe_texts(
                [item.get('book_id', '') for item in book_refs],
                8,
            ),
            'is_phrase': _is_phrase(display_word),
        })
    if merged:
        return merged

    for seed in collect_word_seeds(book_ids):
        merged.append({
            **seed,
            'definitions': _dedupe_texts([seed.get('definition', '')], 3),
            'book_ids': _dedupe_texts(
                [item.get('book_id', '') for item in seed.get('book_refs', [])],
                8,
            ),
            'is_phrase': _is_phrase(seed.get('display_word', '')),
        })
    return merged


def _has_memory_note(catalog_entry) -> bool:
    if not catalog_entry:
        return False
    note = catalog_entry.get_memory_note()
    return bool(note and note.get('text'))


def _build_record_index(word_seeds: list[dict]) -> dict[str, object]:
    normalized_words = [
        seed['normalized_word']
        for seed in word_seeds
        if seed.get('normalized_word')
    ]
    if not normalized_words:
        return {}
    records = word_catalog_repository.list_word_catalog_entries_by_normalized_words(
        normalized_words,
    )
    return {record.normalized_word: record for record in records}


def collect_pending_memory_word_seeds(
    word_seeds: list[dict],
    *,
    overwrite: bool = False,
) -> list[dict]:
    if overwrite:
        return list(word_seeds)

    record_index = _build_record_index(word_seeds)
    return [
        seed
        for seed in word_seeds
        if not _has_memory_note(record_index.get(seed['normalized_word']))
    ]


def _looks_like_formula_text(text: str, *, is_phrase: bool) -> bool:
    if _ONLY_LATIN_FORMULA_RE.fullmatch(text):
        return True
    if re.search(r'[+=]|->|→', text) and len(_CJK_RE.findall(text)) < 4:
        return True
    if is_phrase and re.search(r'[+=]|->|→', text):
        return True
    return False


def _definition_echo(text: str, definitions: list[str]) -> bool:
    compact_text = _compact_text(text)
    if not compact_text:
        return True
    compact_definitions = {
        _compact_text(definition)
        for definition in definitions
        if str(definition or '').strip()
    }
    return compact_text in compact_definitions


def _has_definition_anchor(text: str, definitions: list[str]) -> bool:
    terms = _definition_terms(definitions)
    if not terms:
        return True
    return any(term in text for term in terms)


def _sanitize_memory_note_payload(word_seed: dict, raw_item: dict) -> dict:
    if not isinstance(raw_item, dict):
        raise ValueError('memory note payload must be an object')

    badge = str(raw_item.get('badge') or '').strip() or '联想'
    if badge not in {'谐音', '联想'}:
        badge = '联想'

    text = _normalize_note_text(raw_item.get('text') or raw_item.get('note') or '')
    if len(text) < 10:
        raise ValueError(f'memory note too short for {word_seed["normalized_word"]}')
    if len(text) > 120:
        raise ValueError(f'memory note too long for {word_seed["normalized_word"]}')
    if not _CJK_RE.search(text):
        raise ValueError(f'memory note missing Chinese cue for {word_seed["normalized_word"]}')
    if _compact_text(text) in {
        _compact_text(word_seed['display_word']),
        _compact_text(word_seed['normalized_word']),
    }:
        raise ValueError(f'memory note only repeats word for {word_seed["normalized_word"]}')
    if _definition_echo(text, word_seed['definitions']):
        raise ValueError(f'memory note only repeats definition for {word_seed["normalized_word"]}')
    if not _has_definition_anchor(text, word_seed['definitions']):
        raise ValueError(f'memory note missing definition anchor for {word_seed["normalized_word"]}')
    if _looks_like_formula_text(text, is_phrase=bool(word_seed['is_phrase'])):
        raise ValueError(f'memory note looks formulaic for {word_seed["normalized_word"]}')

    return {'badge': badge, 'text': text}


def _persist_memory_note(word_seed: dict, raw_item: dict) -> None:
    note = _sanitize_memory_note_payload(word_seed, raw_item)
    record, _changed = ensure_word_catalog_entry(word_seed['display_word'])
    record.set_memory_note({
        **note,
        'source': MEMORY_NOTE_SOURCE,
    })


def _retry_delay_seconds(attempt: int, *, base: float, cap: float) -> float:
    exponent = min(max(0, attempt - 1), 6)
    delay = min(cap, base * (2 ** exponent))
    jitter = min(5.0, max(0.5, base * 0.1))
    return min(cap, delay + random.uniform(0.0, jitter))


def _enrich_batch(
    word_seeds: list[dict],
    *,
    stats: dict,
    provider: str,
    model: str | None,
    fallback_provider: str | None,
    fallback_model: str | None,
    rate_limit_max_attempts: int,
    rate_limit_base_sleep_seconds: float,
    rate_limit_max_sleep_seconds: float,
) -> None:
    db_lock_attempt = 0
    rate_limit_attempt = 0
    while True:
        try:
            raw_items = request_memory_note_batch(
                word_seeds,
                provider=provider,
                model=model,
                fallback_provider=fallback_provider,
                fallback_model=fallback_model,
                normalize_word=normalize_word_key,
            )
            for word_seed in word_seeds:
                _persist_memory_note(
                    word_seed,
                    raw_items[word_seed['normalized_word']],
                )
            word_catalog_repository.commit()
            stats['enriched'] += len(word_seeds)
            return
        except Exception as exc:
            word_catalog_repository.rollback()
            error_text = str(exc).lower()
            if 'database is locked' in error_text and db_lock_attempt < 8:
                db_lock_attempt += 1
                delay = 0.5 * db_lock_attempt
                print(
                    '[Word Memory Enrichment] database locked '
                    f'attempt={db_lock_attempt} sleep={delay:.1f}s reason={exc}',
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(delay)
                continue
            if is_rate_limit_error(exc):
                rate_limit_attempt += 1
                if (
                    rate_limit_max_attempts > 0
                    and rate_limit_attempt >= rate_limit_max_attempts
                ):
                    raise
                delay = _retry_delay_seconds(
                    rate_limit_attempt,
                    base=rate_limit_base_sleep_seconds,
                    cap=rate_limit_max_sleep_seconds,
                )
                stats['rate_limit_retries'] += 1
                stats['rate_limit_wait_seconds'] += delay
                print(
                    '[Word Memory Enrichment] rate limited '
                    f'attempt={rate_limit_attempt} sleep={delay:.1f}s '
                    f'size={len(word_seeds)} reason={exc}',
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(delay)
                continue
            raise


def enrich_memory_word_seeds(
    word_seeds: list[dict],
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    overwrite: bool = False,
    sleep_seconds: float = 0.0,
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
    fallback_provider: str | None = None,
    fallback_model: str | None = None,
    rate_limit_max_attempts: int = DEFAULT_RATE_LIMIT_MAX_ATTEMPTS,
    rate_limit_base_sleep_seconds: float = DEFAULT_RATE_LIMIT_BASE_SLEEP_SECONDS,
    rate_limit_max_sleep_seconds: float = DEFAULT_RATE_LIMIT_MAX_SLEEP_SECONDS,
    progress_callback=None,
) -> dict:
    pending = collect_pending_memory_word_seeds(word_seeds, overwrite=overwrite)
    stats = {
        'requested': len(word_seeds),
        'pending': len(pending),
        'enriched': 0,
        'failed': 0,
        'failed_words': [],
        'failure_details': [],
        'quota_exhausted': False,
        'stop_reason': '',
        'rate_limit_retries': 0,
        'rate_limit_wait_seconds': 0.0,
    }
    total_batches = (len(pending) + batch_size - 1) // batch_size if pending else 0
    stats['total_batches'] = total_batches
    stats['completed_batches'] = 0

    def emit_progress() -> None:
        if not progress_callback:
            return
        progress_callback(deepcopy(stats))

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
                rate_limit_max_attempts=rate_limit_max_attempts,
                rate_limit_base_sleep_seconds=rate_limit_base_sleep_seconds,
                rate_limit_max_sleep_seconds=rate_limit_max_sleep_seconds,
            )
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
        except Exception as exc:
            word_catalog_repository.rollback()
            if is_rate_limit_error(exc):
                raise RuntimeError(
                    'rate limit retries exhausted before batch completed: '
                    f'{exc}'
                ) from exc
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
                    f'[Word Memory Enrichment] quota exhausted size={len(batch)} reason={exc}',
                    file=sys.stderr,
                    flush=True,
                )
                return
            print(
                f'[Word Memory Enrichment] split batch size={len(batch)} reason={exc}',
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
        stats['completed_batches'] = batch_index
        print(
            f'[Word Memory Enrichment] batch {batch_index}/{total_batches} '
            f'enriched={stats["enriched"]} failed={stats["failed"]}',
            flush=True,
        )
        emit_progress()
        if stats['quota_exhausted']:
            break

    emit_progress()
    return stats


def enrich_catalog_memory_notes(
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
    rate_limit_max_attempts: int = DEFAULT_RATE_LIMIT_MAX_ATTEMPTS,
    rate_limit_base_sleep_seconds: float = DEFAULT_RATE_LIMIT_BASE_SLEEP_SECONDS,
    rate_limit_max_sleep_seconds: float = DEFAULT_RATE_LIMIT_MAX_SLEEP_SECONDS,
    progress_callback=None,
) -> dict:
    seeds = collect_memory_word_seeds(book_ids)
    if words:
        wanted = {normalize_word_key(word) for word in words}
        seeds = [seed for seed in seeds if seed['normalized_word'] in wanted]
    if start_at > 0:
        seeds = seeds[start_at:]
    if limit is not None:
        seeds = seeds[:limit]

    stats = enrich_memory_word_seeds(
        seeds,
        batch_size=batch_size,
        overwrite=overwrite,
        sleep_seconds=sleep_seconds,
        provider=provider,
        model=model,
        fallback_provider=fallback_provider,
        fallback_model=fallback_model,
        rate_limit_max_attempts=rate_limit_max_attempts,
        rate_limit_base_sleep_seconds=rate_limit_base_sleep_seconds,
        rate_limit_max_sleep_seconds=rate_limit_max_sleep_seconds,
        progress_callback=progress_callback,
    )
    return {
        **stats,
        'book_ids': list(book_ids or []),
        'provider': provider,
        'model': model or '',
        'word_count': len(seeds),
    }


def enrich_premium_book_memory_notes(
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
    rate_limit_max_attempts: int = DEFAULT_RATE_LIMIT_MAX_ATTEMPTS,
    rate_limit_base_sleep_seconds: float = DEFAULT_RATE_LIMIT_BASE_SLEEP_SECONDS,
    rate_limit_max_sleep_seconds: float = DEFAULT_RATE_LIMIT_MAX_SLEEP_SECONDS,
    progress_callback=None,
) -> dict:
    return enrich_catalog_memory_notes(
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
        rate_limit_max_attempts=rate_limit_max_attempts,
        rate_limit_base_sleep_seconds=rate_limit_base_sleep_seconds,
        rate_limit_max_sleep_seconds=rate_limit_max_sleep_seconds,
        progress_callback=progress_callback,
    )
