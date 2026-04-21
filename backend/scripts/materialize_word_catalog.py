#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.catalog_content_script_runtime import create_catalog_content_script_app
from services.word_catalog_service import materialize_word_catalog


parser = argparse.ArgumentParser(description='将现有词书数据落到全局词条主表')
parser.add_argument('--book', action='append', default=[], help='仅 materialize 指定词书 id')
parser.add_argument('--limit', type=int, default=None, help='仅处理前 N 个词')
parser.add_argument('--start-at', type=int, default=0, help='从第 N 个词开始')
args = parser.parse_args()


def main() -> int:
    app = create_catalog_content_script_app()
    with app.app_context():
        stats = materialize_word_catalog(
            book_ids=tuple(args.book) if args.book else None,
            limit=args.limit,
            start_at=max(0, args.start_at),
        )

    print('[Word Catalog Materialize] done')
    print(f"total={stats['total']}")
    print(f"created={stats['created']}")
    print(f"updated={stats['updated']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
