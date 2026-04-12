from __future__ import annotations

from datetime import datetime

import pytest

from models import AdminProjectedUser, AdminProjectionCursor, User, db
from platform_sdk.admin_projection_bootstrap import bootstrap_projection_marker_name
from platform_sdk.admin_user_projection_application import USER_DIRECTORY_PROJECTION
from services import admin_user_directory_repository
from services.admin_projection_repository_support import AdminProjectionUnavailable


def test_strict_admin_directory_requires_projection_bootstrap(monkeypatch, app):
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'admin-ops-service')
    monkeypatch.delenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', raising=False)

    with app.app_context():
        with pytest.raises(AdminProjectionUnavailable) as exc_info:
            admin_user_directory_repository.search_users(search='', order='desc')

    assert exc_info.value.action == 'admin-user-directory'


def test_strict_admin_directory_does_not_fallback_to_shared_user(monkeypatch, app):
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'admin-ops-service')
    monkeypatch.delenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', raising=False)

    with app.app_context():
        shared_only_user = User(username='shared-only-strict', email='shared-only-strict@example.com')
        shared_only_user.set_password('password123')
        projected_user = AdminProjectedUser(
            id=202,
            username='projected-strict',
            email='projected-strict@example.com',
            avatar_url=None,
            is_admin=False,
            created_at=datetime.utcnow(),
        )
        marker = AdminProjectionCursor(
            projection_name=bootstrap_projection_marker_name(USER_DIRECTORY_PROJECTION),
            last_event_id='bootstrap:admin.user-directory:strict',
            last_topic='__bootstrap__',
            last_processed_at=datetime.utcnow(),
        )
        db.session.add_all([shared_only_user, projected_user, marker])
        db.session.commit()

        total, users = admin_user_directory_repository.search_users(search='strict', order='desc')
        shared_result = admin_user_directory_repository.get_user(shared_only_user.id)
        projected_result = admin_user_directory_repository.get_user(projected_user.id)

    assert total == 1
    assert [user.username for user in users] == ['projected-strict']
    assert shared_result is None
    assert projected_result is not None
    assert projected_result.__class__.__name__ == 'AdminProjectedUser'
