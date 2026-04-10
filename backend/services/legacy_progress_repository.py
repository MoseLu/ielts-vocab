from __future__ import annotations

from service_models.learning_core_models import UserProgress, db


def list_user_progress_rows(user_id: int):
    return UserProgress.query.filter_by(user_id=user_id).all()


def get_user_progress(user_id: int, day: int):
    return UserProgress.query.filter_by(user_id=user_id, day=day).first()


def create_user_progress(
    user_id: int,
    *,
    day: int,
    current_index: int,
    correct_count: int,
    wrong_count: int,
):
    progress = UserProgress(
        user_id=user_id,
        day=day,
        current_index=current_index,
        correct_count=correct_count,
        wrong_count=wrong_count,
    )
    db.session.add(progress)
    return progress


def commit() -> None:
    db.session.commit()
