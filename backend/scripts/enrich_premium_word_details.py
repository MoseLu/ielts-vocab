#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

load_dotenv(BACKEND_ROOT / '.env')

from app import create_app
from services.word_detail_enrichment import (
    DEFAULT_BATCH_SIZE,
    enrich_premium_books,
)
from services.word_detail_llm_client import DISABLE_FALLBACK_PROVIDER


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


parser = argparse.ArgumentParser(description='批量补全付费词书单词详情')
parser.add_argument('--book', action='append', default=[], help='指定词书 id，可重复传入')
parser.add_argument('--word', action='append', default=[], help='只补指定单词，可重复传入')
parser.add_argument('--words-file', action='append', default=[], help='从文件读取单词列表，每行一个')
parser.add_argument('--batch-size', type=int, default=DEFAULT_BATCH_SIZE, help='每批请求的单词数')
parser.add_argument('--limit', type=int, default=None, help='仅处理前 N 个词')
parser.add_argument('--start-at', type=int, default=0, help='从第 N 个去重词开始')
parser.add_argument('--sleep', type=float, default=0.2, help='批次间隔秒数')
parser.add_argument('--overwrite', action='store_true', help='覆盖已有详情')
parser.add_argument('--no-fallback', action='store_true', help='禁用 provider 自动回退')
parser.add_argument('--provider', type=str, default='minimax', help='LLM provider: minimax 或 dashscope')
parser.add_argument('--model', type=str, default='', help='指定主模型，例如 qwen-plus-2025-07-28')
parser.add_argument('--fallback-provider', type=str, default='', help='失败时切换的备用 provider')
parser.add_argument('--fallback-model', type=str, default='', help='失败时切换的备用模型')
args = parser.parse_args()


def main() -> int:
    selected_words = [*args.word, *_load_words_from_files(args.words_file)]
    fallback_provider = (
        DISABLE_FALLBACK_PROVIDER
        if args.no_fallback
        else (args.fallback_provider or None)
    )
    fallback_model = None if args.no_fallback else (args.fallback_model or None)

    app = create_app()
    with app.app_context():
        stats = enrich_premium_books(
            book_ids=tuple(args.book) if args.book else (
                'ielts_listening_premium',
                'ielts_reading_premium',
            ),
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
        )

    print('[Word Detail Enrichment] done')
    print(f"books={','.join(stats['book_ids'])}")
    print(f"provider={stats['provider']} model={stats['model']}")
    print(f"requested={stats['requested']} pending={stats['pending']}")
    print(f"enriched={stats['enriched']} failed={stats['failed']}")
    print(f"word_count={stats['word_count']}")
    return 0 if stats['failed'] == 0 else 2


if __name__ == '__main__':
    raise SystemExit(main())
