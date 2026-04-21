#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.catalog_content_script_runtime import create_catalog_content_script_app
from services.legacy_word_detail_migration import migrate_legacy_word_details


parser = argparse.ArgumentParser(description='迁移旧单词详情表到全局词条主表')
parser.add_argument('--word', action='append', default=[], help='只迁移指定单词，可重复传入')
parser.add_argument('--limit', type=int, default=None, help='仅迁移前 N 个词')
parser.add_argument('--start-at', type=int, default=0, help='从第 N 个词开始')
parser.add_argument('--overwrite', action='store_true', help='覆盖主表已有字段')
args = parser.parse_args()


def main() -> int:
    app = create_catalog_content_script_app()
    with app.app_context():
        stats = migrate_legacy_word_details(
            words=args.word or None,
            limit=args.limit,
            start_at=max(0, args.start_at),
            overwrite=bool(args.overwrite),
        )

    print('[Legacy Word Detail Migration] done')
    print(f"total={stats['total']}")
    print(f"migrated={stats['migrated']}")
    print(f"skipped={stats['skipped']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
