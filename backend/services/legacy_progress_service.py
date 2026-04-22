from __future__ import annotations

from service_models.learning_core_models import db
from services.legacy_day_progress_compat import (
    get_legacy_day_progress,
    list_legacy_day_progress_rows,
    save_legacy_day_progress,
)


def list_legacy_progress(user_id: int) -> list[dict]:
    progress_rows = list_legacy_day_progress_rows(user_id)
    return [row.to_dict() for row in progress_rows]


def save_legacy_progress(user_id: int, payload: dict | None) -> dict:
    data = payload or {}
    day = data.get('day')
    if not day:
        raise ValueError('Day is required')

    progress = save_legacy_day_progress(
        user_id,
        day=day,
        current_index=data.get('current_index', 0),
        correct_count=data.get('correct_count', 0),
        wrong_count=data.get('wrong_count', 0),
    )
    db.session.commit()
    return progress.to_dict()


def get_legacy_progress_for_day(user_id: int, day: int) -> dict | None:
    progress = get_legacy_day_progress(user_id, day)
    if progress is None:
        return None
    return progress.to_dict()
