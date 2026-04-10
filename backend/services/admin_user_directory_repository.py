from __future__ import annotations

from sqlalchemy import desc

from service_models.admin_ops_models import User, db


def get_user(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def search_users(*, search: str, order: str):
    query = User.query
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) | (User.email.ilike(f'%{search}%'))
        )
    total = query.count()
    users = query.order_by(desc(User.created_at) if order == 'desc' else User.created_at).all()
    return total, users


def set_user_admin(user: User, *, is_admin: bool) -> User:
    user.is_admin = bool(is_admin)
    db.session.commit()
    return user
