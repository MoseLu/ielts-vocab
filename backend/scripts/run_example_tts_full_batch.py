#!/usr/bin/env python3
"""
CLI: 批量生成词书例句百炼 TTS。

用法:
  python scripts/run_example_tts_full_batch.py --book ielts_listening_premium --book ielts_reading_premium
  python scripts/run_example_tts_full_batch.py --rate-interval 7
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(BACKEND_ROOT / '.env')


parser = argparse.ArgumentParser(description='百炼例句 TTS 批量生成')
parser.add_argument(
    '--book',
    action='append',
    default=[],
    help='仅跑指定词书 id，可重复传入多次',
)
parser.add_argument(
    '--rate-interval',
    type=float,
    default=None,
    help='相邻 API 请求最小间隔秒数；未指定时按模型自动推断',
)
parser.add_argument(
    '--limit',
    type=int,
    default=None,
    help='仅处理前 N 条唯一例句，便于 smoke test',
)
args = parser.parse_args()

_MINIMAX_EXAMPLE_VOICES = ['English_Trustworthy_Man', 'Serene_Woman']


def add_pause_tags(text: str, pause_seconds: float = 0.4) -> str:
    import re

    pause_tag = f'<#{pause_seconds}#>'
    text = re.sub(r',(\s*)', f',{pause_tag}\\1', text)
    text = re.sub(r'([.!?])(\s+)', f'{pause_tag}\\1\\2', text)
    text = re.sub(r';(\s*)', f';{pause_tag}\\1', text)
    return text


def _provider() -> str:
    return os.environ.get('BAILIAN_TTS_PROVIDER', 'minimax').strip().lower()


def _require_provider_credentials(provider: str) -> bool:
    if provider == 'azure':
        if not os.environ.get('AZURE_SPEECH_KEY', '').strip():
            print('ERROR: 请在 backend/.env 中设置 AZURE_SPEECH_KEY', file=sys.stderr)
            return False
        if not os.environ.get('AZURE_SPEECH_REGION', '').strip():
            print('ERROR: 请在 backend/.env 中设置 AZURE_SPEECH_REGION', file=sys.stderr)
            return False
        return True

    if provider != 'minimax' and not os.environ.get('DASHSCOPE_API_KEY', '').strip():
        print('ERROR: 请在 backend/.env 中设置 DASHSCOPE_API_KEY', file=sys.stderr)
        return False
    return True


def _cache_dir() -> Path:
    d = BACKEND_ROOT / 'tts_cache'
    d.mkdir(parents=True, exist_ok=True)
    return d


def _progress_file() -> Path:
    return _cache_dir() / 'progress_examples_batch.json'


def _write_progress(
    total: int,
    completed: int,
    status: str,
    book_ids: list[str] | None,
    *,
    current_sentence: str | None = None,
) -> None:
    payload: dict[str, object] = {
        'total': total,
        'completed': completed,
        'status': status,
        'updated_at': datetime.utcnow().isoformat(),
        'book_ids': book_ids or [],
    }
    if current_sentence is not None:
        payload['current_sentence'] = current_sentence
    _progress_file().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def _example_voice(sentence: str, default_voice: str) -> str:
    if _provider() != 'minimax':
        return default_voice
    digest = hashlib.md5(sentence.encode('utf-8')).digest()
    return _MINIMAX_EXAMPLE_VOICES[digest[0] % len(_MINIMAX_EXAMPLE_VOICES)]


def _example_cache_path(sentence: str, model: str, voice: str) -> Path:
    key = hashlib.md5(f'ex:{sentence}:{model}:{voice}'.encode('utf-8')).hexdigest()[:16]
    return _cache_dir() / f'{key}.mp3'


def collect_example_sentences(book_ids: list[str] | None) -> list[str]:
    from services.books_catalog_service import load_book_vocabulary
    from services.books_registry_service import VOCAB_BOOKS

    books = VOCAB_BOOKS if book_ids is None else [b for b in VOCAB_BOOKS if b['id'] in book_ids]
    seen: set[str] = set()
    sentences: list[str] = []
    for book in books:
        vocab = load_book_vocabulary(book['id'])
        if not vocab:
            continue
        for entry in vocab:
            examples = entry.get('examples') or []
            if not examples:
                continue
            sentence = (examples[0].get('en') or '').strip()
            if not sentence or sentence in seen:
                continue
            seen.add(sentence)
            sentences.append(sentence)
    return sentences


def main() -> int:
    from services.word_tts import (
        _RequestRateLimiter,
        _is_rate_limit_error,
        default_cache_identity,
        is_probably_valid_mp3_file,
        recommended_batch_backoff_delays,
        recommended_batch_concurrency,
        recommended_batch_rate_interval,
        remove_invalid_cached_audio,
        synthesize_word_to_bytes,
        write_bytes_atomically,
    )

    provider = _provider()
    if not _require_provider_credentials(provider):
        return 1

    model, default_voice = default_cache_identity()
    rate_interval = (
        args.rate_interval
        if args.rate_interval is not None
        else recommended_batch_rate_interval(model)
    )
    backoff = recommended_batch_backoff_delays(rate_interval)
    jobs = recommended_batch_concurrency(model)
    limiter = _RequestRateLimiter(rate_interval)
    book_ids = args.book or None

    sentences = collect_example_sentences(book_ids)
    if args.limit is not None:
        sentences = sentences[:max(0, args.limit)]

    total = len(sentences)
    completed = 0
    pending: list[tuple[str, str, Path]] = []

    for sentence in sentences:
        voice = _example_voice(sentence, default_voice)
        cache_path = _example_cache_path(sentence, model, voice)
        if cache_path.exists() and is_probably_valid_mp3_file(cache_path):
            completed += 1
            continue
        remove_invalid_cached_audio(cache_path)
        pending.append((sentence, voice, cache_path))

    _write_progress(total, completed, 'running', book_ids)

    print(f'[Example TTS] cache_dir={_cache_dir()}')
    print(f'[Example TTS] provider={provider} model={model} voice={default_voice}')
    print(f'[Example TTS] book_ids={book_ids or "ALL"}')
    print(f'[Example TTS] total={total} completed={completed} pending={len(pending)}')
    print(f'[Example TTS] jobs={jobs} rate_interval={rate_interval:.1f}s backoff={backoff}')

    errors: list[str] = []
    completed_lock = threading.Lock()
    progress_every = 5 if rate_interval > 0 else 25

    def process_sentence(sentence: str, voice: str, cache_path: Path) -> tuple[str, bool]:
        text_for_tts = add_pause_tags(sentence, pause_seconds=0.4) if provider == 'minimax' else sentence
        for attempt in range(len(backoff) + 1):
            try:
                limiter.wait_for_turn()
                audio = synthesize_word_to_bytes(
                    text_for_tts,
                    model,
                    voice,
                    provider=provider,
                    content_mode='sentence' if provider == 'azure' else None,
                )
                write_bytes_atomically(cache_path, audio)
                return sentence, True
            except Exception as exc:
                if _is_rate_limit_error(exc) and attempt < len(backoff):
                    delay = backoff[attempt]
                    limiter.cooldown(delay)
                    print(
                        f'[Example TTS 429] backoff {delay}s '
                        f'(attempt {attempt + 1}) sentence={sentence[:60]!r}',
                        flush=True,
                    )
                    time.sleep(delay)
                    continue
                return sentence, False
        return sentence, False

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = {
            executor.submit(process_sentence, sentence, voice, cache_path): sentence
            for sentence, voice, cache_path in pending
        }
        for future in as_completed(futures):
            sentence = futures[future]
            try:
                _, ok = future.result()
            except Exception as exc:
                ok = False
                errors.append(f'{sentence[:120]!r}: {exc}')
                print(f'[Example TTS Error] sentence={sentence[:60]!r}: {exc}', flush=True)
            else:
                if not ok:
                    errors.append(f'{sentence[:120]!r}: generation failed')
                    print(f'[Example TTS Error] sentence={sentence[:60]!r}: generation failed', flush=True)

            with completed_lock:
                if ok:
                    completed += 1
                if completed % progress_every == 0 or completed == total:
                    _write_progress(
                        total,
                        completed,
                        'running',
                        book_ids,
                        current_sentence=sentence,
                    )

    status = 'done' if not errors else 'done_with_errors'
    _write_progress(total, completed, status, book_ids)
    print(f'[Example TTS] finished status={status} completed={completed} errors={len(errors)}')
    return 0 if not errors else 2


if __name__ == '__main__':
    raise SystemExit(main())
