from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from services import word_memory_note_enrichment as memory_enrichment


MEMORY_NOTE_SOURCE = 'premium_word_mnemonics'
DEFAULT_SINGLE_WORD_MAX_ATTEMPTS = 3
TRANSIENT_ERROR_MARKERS = (
    'SSLEOFError',
    'UNEXPECTED_EOF',
    'Connection aborted',
    'Connection reset',
    'Read timed out',
    'Max retries exceeded',
    'RemoteDisconnected',
)


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f'{path.suffix}.tmp')
    temp_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding='utf-8',
    )
    temp_path.replace(path)


def _load_existing_items(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    items = payload.get('items') if isinstance(payload, dict) else {}
    if not isinstance(items, dict):
        return {}
    return {
        str(word): item
        for word, item in items.items()
        if isinstance(item, dict) and item.get('text')
    }


def _format_item(seed: dict, raw_item: dict) -> dict:
    note = memory_enrichment._sanitize_memory_note_payload(seed, raw_item)
    return {
        'word': seed['normalized_word'],
        'badge': note['badge'],
        'text': note['text'],
        'book_ids': list(seed.get('book_ids') or []),
        'source': MEMORY_NOTE_SOURCE,
    }


def _manifest(book_ids: tuple[str, ...], items: dict[str, dict]) -> dict:
    return {
        'manifest_version': 1,
        'book_ids': list(book_ids),
        'generated_at': _utc_now_iso(),
        'items': dict(sorted(items.items())),
    }


def _coverage(word_seeds: list[dict], items: dict[str, dict]) -> dict:
    expected = [seed['normalized_word'] for seed in word_seeds]
    missing = sorted(word for word in expected if word not in items)
    return {
        'total_words': len(expected),
        'covered_words': len(expected) - len(missing),
        'missing_words': missing,
    }


def _coverage_summary(word_seeds: list[dict], items: dict[str, dict]) -> dict:
    coverage = _coverage(word_seeds, items)
    missing_words = coverage['missing_words']
    return {
        'total_words': coverage['total_words'],
        'covered_words': coverage['covered_words'],
        'missing_count': len(missing_words),
        'missing_sample': missing_words[:20],
    }


def _badge_distribution(items: dict[str, dict]) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for item in items.values():
        badge = str(item.get('badge') or '').strip()
        if not badge:
            continue
        distribution[badge] = distribution.get(badge, 0) + 1
    return dict(sorted(distribution.items()))


def _sample_items(items: dict[str, dict], limit: int = 8) -> list[dict]:
    return [
        {'word': word, 'badge': item.get('badge', ''), 'text': item.get('text', '')}
        for word, item in list(sorted(items.items()))[:limit]
    ]


def _is_retryable_error(exc: Exception) -> bool:
    text = str(exc)
    return memory_enrichment.is_rate_limit_error(exc) or any(
        marker in text
        for marker in TRANSIENT_ERROR_MARKERS
    )


def enrich_premium_book_memory_note_file(
    *,
    output_path: str | Path,
    book_ids: tuple[str, ...] = memory_enrichment.PREMIUM_BOOK_IDS,
    words: list[str] | None = None,
    batch_size: int = memory_enrichment.DEFAULT_BATCH_SIZE,
    limit: int | None = None,
    overwrite: bool = False,
    sleep_seconds: float = 0.0,
    start_at: int = 0,
    provider: str = memory_enrichment.DEFAULT_PROVIDER,
    model: str | None = None,
    fallback_provider: str | None = None,
    fallback_model: str | None = None,
    rate_limit_max_attempts: int = memory_enrichment.DEFAULT_RATE_LIMIT_MAX_ATTEMPTS,
    rate_limit_base_sleep_seconds: float = memory_enrichment.DEFAULT_RATE_LIMIT_BASE_SLEEP_SECONDS,
    rate_limit_max_sleep_seconds: float = memory_enrichment.DEFAULT_RATE_LIMIT_MAX_SLEEP_SECONDS,
    single_word_max_attempts: int = DEFAULT_SINGLE_WORD_MAX_ATTEMPTS,
    progress_path: str | Path | None = None,
    failure_path: str | Path | None = None,
    progress_callback=None,
) -> dict:
    path = Path(output_path)
    seeds = memory_enrichment.collect_memory_word_seeds(book_ids)
    if words:
        wanted = {memory_enrichment.normalize_word_key(word) for word in words}
        seeds = [seed for seed in seeds if seed['normalized_word'] in wanted]
    if start_at > 0:
        seeds = seeds[start_at:]
    if limit is not None:
        seeds = seeds[:limit]

    items = {} if overwrite else _load_existing_items(path)
    pending = [seed for seed in seeds if overwrite or seed['normalized_word'] not in items]
    stats = {
        'requested': len(seeds),
        'pending': len(pending),
        'enriched': 0,
        'failed': 0,
        'failed_words': [],
        'failure_details': [],
        'total_batches': (len(pending) + batch_size - 1) // batch_size if pending else 0,
        'completed_batches': 0,
    }

    def emit_progress() -> None:
        current = {
            **stats,
            'coverage': _coverage_summary(seeds, items),
            'badge_distribution': _badge_distribution(items),
            'sample_items': _sample_items(items),
            'updated_at': _utc_now_iso(),
        }
        if progress_path:
            _write_json(Path(progress_path), current)
        if progress_callback:
            progress_callback(deepcopy(current))

    def write_output() -> None:
        _write_json(path, _manifest(book_ids, items))
        if failure_path:
            _write_json(Path(failure_path), {
                'failed_count': len(stats['failed_words']),
                'failed_words_tail': stats['failed_words'][-50:],
                'failure_details_tail': stats['failure_details'][-50:],
            })

    def process(batch: list[dict]) -> None:
        if not batch:
            return
        attempt = 0
        try:
            while True:
                try:
                    raw_items = memory_enrichment.request_memory_note_batch(
                        batch,
                        provider=provider,
                        model=model,
                        fallback_provider=fallback_provider,
                        fallback_model=fallback_model,
                        normalize_word=memory_enrichment.normalize_word_key,
                    )
                    break
                except Exception as exc:
                    if not _is_retryable_error(exc):
                        raise
                    attempt += 1
                    if (
                        rate_limit_max_attempts > 0
                        and attempt >= rate_limit_max_attempts
                    ):
                        raise
                    delay = memory_enrichment._retry_delay_seconds(
                        attempt,
                        base=rate_limit_base_sleep_seconds,
                        cap=rate_limit_max_sleep_seconds,
                    )
                    memory_enrichment.time.sleep(delay)
            for seed in batch:
                items[seed['normalized_word']] = _format_item(
                    seed,
                    raw_items[seed['normalized_word']],
                )
            stats['enriched'] += len(batch)
        except Exception as exc:
            if len(batch) > 1:
                midpoint = max(1, len(batch) // 2)
                process(batch[:midpoint])
                process(batch[midpoint:])
                return
            for _attempt in range(1, max(1, single_word_max_attempts)):
                delay_base = rate_limit_base_sleep_seconds if _is_retryable_error(exc) else 1.0
                try:
                    raw_items = memory_enrichment.request_memory_note_batch(
                        batch,
                        provider=provider,
                        model=model,
                        fallback_provider=fallback_provider,
                        fallback_model=fallback_model,
                        normalize_word=memory_enrichment.normalize_word_key,
                    )
                    seed = batch[0]
                    items[seed['normalized_word']] = _format_item(
                        seed,
                        raw_items[seed['normalized_word']],
                    )
                    stats['enriched'] += 1
                    return
                except Exception as retry_exc:
                    exc = retry_exc
                    delay = memory_enrichment._retry_delay_seconds(
                        _attempt,
                        base=delay_base,
                        cap=rate_limit_max_sleep_seconds,
                    )
                    memory_enrichment.time.sleep(delay)
            stats['failed'] += 1
            stats['failed_words'].append(batch[0]['normalized_word'])
            stats['failure_details'].append({
                'word': batch[0]['normalized_word'],
                'reason': str(exc),
            })

    for index, start in enumerate(range(0, len(pending), max(1, batch_size)), start=1):
        process(pending[start:start + max(1, batch_size)])
        stats['completed_batches'] = index
        write_output()
        emit_progress()
        if sleep_seconds > 0:
            memory_enrichment.time.sleep(sleep_seconds)

    write_output()
    coverage = _coverage(seeds, items)
    return {
        **stats,
        'book_ids': list(book_ids),
        'provider': provider,
        'model': model or '',
        'word_count': len(seeds),
        'coverage': coverage,
        'badge_distribution': _badge_distribution(items),
        'sample_items': _sample_items(items),
    }
