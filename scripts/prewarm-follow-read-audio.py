from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = REPO_ROOT / 'backend'
for candidate in (SCRIPT_DIR, BACKEND_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from dotenv import load_dotenv

from services.follow_read_segments_manifest_service import load_follow_read_sidecar_entries
from services.follow_read_segments_service import supported_follow_read_book_ids
from services.follow_read_timeline_service import _follow_read_chunk_cache_path, generate_follow_read_chunked_audio_bytes
from services.word_tts import is_probably_valid_mp3_file


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError('workers must be greater than 0')
    return parsed


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError('retries must be 0 or greater')
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Prewarm local follow-read three-pass audio cache for premium books.',
    )
    parser.add_argument(
        '--books',
        nargs='*',
        default=list(supported_follow_read_book_ids()),
        help='Premium book IDs to prewarm. Defaults to all supported premium books.',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='Stop after processing N unique follow-read entries. 0 means no limit.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only report the cache files that would be generated.',
    )
    parser.add_argument(
        '--full-word-provider',
        choices=('azure',),
        default='azure',
        help='Provider for the first/third full-word pass. Follow-read prewarm is pinned to Azure.',
    )
    parser.add_argument(
        '--workers',
        type=_positive_int,
        default=6,
        help='Number of concurrent follow-read prewarm workers. Defaults to 6.',
    )
    parser.add_argument(
        '--retries',
        type=_non_negative_int,
        default=3,
        help='Retry count for transient Azure/network failures. Defaults to 3.',
    )
    return parser.parse_args()


def _load_env() -> None:
    load_dotenv(BACKEND_DIR / '.env')
    load_dotenv(BACKEND_DIR / '.env.microservices.local', override=False)


def _collect_jobs(book_ids: list[str], limit: int) -> tuple[list[dict], int]:
    jobs: list[dict] = []
    skipped = 0
    seen_cache_paths: set[str] = set()
    for book_id in book_ids:
        entries = load_follow_read_sidecar_entries(book_id)
        for entry in entries.values():
            word = str(entry.get('word') or '').strip()
            phonetic = str(entry.get('phonetic') or '').strip() or None
            segments = entry.get('segments') or []
            cache_path = _follow_read_chunk_cache_path(word, phonetic, segments)
            cache_key = str(cache_path)
            if cache_key in seen_cache_paths:
                continue
            seen_cache_paths.add(cache_key)
            if cache_path.exists() and is_probably_valid_mp3_file(cache_path):
                skipped += 1
            else:
                jobs.append({
                    'book_id': book_id,
                    'word': word,
                    'phonetic': phonetic,
                    'cache_path': cache_path,
                })
            if limit > 0 and len(jobs) + skipped >= limit:
                return jobs, skipped
    return jobs, skipped


def _is_retryable_prewarm_error(exc: Exception) -> bool:
    message = str(exc or '').strip().lower()
    markers = (
        'timed out',
        'timeout',
        'max retries exceeded',
        'ssl',
        'eof occurred',
        'connection aborted',
        'connection reset',
        'remote end closed',
        'temporarily unavailable',
        'service unavailable',
        'bad gateway',
        '429',
        '502',
        '503',
        '504',
    )
    return any(marker in message for marker in markers)


def _generate_job(job: dict, retries: int) -> dict:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            generate_follow_read_chunked_audio_bytes(
                word=job['word'],
                phonetic=job['phonetic'],
            )
            return {**job, 'attempts': attempt + 1}
        except Exception as exc:
            last_error = exc
            if attempt >= retries or not _is_retryable_prewarm_error(exc):
                raise
            time.sleep(min(10.0, 1.5 * (2 ** attempt)))
    raise last_error if last_error is not None else RuntimeError('follow read prewarm failed without error')


def main() -> int:
    args = parse_args()
    supported = set(supported_follow_read_book_ids())
    book_ids = [book_id for book_id in args.books if book_id in supported]
    if not book_ids:
        raise RuntimeError('No supported premium book IDs were provided.')

    _load_env()
    jobs, skipped = _collect_jobs(book_ids, args.limit)
    processed = len(jobs) + skipped
    if args.dry_run:
        for index, job in enumerate(jobs, start=1):
            print(f"[dry-run {index}/{len(jobs)}] {job['word']}\t{job['cache_path']}")
        print(f'Summary: processed={processed} generated={len(jobs)} skipped={skipped} workers={args.workers}')
        return 0

    if not jobs:
        print(f'Summary: processed={processed} generated=0 skipped={skipped} workers={args.workers}')
        return 0

    generated = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=args.workers, thread_name_prefix='follow-read-prewarm') as executor:
        futures = {executor.submit(_generate_job, job, args.retries): job for job in jobs}
        for index, future in enumerate(as_completed(futures), start=1):
            job = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                failed += 1
                print(f"[failed {index}/{len(jobs)}] {job['word']}\t{job['cache_path']}\t{exc}")
                continue
            generated += 1
            attempts = int(result.get('attempts') or 1)
            retry_note = '' if attempts <= 1 else f'\tattempts={attempts}'
            print(f"[generated {index}/{len(jobs)}] {job['word']}\t{job['cache_path']}{retry_note}")

    print(
        f'Summary: processed={processed} generated={generated} '
        f'skipped={skipped} failed={failed} workers={args.workers} retries={args.retries}'
    )
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
