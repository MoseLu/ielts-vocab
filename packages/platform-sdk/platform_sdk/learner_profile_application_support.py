from __future__ import annotations

from platform_sdk.learner_profile_builder_adapter import build_learner_profile


def build_learner_profile_payload(
    user_id: int,
    *,
    target_date: str | None = None,
    view: str = 'full',
) -> dict:
    return build_learner_profile(user_id, target_date, view)


def build_learner_profile_response(
    user_id: int,
    *,
    target_date: str | None,
    view: str,
) -> tuple[dict, int]:
    try:
        return build_learner_profile_payload(
            user_id,
            target_date=target_date,
            view=view,
        ), 200
    except ValueError:
        return {'error': 'date must be YYYY-MM-DD'}, 400


__all__ = [
    'build_learner_profile_payload',
    'build_learner_profile_response',
]
