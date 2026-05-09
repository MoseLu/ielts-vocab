#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / 'backend'
SDK_ROOT = REPO_ROOT / 'packages' / 'platform-sdk'
SCRIPTS_ROOT = Path(__file__).resolve().parent
for candidate in (BACKEND_ROOT, SDK_ROOT, SCRIPTS_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from premium_phonetic_audit_support import PREMIUM_BOOK_IDS  # noqa: E402
from services.word_tts import collect_unique_words  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Verify production word-audio metadata for premium books.')
    parser.add_argument('--base-url', default='https://axiomaticworld.com')
    parser.add_argument('--book-id', action='append', dest='book_ids', default=[])
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--timeout', type=float, default=15.0)
    parser.add_argument('--output-dir', default='')
    return parser


def _default_output_dir() -> Path:
    timestamp = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    return REPO_ROOT / 'output' / 'word-audio-prod-verify' / timestamp


def _metadata_url(base_url: str, word: str) -> str:
    return f"{base_url.rstrip('/')}/api/tts/word-audio/metadata?{urlencode({'w': word})}"


def _check_word(base_url: str, word: str, timeout: float) -> dict:
    url = _metadata_url(base_url, word)
    try:
        response = requests.get(url, timeout=timeout)
    except Exception as exc:
        return {'word': word, 'status': 'request_error', 'error': str(exc)[:300]}
    row = {
        'word': word,
        'http_status': response.status_code,
        'status': 'ok' if response.status_code == 200 else 'http_error',
        'cache_hit': '',
        'content_type': '',
        'byte_length': '',
        'object_key': '',
        'error': '',
    }
    if response.status_code != 200:
        row['error'] = response.text[:300]
        return row
    try:
        payload = response.json()
    except Exception as exc:
        row['status'] = 'json_error'
        row['error'] = str(exc)[:300]
        return row
    row.update({
        'cache_hit': bool(payload.get('cache_hit', True)),
        'content_type': payload.get('content_type') or '',
        'byte_length': payload.get('byte_length') or '',
        'object_key': payload.get('object_key') or payload.get('media_id') or '',
    })
    if row['content_type'] != 'audio/mpeg' or not row['byte_length']:
        row['status'] = 'metadata_mismatch'
    return row


def _write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = ['word', 'status', 'http_status', 'cache_hit', 'content_type', 'byte_length', 'object_key', 'error']
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    words = collect_unique_words(args.book_ids or list(PREMIUM_BOOK_IDS))
    if args.limit > 0:
        words = words[:args.limit]
    output_dir = Path(args.output_dir).resolve() if args.output_dir else _default_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as executor:
        futures = {
            executor.submit(_check_word, args.base_url, word, args.timeout): word
            for word in words
        }
        for index, future in enumerate(as_completed(futures), start=1):
            row = future.result()
            rows.append(row)
            if index % 100 == 0 or index == len(words):
                print(f"[prod-audio-verify] {index}/{len(words)} {row['status']} {row['word']}")

    rows.sort(key=lambda row: str(row['word']).lower())
    _write_csv(output_dir / 'metadata.csv', rows)
    (output_dir / 'metadata.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    stats: dict[str, int] = {}
    for row in rows:
        stats[row['status']] = stats.get(row['status'], 0) + 1
    summary = {'total_words': len(words), 'status_counts': stats, 'output_dir': str(output_dir)}
    (output_dir / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if stats.get('ok', 0) == len(words) else 1


if __name__ == '__main__':
    raise SystemExit(main())
