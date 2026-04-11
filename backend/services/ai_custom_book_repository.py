from __future__ import annotations

from service_models.catalog_content_models import CustomBook, CustomBookChapter, CustomBookWord, db


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
    return (
        CustomBook.query
        .filter_by(user_id=user_id)
        .order_by(CustomBook.created_at.desc())
        .all()
    )


def get_custom_book(user_id: int, book_id: str):
    return CustomBook.query.filter_by(id=book_id, user_id=user_id).first()


def list_custom_book_words_for_chapter_ids(chapter_ids):
    normalized_ids = [chapter_id for chapter_id in chapter_ids if chapter_id]
    if not normalized_ids:
        return []
    return CustomBookWord.query.filter(CustomBookWord.chapter_id.in_(normalized_ids)).all()


def commit() -> None:
    db.session.commit()


def rollback() -> None:
    db.session.rollback()
