from __future__ import annotations

from service_models.learning_core_models import db
from services.legacy_day_progress_compat import (
    get_legacy_day_progress,
    list_legacy_day_progress_rows,
    save_legacy_day_progress,
)


def list_user_progress_rows(user_id: int):
    return list_legacy_day_progress_rows(user_id)


def get_user_progress(user_id: int, day: int):
    return get_legacy_day_progress(user_id, day)


def create_user_progress(
    user_id: int,
    *,
    day: int,
    current_index: int,
    correct_count: int,
    wrong_count: int,
):
    return save_legacy_day_progress(
        user_id,
        day=day,
        current_index=current_index,
        correct_count=correct_count,
        wrong_count=wrong_count,
    )


def commit() -> None:
    db.session.commit()
