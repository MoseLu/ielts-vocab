from __future__ import annotations

from service_models.learning_core_models import (
    User,
    UserQuickMemoryRecord,
    UserScopedWrongWord,
    UserWrongWord,
    db,
)
from services.learning_scope_support import resolve_learning_scope
from services.scoped_quick_memory_service import upsert_scoped_quick_memory_record
from services.scoped_wrong_word_service import get_or_create_scoped_wrong_word_record


def _target_user_ids(user_ids: list[int] | None) -> list[int]:
    if user_ids:
        return sorted({int(user_id) for user_id in user_ids})
    return [row.id for row in User.query.order_by(User.id).all()]


def _copy_wrong_word_fields(source: UserWrongWord, target: UserScopedWrongWord) -> None:
    target.phonetic = source.phonetic
    target.pos = source.pos
    target.definition = source.definition
    target.wrong_count = source.wrong_count or 0
    target.listening_correct = source.listening_correct or 0
    target.listening_wrong = source.listening_wrong or 0
    target.meaning_correct = source.meaning_correct or 0
    target.meaning_wrong = source.meaning_wrong or 0
    target.dictation_correct = source.dictation_correct or 0
    target.dictation_wrong = source.dictation_wrong or 0
    target.dimension_state = source.dimension_state
    target.updated_at = source.updated_at


def backfill_scoped_learning_state(user_ids: list[int] | None = None, *, commit: bool = True) -> dict:
    target_user_ids = _target_user_ids(user_ids)
    summary = {
        'users': len(target_user_ids),
        'quick_memory_rows': 0,
        'wrong_word_rows': 0,
        'scoped_quick_memory_upserts': 0,
        'scoped_wrong_word_upserts': 0,
        'committed': bool(commit),
    }
    for row in UserQuickMemoryRecord.query.filter(UserQuickMemoryRecord.user_id.in_(target_user_ids)).all():
        scope = resolve_learning_scope(book_id=row.book_id, chapter_id=row.chapter_id)
        upsert_scoped_quick_memory_record(
            user_id=row.user_id,
            word=str(row.word or '').strip().lower(),
            scope=scope,
            record_payload={
                'status': row.status,
                'firstSeen': row.first_seen,
                'unknownCount': row.unknown_count,
                'fuzzyCount': row.fuzzy_count,
            },
            record_last_seen=row.last_seen or 0,
            record_known_count=row.known_count or 0,
            canonical_next_review=row.next_review or 0,
        )
        summary['quick_memory_rows'] += 1
        summary['scoped_quick_memory_upserts'] += 1
    for row in UserWrongWord.query.filter(UserWrongWord.user_id.in_(target_user_ids)).all():
        word = str(row.word or '').strip()
        if not word:
            continue
        scope = resolve_learning_scope()
        scoped = get_or_create_scoped_wrong_word_record(
            row.user_id,
            word,
            row.to_dict(),
            scope=scope,
            record_cache={},
        )
        _copy_wrong_word_fields(row, scoped)
        summary['wrong_word_rows'] += 1
        summary['scoped_wrong_word_upserts'] += 1
    if commit:
        db.session.commit()
    else:
        db.session.rollback()
    return summary
