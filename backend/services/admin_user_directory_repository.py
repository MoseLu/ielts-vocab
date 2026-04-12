from __future__ import annotations

from sqlalchemy import desc

from platform_sdk.admin_projection_bootstrap import sync_admin_projected_user_snapshot
from platform_sdk.cross_service_boundary import legacy_cross_service_fallback_enabled
from service_models.admin_ops_models import User, db
from services.admin_projection_repository_support import user_directory_model


def get_user(user_id: int):
    model = user_directory_model()
    user = db.session.get(model, user_id)
    if user is None and model is not User and legacy_cross_service_fallback_enabled():
        return db.session.get(User, user_id)
    return user


def get_writable_user(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def search_users(*, search: str, order: str):
    model = user_directory_model()
    query = model.query
    if search:
        query = query.filter(
            (model.username.ilike(f'%{search}%')) | (model.email.ilike(f'%{search}%'))
        )
    total = query.count()
    users = query.order_by(desc(model.created_at) if order == 'desc' else model.created_at).all()
    return total, users


def set_user_admin(user: User, *, is_admin: bool) -> User:
    user.is_admin = bool(is_admin)
    db.session.add(user)
    sync_admin_projected_user_snapshot(user, session=db.session)
    db.session.commit()
    return user
