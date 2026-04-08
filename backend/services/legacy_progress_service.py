from services import legacy_progress_repository


def list_legacy_progress(user_id: int) -> list[dict]:
    progress_rows = legacy_progress_repository.list_user_progress_rows(user_id)
    return [row.to_dict() for row in progress_rows]


def save_legacy_progress(user_id: int, payload: dict | None) -> dict:
    data = payload or {}
    day = data.get('day')
    if not day:
        raise ValueError('Day is required')

    current_index = data.get('current_index', 0)
    correct_count = data.get('correct_count', 0)
    wrong_count = data.get('wrong_count', 0)

    progress = legacy_progress_repository.get_user_progress(user_id, day)
    if progress:
        progress.current_index = current_index
        progress.correct_count = correct_count
        progress.wrong_count = wrong_count
    else:
        progress = legacy_progress_repository.create_user_progress(
            user_id,
            day=day,
            current_index=current_index,
            correct_count=correct_count,
            wrong_count=wrong_count,
        )

    legacy_progress_repository.commit()
    return progress.to_dict()


def get_legacy_progress_for_day(user_id: int, day: int) -> dict | None:
    progress = legacy_progress_repository.get_user_progress(user_id, day)
    if not progress:
        return None
    return progress.to_dict()
