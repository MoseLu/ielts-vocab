from __future__ import annotations

from datetime import datetime, timedelta

from models import UserBookProgress, UserChapterProgress, UserLearningEvent, UserWrongWord


def list_user_book_progress_rows(user_id: int):
    return UserBookProgress.query.filter_by(user_id=user_id).all()


def list_user_chapter_progress_rows(
    user_id: int,
    *,
    book_id: str | None = None,
    limit: int | None = None,
):
    query = UserChapterProgress.query.filter_by(user_id=user_id)
    if book_id:
        query = query.filter_by(book_id=book_id)
    query = query.order_by(UserChapterProgress.updated_at.desc())
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def list_user_wrong_word_rows(user_id: int):
    return UserWrongWord.query.filter_by(user_id=user_id).all()


def count_user_wrong_words(user_id: int) -> int:
    return UserWrongWord.query.filter_by(user_id=user_id).count()


def list_learning_events_for_sessions(
    user_id: int,
    *,
    lower_bound: datetime,
    upper_bound: datetime,
):
    return (
        UserLearningEvent.query
        .filter(
            UserLearningEvent.user_id == user_id,
            UserLearningEvent.word.isnot(None),
            UserLearningEvent.event_type.in_(('quick_memory_review', 'wrong_word_recorded')),
            UserLearningEvent.occurred_at >= lower_bound - timedelta(seconds=5),
            UserLearningEvent.occurred_at <= upper_bound + timedelta(seconds=5),
        )
        .order_by(UserLearningEvent.occurred_at.asc(), UserLearningEvent.id.asc())
        .all()
    )
