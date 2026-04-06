#!/usr/bin/env python3
"""
CLI: 批量生成词书单词百炼 TTS。

用法:
  python scripts/run_word_tts_full_batch.py
  python scripts/run_word_tts_full_batch.py --book ielts_listening_premium --book ielts_reading_premium
  python scripts/run_word_tts_full_batch.py --rate-interval 7

环境变量 (backend/.env):
  DASHSCOPE_API_KEY    (必需)
  BAILIAN_TTS_MODEL    (默认 cosyvoice-v3-flash)
  BAILIAN_TTS_VOICE    (默认 longanyang)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(BACKEND_ROOT / '.env')


# ── 参数解析 ──────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description='百炼 TTS 全量并发生成')
parser.add_argument(
    '--jobs', '-j', type=int, default=None,
    help='并发线程数；未指定时会按模型限速策略自动选择',
)
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


# ── 核心逻辑（可在函数内调用，也直接执行）────────────────────────────────────────

def main() -> int:
    if not os.environ.get('DASHSCOPE_API_KEY', '').strip():
        print('ERROR: 请在 backend/.env 中设置 DASHSCOPE_API_KEY', file=sys.stderr)
        return 1

    from services.word_tts import (
        default_cache_identity,
        recommended_batch_backoff_delays,
        recommended_batch_concurrency,
        recommended_batch_rate_interval,
        run_batch_generate_missing,
        word_tts_data_dir,
    )

    cache_dir = word_tts_data_dir()
    model, voice = default_cache_identity()
    rate_interval = (
        args.rate_interval
        if args.rate_interval is not None
        else recommended_batch_rate_interval(model)
    )
    jobs = args.jobs if args.jobs is not None else recommended_batch_concurrency(model)
    book_ids = args.book or None
    backoff = recommended_batch_backoff_delays(rate_interval)

    print(f'[Word TTS] cache_dir={cache_dir}')
    print(f'[Word TTS] model={model} voice={voice}')
    print(f'[Word TTS] book_ids={book_ids or "ALL"}')
    print(f'[Word TTS] jobs={jobs} rate_interval={rate_interval:.1f}s backoff={backoff}')

    stats = run_batch_generate_missing(
        book_ids,
        cache_dir=cache_dir,
        concurrency=jobs,
        backoff_delays=backoff,
        rate_interval=rate_interval,
    )
    print('[Word TTS] 完成:', stats)
    return 0 if not stats.get('errors') else 2


if __name__ == '__main__':
    raise SystemExit(main())
