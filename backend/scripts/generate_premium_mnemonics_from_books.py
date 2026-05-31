#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.premium_vocab_cleanup import normalize_premium_word
from services.premium_word_mnemonic_catalog import is_low_quality_mnemonic_text
from services.word_detail_llm_client import DISABLE_FALLBACK_PROVIDER
from services.word_memory_note_llm_client import request_memory_note_batch


BOOK_FILES = {
    'ielts_listening_premium': 'ielts_listening_premium.json',
    'ielts_reading_premium': 'ielts_reading_premium.json',
}
BADGES = {'助记', '联想', '词根词缀', '辨析', '串记', '扩展', '谐音', '词源', '口诀'}
SOURCE = 'premium_word_mnemonics'
GENERIC_PATTERN = re.compile(
    r'先抓核心义|放回句子判断|核心义仍是|记住它常落在|'
    r'按语境确定含义|放进真实场景里记|常见变体|词形变体|'
    r'-ain\s*表|后缀-ain'
)
CJK_RE = re.compile(r'[\u4e00-\u9fff]')


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


def _dedupe(values: list[str], limit: int) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = str(value or '').strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
        if len(result) >= limit:
            break
    return result


def _load_existing_items(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding='utf-8'))
    items = payload.get('items') if isinstance(payload, dict) else {}
    if not isinstance(items, dict):
        return {}
    return {
        str(word): item
        for word, item in items.items()
        if isinstance(item, dict) and item.get('text')
    }


def collect_book_word_seeds(book_ids: tuple[str, ...]) -> list[dict]:
    seed_index: dict[str, dict] = {}
    for book_id in book_ids:
        payload = json.loads(
            (REPO_ROOT / 'vocabulary_data' / BOOK_FILES[book_id]).read_text(
                encoding='utf-8',
            )
        )
        for chapter in payload['chapters']:
            for entry in chapter['words']:
                normalized_word = normalize_premium_word(entry.get('word'))
                if not normalized_word:
                    continue
                existing = seed_index.get(normalized_word, {})
                book_refs = [*existing.get('book_ids', []), book_id]
                definitions = [
                    *existing.get('definitions', []),
                    str(entry.get('definition') or entry.get('translation') or ''),
                ]
                seed_index[normalized_word] = {
                    'normalized_word': normalized_word,
                    'display_word': existing.get('display_word') or str(entry.get('word') or '').strip(),
                    'phonetic': existing.get('phonetic') or str(entry.get('phonetic') or '').strip(),
                    'pos': existing.get('pos') or str(entry.get('pos') or '').strip(),
                    'definitions': _dedupe(definitions, 3),
                    'examples': existing.get('examples', []),
                    'is_phrase': ' ' in normalized_word,
                    'book_ids': _dedupe(book_refs, 4),
                }
    return [seed_index[word] for word in sorted(seed_index)]


def _normalize_word(value: str | None) -> str:
    return normalize_premium_word(value)


def _sanitize_item(seed: dict, raw_item: dict) -> dict:
    badge = str(raw_item.get('badge') or '').strip()
    if badge not in BADGES:
        badge = '联想'
    text = re.sub(r'\s+', ' ', str(raw_item.get('text') or '').strip())
    text = text.replace('“ ', '“').replace(' ”', '”')
    if len(text) < 8:
        raise ValueError(f'memory note too short for {seed["normalized_word"]}')
    if len(text) > 180:
        raise ValueError(f'memory note too long for {seed["normalized_word"]}')
    if not CJK_RE.search(text):
        raise ValueError(f'memory note missing Chinese cue for {seed["normalized_word"]}')
    if GENERIC_PATTERN.search(text) or is_low_quality_mnemonic_text(text):
        raise ValueError(f'memory note is generic for {seed["normalized_word"]}')
    return {
        'word': seed['normalized_word'],
        'badge': badge,
        'text': text,
        'book_ids': list(seed.get('book_ids') or []),
        'source': SOURCE,
    }


def _manifest(book_ids: tuple[str, ...], items: dict[str, dict]) -> dict:
    return {
        'manifest_version': 1,
        'book_ids': list(book_ids),
        'generated_at': _utc_now_iso(),
        'items': dict(sorted(items.items())),
    }


def _summary(stats: dict, seeds: list[dict], items: dict[str, dict]) -> dict:
    expected = [seed['normalized_word'] for seed in seeds]
    missing = sorted(word for word in expected if word not in items)
    badges: dict[str, int] = {}
    for item in items.values():
        badge = str(item.get('badge') or '')
        badges[badge] = badges.get(badge, 0) + 1
    return {
        **stats,
        'coverage': {
            'total_words': len(expected),
            'covered_words': len(expected) - len(missing),
            'missing_count': len(missing),
            'missing_sample': missing[:20],
        },
        'badge_distribution': dict(sorted(badges.items())),
        'updated_at': _utc_now_iso(),
    }


