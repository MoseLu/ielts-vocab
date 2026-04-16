from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from platform_sdk.runtime_env import load_split_service_env


load_split_service_env(service_name='ai-execution-service')

from platform_sdk.ai_runtime import create_ai_flask_app
from platform_sdk.ai_word_image_application import (
    DEFAULT_GAME_WORD_IMAGE_BOOK_IDS,
    queue_game_word_images_for_books,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Queue five-dimensional game word-image assets for premium IELTS books.',
    )
    parser.add_argument(
        '--book-ids',
        nargs='+',
        default=list(DEFAULT_GAME_WORD_IMAGE_BOOK_IDS),
        help='Limit the queue to one or more vocabulary books.',
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='Stop after processing N unique sense candidates. 0 means no limit.',
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Skip non-ready assets that are already present instead of re-queueing them.',
    )
    parser.add_argument(
        '--format',
        choices=('text', 'json'),
        default='text',
        help='Choose the output format.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    app = create_ai_flask_app()
    with app.app_context():
        summary = queue_game_word_images_for_books(
            book_ids=args.book_ids,
            limit=max(0, int(args.limit or 0)),
            resume=bool(args.resume),
        )

    if args.format == 'json':
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            'Queued game word images: '
            f'seen={summary["seen_candidates"]} '
            f'queued={summary["queued"]} '
            f'skipped_ready={summary["skipped_ready"]} '
            f'skipped_existing={summary["skipped_existing"]} '
            f'updated_existing={summary["updated_existing"]}'
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
