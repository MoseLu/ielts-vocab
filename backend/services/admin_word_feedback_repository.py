from __future__ import annotations

import json

from service_models.admin_ops_models import AdminWordFeedback, db


def create_word_feedback(
    *,
    user_id: int,
    username: str,
    email: str | None,
    word: str,
    normalized_word: str,
    phonetic: str,
    pos: str,
    definition: str,
    example_en: str,
    example_zh: str,
    source_book_id: str | None,
    source_book_title: str | None,
    source_chapter_id: str | None,
    source_chapter_title: str | None,
    feedback_types: list[str],
    source: str,
    comment: str,
) -> AdminWordFeedback:
    record = AdminWordFeedback(
        user_id=user_id,
        username_snapshot=username,
        email_snapshot=email,
        word=word,
        normalized_word=normalized_word,
        phonetic=phonetic,
        pos=pos,
        definition=definition,
        example_en=example_en,
        example_zh=example_zh,
        source_book_id=source_book_id,
        source_book_title=source_book_title,
        source_chapter_id=source_chapter_id,
        source_chapter_title=source_chapter_title,
        feedback_types_json=json.dumps(feedback_types, ensure_ascii=False),
        source=source,
        comment=comment,
    )
    db.session.add(record)
    db.session.commit()
    return record


def count_word_feedback_rows() -> int:
    return AdminWordFeedback.query.count()


def list_recent_word_feedback_rows(*, limit: int = 50):
    return (
        AdminWordFeedback.query
        .order_by(AdminWordFeedback.created_at.desc(), AdminWordFeedback.id.desc())
        .limit(limit)
        .all()
    )
