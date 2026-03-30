#!/usr/bin/env python3
"""
CLI: 全量生成词书单词百炼 TTS — 支持多线程并发加速（不触发 429 限流）

用法:
  python scripts/run_word_tts_full_batch.py              # 默认并发=5
  python scripts/run_word_tts_full_batch.py --jobs 8   # 并发=8

环境变量 (backend/.env):
  DASHSCOPE_API_KEY      (必需)
  BAILIAN_TTS_MODEL      (默认 cosyvoice-v3-flash)
  BAILIAN_TTS_VOICE     (默认 longanyang)
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(BACKEND_ROOT / '.env')


# ── 参数解析 ──────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description='百炼 TTS 全量并发生成')
parser.add_argument(
    '--jobs', '-j', type=int, default=16,
    help='并发线程数 (default: 16)',
)
args = parser.parse_args()


# ── 核心逻辑（可在函数内调用，也直接执行）────────────────────────────────────────

def main() -> int:
    if not os.environ.get('DASHSCOPE_API_KEY', '').strip():
        print('ERROR: 请在 backend/.env 中设置 DASHSCOPE_API_KEY', file=sys.stderr)
        return 1

    from services.word_tts import (
        run_batch_generate_missing,
        word_tts_data_dir,
    )

    cache_dir = word_tts_data_dir()
    print(f'[Word TTS] cache_dir={cache_dir}')
    print(f'[Word TTS] 并发数={args.jobs}  (HTTP REST API, 多模型轮询无429)')

    # 429 退避重试间隔（秒）- 降为快速退避，减少 worker 阻塞
    backoff = (2.0, 4.0, 8.0)

    stats = run_batch_generate_missing(
        None,
        cache_dir=cache_dir,
        concurrency=args.jobs,
        backoff_delays=backoff,
    )
    print('[Word TTS] 完成:', stats)
    return 0 if not stats.get('errors') else 2


if __name__ == '__main__':
    raise SystemExit(main())
