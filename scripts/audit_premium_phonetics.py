#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / 'backend'
SDK_ROOT = REPO_ROOT / 'packages' / 'platform-sdk'
for candidate in (BACKEND_ROOT, SDK_ROOT, Path(__file__).resolve().parent):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from premium_phonetic_audit_support import (  # noqa: E402
    PREMIUM_BOOK_IDS,
    SourceFetcher,
    audit_word,
    has_unsafe_marker,
    write_audit_csv,
    write_jsonl,
)
from services import phonetic_lookup_service  # noqa: E402
from services.word_tts import collect_unique_words  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Audit premium-book phonetics against two or more dictionary sources.',
    )
    parser.add_argument('--book-id', action='append', dest='book_ids', default=[])
    parser.add_argument('--word', action='append', default=[])
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--only-unsafe', action='store_true')
    parser.add_argument('--only-overrides', action='store_true')
    parser.add_argument('--refresh-sources', action='store_true')
    parser.add_argument('--use-wiktionary-fallback', action='store_true')
    parser.add_argument('--timeout', type=float, default=12.0)
    parser.add_argument('--delay', type=float, default=0.2)
    parser.add_argument('--apply-overrides', action='store_true')
    parser.add_argument('--output-dir', default='')
    parser.add_argument('--cache-file', default='')
    return parser


def _default_output_dir() -> Path:
    timestamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    return REPO_ROOT / 'output' / 'phonetic-audit' / timestamp


def _select_words(book_ids: list[str], *, only_unsafe: bool, only_overrides: bool) -> list[str]:
    selected_books = book_ids or list(PREMIUM_BOOK_IDS)
    words = collect_unique_words(selected_books)
    overrides = phonetic_lookup_service.load_phonetic_overrides()
    local_lookup = phonetic_lookup_service.lookup_local_phonetics(words)
    selected = []
    for word in words:
        key = phonetic_lookup_service.normalize_word_key(word)
        current = local_lookup.get(key, '')
        if only_unsafe and not has_unsafe_marker(current):
            continue
        if only_overrides and key not in overrides:
            continue
        selected.append(word)
    return selected


def _dedupe_requested_words(values: list[str]) -> list[str]:
    seen = set()
    words = []
    for value in values:
        word = value.strip()
        key = phonetic_lookup_service.normalize_word_key(word)
        if not key or key in seen:
            continue
        seen.add(key)
        words.append(word)
    return words


def _source_results(fetcher: SourceFetcher, word: str, *, use_wiktionary_fallback: bool):
    results = [fetcher.fetch(source, word) for source in ('oxford', 'cambridge', 'longman')]
    usable_sources = {result.source for result in results if result.phonetics}
    if not use_wiktionary_fallback or len(usable_sources) >= 3:
        return results
    for fallback in ('wiktionary',):
        result = fetcher.fetch(fallback, word)
        results.append(result)
        if result.phonetics:
            usable_sources.add(result.source)
    return results


def _write_rerun_list(path: Path, records) -> list[dict]:
    reruns = [
        {
            'word': record.word,
            'current_phonetic': record.current_phonetic,
            'new_phonetic': record.consensus_phonetic,
            'confidence': record.confidence,
            'voters': record.voters,
            'sources': record.sources,
        }
        for record in records
        if record.auto_fixable
    ]
    path.write_text(json.dumps(reruns, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return reruns


def _apply_overrides(records) -> int:
    overrides = phonetic_lookup_service.load_phonetic_overrides().copy()
    changed = 0
    for record in records:
        if not record.auto_fixable:
            continue
        key = phonetic_lookup_service.normalize_word_key(record.word)
        if overrides.get(key) == record.consensus_phonetic:
            continue
        overrides[key] = record.consensus_phonetic
        changed += 1
    if changed:
        phonetic_lookup_service.save_phonetic_overrides(overrides)
    return changed


def _audit_records(
    words: list[str],
    local_lookup,
    fetcher: SourceFetcher,
    *,
    jobs: int,
    use_wiktionary_fallback: bool,
):
    def audit_one(word: str):
        key = phonetic_lookup_service.normalize_word_key(word)
        current = local_lookup.get(key, '')
        return audit_word(
            word,
            current,
            _source_results(fetcher, word, use_wiktionary_fallback=use_wiktionary_fallback),
        )

    worker_count = max(1, jobs)
    if worker_count == 1:
        records = []
        for index, word in enumerate(words, start=1):
            record = audit_one(word)
            records.append(record)
            if index % 50 == 0 or index == len(words):
                print(f'[phonetic-audit] {index}/{len(words)} {record.status} {word}', flush=True)
        return records

    records = [None] * len(words)
    completed = 0
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(audit_one, word): (index, word)
            for index, word in enumerate(words)
        }
        for future in as_completed(futures):
            index, word = futures[future]
            record = future.result()
            records[index] = record
            completed += 1
            if completed % 50 == 0 or completed == len(words):
                print(f'[phonetic-audit] {completed}/{len(words)} {record.status} {word}', flush=True)
    return records


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_path = (
        Path(args.cache_file).resolve()
        if args.cache_file
        else output_dir.parent / 'source-cache.jsonl'
    )

    if args.word:
        words = _dedupe_requested_words(args.word)
    else:
        words = _select_words(
            args.book_ids,
            only_unsafe=args.only_unsafe,
            only_overrides=args.only_overrides,
        )
    if args.limit > 0:
        words = words[:args.limit]
    local_lookup = phonetic_lookup_service.lookup_local_phonetics(words)
    fetcher = SourceFetcher(
        cache_path=cache_path,
        timeout=args.timeout,
        delay_seconds=args.delay,
        refresh=args.refresh_sources,
    )

    records = _audit_records(
        words,
        local_lookup,
        fetcher,
        jobs=args.jobs,
        use_wiktionary_fallback=args.use_wiktionary_fallback,
    )

    write_jsonl(output_dir / 'audit.jsonl', records)
    write_audit_csv(output_dir / 'audit.csv', records)
    manual_records = [record for record in records if record.status != 'confirmed']
    write_audit_csv(output_dir / 'manual-review.csv', manual_records)
    reruns = _write_rerun_list(output_dir / 'rerun-list.json', records)
    override_changes = _apply_overrides(records) if args.apply_overrides else 0

    stats = {status: 0 for status in sorted({record.status for record in records})}
    for record in records:
        stats[record.status] = stats.get(record.status, 0) + 1
    summary = {
        'book_ids': args.book_ids or list(PREMIUM_BOOK_IDS),
        'total_words': len(words),
        'status_counts': stats,
        'auto_fixable': len(reruns),
        'override_changes': override_changes,
        'output_dir': str(output_dir),
        'cache_file': str(cache_path),
    }
    (output_dir / 'summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