def generate(args: argparse.Namespace) -> dict:
    book_ids = tuple(args.book or BOOK_FILES)
    seeds = collect_book_word_seeds(book_ids)
    if args.words:
        wanted = {normalize_premium_word(word) for word in args.words}
        seeds = [seed for seed in seeds if seed['normalized_word'] in wanted]
    if args.start_at > 0:
        seeds = seeds[args.start_at:]
    if args.limit is not None:
        seeds = seeds[:args.limit]

    output_path = Path(args.output_file)
    items = {} if args.overwrite else _load_existing_items(output_path)
    pending = [seed for seed in seeds if seed['normalized_word'] not in items]
    stats = {
        'requested': len(seeds),
        'pending': len(pending),
        'enriched': 0,
        'failed': 0,
        'failed_words': [],
        'failure_details': [],
        'completed_batches': 0,
        'total_batches': (len(pending) + args.batch_size - 1) // args.batch_size if pending else 0,
        'progress_state': 'running',
    }

    def write_progress() -> None:
        _write_json(output_path, _manifest(book_ids, items))
        if args.summary_file:
            _write_json(Path(args.summary_file), _summary(stats, seeds, items))
        if args.failure_file:
            _write_json(Path(args.failure_file), {
                'failed_count': len(stats['failed_words']),
                'failed_words': stats['failed_words'],
                'failure_details': stats['failure_details'],
            })

    def process(batch: list[dict]) -> None:
        if not batch:
            return
        try:
            raw_items = request_memory_note_batch(
                batch,
                provider=args.provider,
                model=args.model,
                fallback_provider=DISABLE_FALLBACK_PROVIDER if args.no_fallback else args.fallback_provider,
                fallback_model=args.fallback_model,
                normalize_word=_normalize_word,
            )
            for seed in batch:
                items[seed['normalized_word']] = _sanitize_item(
                    seed,
                    raw_items[seed['normalized_word']],
                )
            stats['enriched'] += len(batch)
            return
        except Exception as exc:
            if len(batch) > 1:
                midpoint = max(1, len(batch) // 2)
                process(batch[:midpoint])
                process(batch[midpoint:])
                return
            seed = batch[0]
            last_exc = exc
            for attempt in range(max(0, args.single_word_max_attempts - 1)):
                time.sleep(min(8.0, 0.75 * (attempt + 1)))
                try:
                    raw_items = request_memory_note_batch(
                        batch,
                        provider=args.provider,
                        model=args.model,
                        fallback_provider=DISABLE_FALLBACK_PROVIDER if args.no_fallback else args.fallback_provider,
                        fallback_model=args.fallback_model,
                        normalize_word=_normalize_word,
                    )
                    items[seed['normalized_word']] = _sanitize_item(
                        seed,
                        raw_items[seed['normalized_word']],
                    )
                    stats['enriched'] += 1
                    return
                except Exception as retry_exc:
                    last_exc = retry_exc
            stats['failed'] += 1
            stats['failed_words'].append(seed['normalized_word'])
            stats['failure_details'].append({
                'word': seed['normalized_word'],
                'reason': str(last_exc),
            })

    write_progress()
    for index, start in enumerate(range(0, len(pending), args.batch_size), start=1):
        process(pending[start:start + args.batch_size])
        stats['completed_batches'] = index
        write_progress()
        if args.sleep > 0:
            time.sleep(args.sleep)
    stats['progress_state'] = 'completed'
    write_progress()
    return _summary(stats, seeds, items)


def main() -> int:
    parser = argparse.ArgumentParser(description='Generate premium mnemonics from book JSON only.')
    parser.add_argument('--book', action='append', choices=sorted(BOOK_FILES), default=[])
    parser.add_argument('--word', dest='words', action='append', default=[])
    parser.add_argument('--output-file', required=True)
    parser.add_argument('--summary-file', default='')
    parser.add_argument('--failure-file', default='')
    parser.add_argument('--provider', default='minimax')
    parser.add_argument('--model', default='MiniMax-M2.7-highspeed')
    parser.add_argument('--fallback-provider', default='')
    parser.add_argument('--fallback-model', default='')
    parser.add_argument('--no-fallback', action='store_true')
    parser.add_argument('--batch-size', type=int, default=12)
    parser.add_argument('--sleep', type=float, default=0.0)
    parser.add_argument('--single-word-max-attempts', type=int, default=5)
    parser.add_argument('--start-at', type=int, default=0)
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    args.batch_size = max(1, args.batch_size)
    args.start_at = max(0, args.start_at)
    args.single_word_max_attempts = max(1, args.single_word_max_attempts)

    stats = generate(args)
    print('[Premium Mnemonics] done')
    print(f"requested={stats['requested']} pending={stats['pending']}")
    print(f"enriched={stats['enriched']} failed={stats['failed']}")
    print(f"covered={stats['coverage']['covered_words']}/{stats['coverage']['total_words']}")
    print(f"badges={json.dumps(stats['badge_distribution'], ensure_ascii=False, sort_keys=True)}")
    return 0 if stats['failed'] == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
