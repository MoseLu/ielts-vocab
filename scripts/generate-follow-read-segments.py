from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = REPO_ROOT / 'backend'
for candidate in (SCRIPT_DIR, BACKEND_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from services.follow_read_segments_service import (
    build_follow_read_sidecar,
    supported_follow_read_book_ids,
    write_follow_read_sidecar,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Generate phonetic-driven follow-read segment sidecars for premium vocabulary books.',
    )
    parser.add_argument(
        '--books',
        nargs='*',
        default=list(supported_follow_read_book_ids()),
        help='Premium book IDs to generate. Defaults to all supported premium books.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    supported = set(supported_follow_read_book_ids())
    book_ids = [book_id for book_id in args.books if book_id in supported]
    if not book_ids:
        raise RuntimeError('No supported premium book IDs were provided.')

    print('Generating follow-read sidecars...')
    for book_id in book_ids:
        payload = build_follow_read_sidecar(book_id)
        path = write_follow_read_sidecar(book_id)
        print(json.dumps({
            'book_id': book_id,
            'entry_count': payload['entry_count'],
            'path': str(path),
        }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
