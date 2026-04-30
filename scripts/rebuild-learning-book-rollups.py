from __future__ import annotations

import argparse
import json
import os
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Rebuild learning-core book rollups from existing chapter rollups and direct ledgers.',
    )
    parser.add_argument('--user-id', type=int, action='append', help='Rebuild one user; can be repeated.')
    parser.add_argument('--book-id', action='append', help='Rebuild one book; can be repeated.')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    parser.add_argument('--env-file', help='Optional microservices env file.')
    parser.add_argument('--service-name', default='learning-core-service')
    return parser.parse_args()


def _target_scopes(user_ids: list[int] | None, book_ids: list[str] | None):
    from service_models.learning_core_models import (
        UserLearningBookRollup,
        UserLearningChapterRollup,
        db,
    )

    scopes: set[tuple[int, str]] = set()
    for model in (UserLearningBookRollup, UserLearningChapterRollup):
        query = db.session.query(model.user_id, model.book_id)
        if user_ids:
            query = query.filter(model.user_id.in_(user_ids))
        if book_ids:
            query = query.filter(model.book_id.in_(book_ids))
        for user_id, book_id in query.distinct().all():
            if user_id is not None and book_id:
                scopes.add((int(user_id), str(book_id)))
    return sorted(scopes)


def main() -> int:
    args = parse_args()
    if args.env_file:
        os.environ['MICROSERVICES_ENV_FILE'] = str(Path(args.env_file).resolve())
    load_split_service_env(service_name=args.service_name)

    from app import create_app
    from service_models.learning_core_models import UserLearningBookRollup, db
    from services.learning_activity_service import rebuild_learning_activity_rollups

    app = create_app()
    with app.app_context():
        scopes = _target_scopes(args.user_id, args.book_id)
        before = {}
        for user_id, book_id in scopes:
            row = UserLearningBookRollup.query.filter_by(
                user_id=user_id,
                book_id=book_id,
            ).first()
            before[f'{user_id}:{book_id}'] = {
                'current_index': int(row.current_index or 0) if row else 0,
                'words_learned': int(row.words_learned or 0) if row else 0,
                'is_completed': bool(row.is_completed) if row else False,
            }
            rebuild_learning_activity_rollups(user_id=user_id, book_id=book_id)
        db.session.flush()
        after = {}
        changed = 0
        for user_id, book_id in scopes:
            row = UserLearningBookRollup.query.filter_by(
                user_id=user_id,
                book_id=book_id,
            ).first()
            snapshot = {
                'current_index': int(row.current_index or 0) if row else 0,
                'words_learned': int(row.words_learned or 0) if row else 0,
                'is_completed': bool(row.is_completed) if row else False,
            }
            key = f'{user_id}:{book_id}'
            after[key] = snapshot
            changed += int(snapshot != before[key])
        db.session.rollback() if args.dry_run else db.session.commit()

    summary = {
        'scopes': len(scopes),
        'changed': changed,
        'dry_run': bool(args.dry_run),
        'before': before,
        'after': after,
    }
    if args.format == 'json':
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(
            'Rebuilt learning book rollups: '
            f'scopes={len(scopes)} changed={changed} dry_run={args.dry_run}'
        )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
