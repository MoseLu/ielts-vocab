#!/usr/bin/env python3
"""
CLI: 顺序生成词书单词音频，然后继续生成例句音频。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(BACKEND_ROOT / '.env')


parser = argparse.ArgumentParser(description='词书音频顺序预热管道')
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
args = parser.parse_args()


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


def main() -> int:
    provider = _provider()
    if not _require_provider_credentials(provider):
        return 1

    from services.word_tts import (
        _strip_word_tts_strategy_tag,
        default_word_tts_identity,
        recommended_batch_backoff_delays,
        recommended_batch_concurrency,
        recommended_batch_rate_interval,
        run_batch_generate_missing,
        word_tts_data_dir,
    )

    book_ids = args.book or None
    _, cache_model, voice = default_word_tts_identity()
    model = _strip_word_tts_strategy_tag(cache_model)
    rate_interval = (
        args.rate_interval
        if args.rate_interval is not None
        else recommended_batch_rate_interval(model, provider=provider)
    )
    backoff = recommended_batch_backoff_delays(rate_interval)
    jobs = recommended_batch_concurrency(model, provider=provider)

    print(f'[Audio Pipeline] provider={provider} model={model} voice={voice}')
    print(f'[Audio Pipeline] book_ids={book_ids or "ALL"}')
    print(f'[Audio Pipeline] word-stage jobs={jobs} rate_interval={rate_interval:.1f}s')

    word_stats = run_batch_generate_missing(
        book_ids,
        cache_dir=word_tts_data_dir(),
        concurrency=jobs,
        backoff_delays=backoff,
        rate_interval=rate_interval,
    )
    print(f'[Audio Pipeline] word stage done: {word_stats}')
    if word_stats.get('errors'):
        return 2

    cmd = [sys.executable, '-u', str(Path(__file__).with_name('run_example_tts_full_batch.py'))]
    for book_id in args.book:
        cmd.extend(['--book', book_id])
    if args.rate_interval is not None:
        cmd.extend(['--rate-interval', str(args.rate_interval)])

    print(f'[Audio Pipeline] starting example stage: {cmd}')
    result = subprocess.run(cmd, cwd=BACKEND_ROOT, check=False)
    print(f'[Audio Pipeline] example stage exited: {result.returncode}')
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
