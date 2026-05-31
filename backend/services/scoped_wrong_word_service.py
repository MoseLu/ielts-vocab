from __future__ import annotations

from services import scoped_wrong_word_repository
from services.learning_scope_support import LearningScope


def get_or_create_scoped_wrong_word_record(
    user_id: int,
    word_value: str,
    payload: dict,
    *,
    scope: LearningScope,
    record_cache: dict[str, object],
):
    cached = record_cache.get(word_value)
    if cached is not None:
        return cached

    existing = scoped_wrong_word_repository.get_user_scoped_wrong_word(
        user_id,
        scope_key=scope.scope_key,
        word=word_value,
    )
    if existing is None:
        existing = scoped_wrong_word_repository.create_user_scoped_wrong_word(
            user_id,
            word_value,
            scope=scope,
            phonetic=payload.get('phonetic'),
            pos=payload.get('pos'),
            definition=payload.get('definition'),
        )

    record_cache[word_value] = existing
    return existing
