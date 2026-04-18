from __future__ import annotations

import logging

from service_models.catalog_content_models import CustomBook, CustomBookChapter, CustomBookWord, db


_CUSTOM_BOOK_SCHEMA_DRIFT_MARKERS = (
    'column custom_books.education_stage does not exist',
    'column custom_books.exam_type does not exist',
    'column custom_books.ielts_skill does not exist',
    'column custom_books.share_enabled does not exist',
    'column custom_books.chapter_word_target does not exist',
    'column custom_book_words.is_incomplete does not exist',
    'no such column: custom_books.education_stage',
    'no such column: custom_books.exam_type',
    'no such column: custom_books.ielts_skill',
    'no such column: custom_books.share_enabled',
    'no such column: custom_books.chapter_word_target',
    'no such column: custom_book_words.is_incomplete',
)


def _is_custom_book_schema_drift_error(exc: Exception) -> bool:
    current = exc
    seen_ids: set[int] = set()
    while current is not None and id(current) not in seen_ids:
        seen_ids.add(id(current))
        message = str(current).lower()
        if 'undefinedcolumn' in message and (
            'custom_books.' in message or 'custom_book_words.' in message
        ):
            return True
        if 'no such column:' in message and (
            'custom_books.' in message or 'custom_book_words.' in message
        ):
            return True
        if any(marker in message for marker in _CUSTOM_BOOK_SCHEMA_DRIFT_MARKERS):
            return True
        current = (
            getattr(current, 'orig', None)
            or getattr(current, '__cause__', None)
            or getattr(current, '__context__', None)
        )
    return False


def _rollback_quietly() -> None:
    try:
        db.session.rollback()
    except Exception:
        return


def _run_custom_book_read(*, action: str, fallback, query):
    try:
        return query()
    except Exception as exc:
        if not _is_custom_book_schema_drift_error(exc):
            raise
        _rollback_quietly()
        logging.warning(
            '[Compatibility] custom book read skipped because metadata columns are missing: action=%s error=%s',
            action,
            exc,
        )
        return fallback


def create_custom_book(
    *,
    book_id: str,
    user_id: int,
    title: str,
    description: str,
    word_count: int,
    education_stage: str = '',
    exam_type: str = '',
    ielts_skill: str = '',
    share_enabled: bool = False,
    chapter_word_target: int = 15,
):
    book = CustomBook(
        id=book_id,
        user_id=user_id,
        title=title,
        description=description,
        word_count=word_count,
        education_stage=education_stage or None,
        exam_type=exam_type or None,
        ielts_skill=ielts_skill or None,
        share_enabled=share_enabled,
        chapter_word_target=chapter_word_target,
    )
    db.session.add(book)
    return book


def create_custom_book_chapter(
    *,
    chapter_id: str,
    book_id: str,
    title: str,
    word_count: int,
    sort_order: int,
):
    chapter = CustomBookChapter(
        id=chapter_id,
        book_id=book_id,
        title=title,
        word_count=word_count,
        sort_order=sort_order,
    )
    db.session.add(chapter)
    return chapter


def create_custom_book_word(
    *,
    chapter_id: str,
    word: str,
    phonetic: str,
    pos: str,
    definition: str,
    is_incomplete: bool = False,
):
    record = CustomBookWord(
        chapter_id=chapter_id,
        word=word,
        phonetic=phonetic,
        pos=pos,
        definition=definition,
        is_incomplete=is_incomplete,
    )
    db.session.add(record)
    return record


def list_custom_books(user_id: int):
    return _run_custom_book_read(
        action='list_custom_books',
        fallback=[],
        query=lambda: (
            CustomBook.query
            .filter_by(user_id=user_id)
            .order_by(CustomBook.created_at.desc())
            .all()
        ),
    )


def get_custom_book(user_id: int, book_id: str):
    return _run_custom_book_read(
        action='get_custom_book',
        fallback=None,
        query=lambda: CustomBook.query.filter_by(id=book_id, user_id=user_id).first(),
    )


def list_custom_book_words_for_chapter_ids(chapter_ids):
    normalized_ids = [chapter_id for chapter_id in chapter_ids if chapter_id]
    if not normalized_ids:
        return []
    return _run_custom_book_read(
        action='list_custom_book_words_for_chapter_ids',
        fallback=[],
        query=lambda: CustomBookWord.query.filter(
            CustomBookWord.chapter_id.in_(normalized_ids),
        ).all(),
    )


def commit() -> None:
    db.session.commit()


def rollback() -> None:
    db.session.rollback()
