#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
for path in (BACKEND_PATH, SDK_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from platform_sdk.runtime_env import load_split_service_env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Ensure the local Mac app admin user exists.')
    parser.add_argument('--username', default='admin')
    parser.add_argument('--password', default='admin123456')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_split_service_env(service_name='identity-service')
    from platform_sdk.identity_runtime import create_identity_flask_app
    from service_models.identity_models import User, db

    app = create_identity_flask_app()

    with app.app_context():
        user = User.query.filter_by(username=args.username).first()
        if user is None:
            user = User(username=args.username, email=None, is_admin=True)
            db.session.add(user)
        user.is_admin = True
        user.set_password(args.password)
        db.session.commit()

    print(f"[mac-local-app] ensured local admin user '{args.username}'")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
