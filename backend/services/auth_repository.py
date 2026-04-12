from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError

from platform_sdk.admin_projection_bootstrap import sync_admin_projected_user_snapshot
from platform_sdk.identity_event_application import queue_user_registered_event
from platform_sdk.identity_rate_limit_runtime import (
    check_rate_limit_with_redis,
    reset_rate_limit_with_redis,
)
from service_models.identity_models import EmailVerificationCode, RateLimitBucket, RevokedToken, User, db


def get_user(user_id: int | None) -> User | None:
    if user_id is None:
        return None
    return db.session.get(User, user_id)


def get_user_by_email(email: str):
    return User.query.filter_by(email=email).first()


def get_user_by_username(username: str):
    return User.query.filter_by(username=username).first()


def find_user_by_identifier(identifier: str):
    if '@' in identifier:
        return get_user_by_email(identifier)
    user = get_user_by_username(identifier)
    if user is None:
        user = get_user_by_email(identifier)
    return user


def create_user(*, username: str, email: str | None, password: str):
    user = User(email=email or None, username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    queue_user_registered_event(user, session=db.session)
    db.session.commit()
    return user


def commit_user(user) -> None:
    db.session.add(user)
    sync_admin_projected_user_snapshot(user, session=db.session)
    db.session.commit()


def check_rate_limit(
    *,
    ip_address: str,
    purpose: str,
    max_attempts: int,
    window_minutes: int,
) -> tuple[bool, int]:
    redis_result = check_rate_limit_with_redis(
        ip_address=ip_address,
        purpose=purpose,
        max_attempts=max_attempts,
        window_minutes=window_minutes,
    )
    if redis_result is not None:
        return redis_result

    try:
        return RateLimitBucket.check_and_increment(
            ip_address=ip_address,
            purpose=purpose,
            max_attempts=max_attempts,
            window_minutes=window_minutes,
        )
    except IntegrityError:
        # Another request won the insert race for the same (ip, purpose) bucket.
        db.session.rollback()
        return RateLimitBucket.check_and_increment(
            ip_address=ip_address,
            purpose=purpose,
            max_attempts=max_attempts,
            window_minutes=window_minutes,
        )


def reset_rate_limit(*, ip_address: str, purpose: str) -> None:
    if reset_rate_limit_with_redis(
        ip_address=ip_address,
        purpose=purpose,
    ):
        return

    RateLimitBucket.reset(
        ip_address=ip_address,
        purpose=purpose,
    )


def latest_unused_verification_code(
    email: str,
    purpose: str,
    *,
    user_id: int | None = None,
) -> EmailVerificationCode | None:
    query = EmailVerificationCode.query.filter_by(
        email=email,
        purpose=purpose,
        used=False,
    )
    if user_id is not None:
        query = query.filter_by(user_id=user_id)
    return query.order_by(EmailVerificationCode.created_at.desc()).first()


def mark_verification_codes_used(
    *,
    purpose: str,
    email: str | None = None,
    user_id: int | None = None,
) -> None:
    query = EmailVerificationCode.query.filter_by(
        purpose=purpose,
        used=False,
    )
    if email is not None:
        query = query.filter_by(email=email)
    if user_id is not None:
        query = query.filter_by(user_id=user_id)
    query.update({'used': True})
    db.session.commit()


def create_verification_code(
    email: str,
    purpose: str,
    *,
    user_id: int | None = None,
    expires_minutes: int = 10,
) -> EmailVerificationCode:
    return EmailVerificationCode.create_for(
        email,
        purpose,
        user_id=user_id,
        expires_minutes=expires_minutes,
    )


def revoke_token(jti: str, *, expires_at: datetime) -> None:
    RevokedToken.revoke(jti, expires_at)


def is_token_revoked(jti: str) -> bool:
    return RevokedToken.is_revoked(jti)


def prune_expired_revoked_tokens() -> None:
    RevokedToken.prune_expired()
