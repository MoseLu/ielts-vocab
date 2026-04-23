#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.catalog_content_script_runtime import create_catalog_content_script_app
from services.word_detail_llm_client import DISABLE_FALLBACK_PROVIDER
from services.word_memory_note_enrichment import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_RATE_LIMIT_BASE_SLEEP_SECONDS,
    DEFAULT_RATE_LIMIT_MAX_ATTEMPTS,
    DEFAULT_RATE_LIMIT_MAX_SLEEP_SECONDS,
    PREMIUM_BOOK_IDS,
    enrich_premium_book_memory_notes,
)


def _load_words_from_files(paths: list[str]) -> list[str]:
    words: list[str] = []
    for raw_path in paths:
        file_path = Path(raw_path).expanduser()
        if not file_path.is_absolute():
            file_path = (Path.cwd() / file_path).resolve()
        for line in file_path.read_text(encoding='utf-8').splitlines():
            word = line.strip()
            if word:
                words.append(word)
    return words


def _write_summary(path_value: str | None, stats: dict) -> None:
    if not path_value:
        return
    summary_path = Path(path_value).expanduser()
    if not summary_path.is_absolute():
        summary_path = (Path.cwd() / summary_path).resolve()
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


parser = argparse.ArgumentParser(description='批量重跑付费词书联想记忆')
parser.add_argument('--book', action='append', default=[], help='指定词书 id，可重复传入')
parser.add_argument('--word', action='append', default=[], help='只处理指定单词，可重复传入')
parser.add_argument('--words-file', action='append', default=[], help='从文件读取单词列表，每行一个')
parser.add_argument('--summary-file', type=str, default='', help='输出本次执行统计 JSON')
parser.add_argument('--progress-file', type=str, default='', help='批次级实时进度 JSON；默认沿用 summary-file')
parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE, help='每批请求的单词数')
parser.add_argument('--limit', type=int, default=None, help='仅处理前 N 个去重词')
parser.add_argument('--start-at', type=int, default=0, help='从第 N 个去重词开始')
parser.add_argument('--sleep', type=float, default=1.0, help='批次间隔秒数')
parser.add_argument('--overwrite', action='store_true', help='覆盖已有联想记忆')
parser.add_argument('--no-fallback', action='store_true', help='禁用 provider 自动回退')
parser.add_argument('--provider', type=str, default='dashscope', help='LLM provider')
parser.add_argument('--model', type=str, default='qwen3.6-plus', help='主模型，支持逗号分隔优先级链')
parser.add_argument('--fallback-provider', type=str, default='', help='失败时切换的备用 provider')
parser.add_argument('--fallback-model', type=str, default='', help='失败时切换的备用模型')
parser.add_argument(
    '--rate-limit-max-attempts',
    type=int,
    default=DEFAULT_RATE_LIMIT_MAX_ATTEMPTS,
    help='429/529 限速时的最大重试次数；0 表示一直重试',
)
parser.add_argument(
    '--rate-limit-base-sleep',
    type=float,
    default=DEFAULT_RATE_LIMIT_BASE_SLEEP_SECONDS,
    help='429/529 首次退避秒数',
)
parser.add_argument(
    '--rate-limit-max-sleep',
    type=float,
    default=DEFAULT_RATE_LIMIT_MAX_SLEEP_SECONDS,
    help='429/529 单次最大退避秒数',
)
args = parser.parse_args()


def main() -> int:
    selected_words = [*args.word, *_load_words_from_files(args.words_file)]
    fallback_provider = (
        DISABLE_FALLBACK_PROVIDER
        if args.no_fallback
        else (args.fallback_provider or None)
    )
    fallback_model = None if args.no_fallback else (args.fallback_model or None)
    progress_path = args.progress_file or args.summary_file or ''
    job_meta = {
        'started_at': _utc_now_iso(),
        'book_ids': list(tuple(args.book) if args.book else PREMIUM_BOOK_IDS),
        'provider': args.provider,
        'model': args.model or '',
        'batch_size': max(1, args.batch_size),
        'limit': args.limit,
        'start_at': max(0, args.start_at),
        'overwrite': bool(args.overwrite),
        'progress_state': 'running',
    }

    def write_progress(stats: dict) -> None:
        payload = {
            **job_meta,
            **stats,
            'updated_at': _utc_now_iso(),
        }
        _write_summary(progress_path or None, payload)

    write_progress({
        'requested': 0,
        'pending': 0,
        'enriched': 0,
        'failed': 0,
        'failed_words': [],
        'failure_details': [],
        'quota_exhausted': False,
        'stop_reason': '',
        'rate_limit_retries': 0,
        'rate_limit_wait_seconds': 0.0,
        'total_batches': 0,
        'completed_batches': 0,
        'word_count': 0,
    })

    app = create_catalog_content_script_app()
    with app.app_context():
        stats = enrich_premium_book_memory_notes(
            book_ids=tuple(args.book) if args.book else PREMIUM_BOOK_IDS,
            words=selected_words or None,
            batch_size=max(1, args.batch_size),
            limit=args.limit,
            overwrite=bool(args.overwrite),
            sleep_seconds=max(0.0, args.sleep),
            start_at=max(0, args.start_at),
            provider=args.provider,
            model=args.model or None,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            rate_limit_max_attempts=max(0, args.rate_limit_max_attempts),
            rate_limit_base_sleep_seconds=max(1.0, args.rate_limit_base_sleep),
            rate_limit_max_sleep_seconds=max(
                max(1.0, args.rate_limit_base_sleep),
                args.rate_limit_max_sleep,
            ),
            progress_callback=write_progress,
        )

    final_payload = {
        **job_meta,
        **stats,
        'updated_at': _utc_now_iso(),
        'progress_state': 'completed',
    }
    _write_summary(progress_path or None, final_payload)
    if args.summary_file and args.summary_file != progress_path:
        _write_summary(args.summary_file, final_payload)
    print('[Word Memory Enrichment] done')
    print(f"books={','.join(stats['book_ids'])}")
    print(f"provider={stats['provider']} model={stats['model']}")
    print(f"requested={stats['requested']} pending={stats['pending']}")
    print(f"enriched={stats['enriched']} failed={stats['failed']}")
    print(f"word_count={stats['word_count']}")
    if stats.get('quota_exhausted'):
        print(f"quota_exhausted=1 reason={stats.get('stop_reason') or ''}")
    return 0 if stats['failed'] == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
