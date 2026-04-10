from __future__ import annotations

from service_models.catalog_content_models import CustomBook, CustomBookChapter, CustomBookWord, db


def create_custom_book(
    *,
    book_id: str,
    user_id: int,
    title: str,
    description: str,
    word_count: int,
):
    book = CustomBook(
        id=book_id,
        user_id=user_id,
        title=title,
        description=description,
        word_count=word_count,
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
):
    record = CustomBookWord(
        chapter_id=chapter_id,
        word=word,
        phonetic=phonetic,
        pos=pos,
        definition=definition,
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
